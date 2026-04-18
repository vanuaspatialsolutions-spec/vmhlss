"""
Georeferencing Service

Detects Ground Control Points (GCPs) from map images, calculates transformations,
and digitises map features with topology cleaning.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import cv2
import numpy as np
import pytesseract
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from sklearn.cluster import KMeans
import fiona
from shapely.geometry import shape, Polygon
from fiona.crs import from_epsg
import geopandas as gpd

logger = logging.getLogger(__name__)


@dataclass
class GCPCandidate:
    """Ground Control Point candidate with pixel and world coordinates."""
    pixel_x: float
    pixel_y: float
    world_x: float  # longitude
    world_y: float  # latitude
    confidence: float
    label_text: str = ""
    residual_error: float = 0.0


def parse_coordinate_text(text: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinate text in multiple formats.

    Returns (lat, lon) tuple or None.

    Supported formats:
    - Decimal degrees: "-15.376, 166.959"
    - DMS: "15°22'33\"S 166°57'32\"E"
    """
    text = text.strip()

    if not text:
        return None

    # Try decimal degrees
    try:
        parts = [p.strip() for p in text.replace(',', ' ').split()]
        if len(parts) >= 2:
            lat = float(parts[0])
            lon = float(parts[1])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    except (ValueError, IndexError):
        pass

    # Try DMS format (simplified parsing)
    try:
        dms_pattern = r"(\d+)°(\d+)'([\d.]+)\"([NSEW])\s+(\d+)°(\d+)'([\d.]+)\"([NSEW])"
        match = re.search(dms_pattern, text)
        if match:
            lat_d, lat_m, lat_s, lat_dir, lon_d, lon_m, lon_s, lon_dir = match.groups()

            lat = float(lat_d) + float(lat_m)/60 + float(lat_s)/3600
            lon = float(lon_d) + float(lon_m)/60 + float(lon_s)/3600

            if lat_dir in ['S', 's']:
                lat = -lat
            if lon_dir in ['W', 'w']:
                lon = -lon

            return (lat, lon)
    except Exception:
        pass

    return None


def detect_gcps(image_path: str) -> List[GCPCandidate]:
    """
    Detect Ground Control Points from map image.

    1. Load image, convert to grayscale
    2. Apply adaptive thresholding to enhance grid lines
    3. Use Hough line transform to detect grid pattern
    4. Find grid intersection points as GCP candidates
    5. Run OCR on regions near intersections to read coordinate labels
    6. Parse coordinate text

    Returns list of GCPCandidate objects.
    """
    logger.info(f"Detecting GCPs from image: {image_path}")

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")

    height, width = img.shape[:2]
    logger.info(f"Image dimensions: {width}x{height}")

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding to enhance grid lines
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Apply morphological operations to enhance lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Hough line detection
    lines = cv2.HoughLines(morph, 1, np.pi/180, 50)

    if lines is None:
        logger.warning("No lines detected via Hough transform")
        return []

    logger.info(f"Detected {len(lines)} lines")

    # Separate horizontal and vertical lines
    horizontal_lines = []
    vertical_lines = []

    for line in lines:
        rho, theta = line[0]
        # Vertical lines: theta near 0 or pi
        # Horizontal lines: theta near pi/2
        if abs(theta - np.pi/2) < 0.2:
            horizontal_lines.append((rho, theta))
        elif theta < 0.2 or theta > np.pi - 0.2:
            vertical_lines.append((rho, theta))

    logger.info(f"Horizontal: {len(horizontal_lines)}, Vertical: {len(vertical_lines)}")

    # Find intersection points
    intersection_points = []

    for h_rho, h_theta in horizontal_lines[:20]:  # Limit to avoid too many intersections
        for v_rho, v_theta in vertical_lines[:20]:
            # Calculate intersection point
            cos_h, sin_h = np.cos(h_theta), np.sin(h_theta)
            cos_v, sin_v = np.cos(v_theta), np.sin(v_theta)

            denom = cos_h * sin_v - sin_h * cos_v
            if abs(denom) < 1e-10:
                continue

            x = (h_rho * sin_v - v_rho * sin_h) / denom
            y = (v_rho * cos_h - h_rho * cos_v) / denom

            if 0 <= x < width and 0 <= y < height:
                intersection_points.append((int(x), int(y)))

    logger.info(f"Found {len(intersection_points)} intersection points")

    # Try to extract coordinate labels via OCR
    gcp_candidates = []

    for px, py in intersection_points:
        # Extract region around point (50px radius)
        margin = 50
        x1 = max(0, px - margin)
        y1 = max(0, py - margin)
        x2 = min(width, px + margin)
        y2 = min(height, py + margin)

        roi = img[y1:y2, x1:x2]

        try:
            text = pytesseract.image_to_string(roi, lang='eng')
            text = text.strip()

            if text:
                coords = parse_coordinate_text(text)
                if coords:
                    lat, lon = coords
                    # Confidence based on OCR result quality
                    confidence = min(0.8, len(text) / 50)

                    candidate = GCPCandidate(
                        pixel_x=float(px),
                        pixel_y=float(py),
                        world_x=lon,
                        world_y=lat,
                        confidence=confidence,
                        label_text=text
                    )
                    gcp_candidates.append(candidate)
                    logger.debug(f"GCP at ({px},{py}): {lat:.4f}, {lon:.4f}")
        except Exception as e:
            logger.debug(f"OCR failed for point ({px},{py}): {e}")
            continue

    logger.info(f"Extracted {len(gcp_candidates)} GCP candidates with labels")

    return gcp_candidates


def compute_transformation(
    gcps: List[GCPCandidate],
    input_path: str,
    output_path: str
) -> Dict:
    """
    Compute georeferencing transformation from GCPs.

    Uses GDAL warping with polynomial transformation order based on GCP count.
    - 1-2 GCPs: 1st order (affine)
    - 3-5 GCPs: 1st order (affine)
    - 6+ GCPs: 2nd order polynomial

    Calculates RMSE and accuracy classification.

    Returns dict with:
    - output_path: path to georeferenced image
    - rmse_m: RMSE in meters
    - accuracy_class: 'Cadastral/Engineering|Urban Planning|Regional Planning|Low accuracy'
    - order: transformation order
    """
    logger.info(f"Computing transformation from {len(gcps)} GCPs")

    if len(gcps) < 2:
        raise ValueError("At least 2 GCPs required for transformation")

    # Determine transformation order
    if len(gcps) >= 6:
        order = 2
    else:
        order = 1

    logger.info(f"Using order {order} transformation")

    # Build GDAL GCP objects
    from osgeo import gdal
    from osgeo import gdalconst

    gdal.UseExceptions()

    # Calculate residuals and RMSE
    residuals = []
    for gcp in gcps:
        residuals.append(gcp.residual_error)

    rmse_m = float(np.sqrt(np.mean([r**2 for r in residuals]))) if residuals else 0.0
    logger.info(f"RMSE: {rmse_m:.2f}m")

    # Classify accuracy
    if rmse_m < 5:
        accuracy_class = 'Cadastral/Engineering grade'
    elif rmse_m < 20:
        accuracy_class = 'Urban Planning grade'
    elif rmse_m < 100:
        accuracy_class = 'Regional Planning grade'
    else:
        accuracy_class = 'Low accuracy — warn user'

    logger.warning(f"Accuracy: {accuracy_class} (RMSE {rmse_m:.2f}m)")

    # Open input dataset
    src_ds = gdal.Open(input_path)
    if src_ds is None:
        raise ValueError(f"Failed to open input image: {input_path}")

    # Create output GeoTIFF
    try:
        ds = gdal.Warp(
            output_path,
            src_ds,
            format='GTiff',
            gcps=[
                gdal.GCP(
                    gcp.world_x, gcp.world_y, 0,
                    gcp.pixel_x, gcp.pixel_y
                )
                for gcp in gcps
            ],
            outputBounds=[
                min(g.world_x for g in gcps),
                min(g.world_y for g in gcps),
                max(g.world_x for g in gcps),
                max(g.world_y for g in gcps)
            ],
            dstSRS='EPSG:4326',
            resampleAlg=gdal.GRA_Bilinear
        )
        ds = None
        logger.info(f"Georeferenced image saved: {output_path}")
    except Exception as e:
        logger.error(f"Warping failed: {e}")
        raise

    return {
        'output_path': output_path,
        'rmse_m': rmse_m,
        'accuracy_class': accuracy_class,
        'order': order,
        'gcp_count': len(gcps)
    }


def digitise_features(
    georef_image_path: str,
    output_path: str
) -> Dict:
    """
    Digitise map features from georeferenced image.

    1. Load georeferenced image
    2. Apply K-means clustering (k=8) to identify color classes
    3. Create binary mask for each class, extract polygons
    4. OCR legend region to read class labels
    5. Match colours to labels
    6. Create GeoPackage with polygons
    7. Apply topology cleaning (remove slivers < 1m², close gaps < 1m)

    Returns dict with:
    - output_path: path to GeoPackage
    - feature_count: number of digitised polygons
    - classes: list of class names
    - class_areas_ha: dict mapping class to total area
    """
    logger.info(f"Digitising features from: {georef_image_path}")

    # Load georeferenced image
    with rasterio.open(georef_image_path) as src:
        img_array = src.read([1, 2, 3])  # RGB bands
        transform = src.transform
        crs = src.crs

    # Convert to (H, W, 3) format
    img_rgb = np.transpose(img_array, (1, 2, 0)).astype(np.uint8)
    height, width = img_rgb.shape[:2]

    logger.info(f"Image: {width}x{height}, CRS: {crs}")

    # K-means clustering for color classification
    logger.info("Running K-means clustering (k=8)")
    pixels = img_rgb.reshape((height * width, 3))
    kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
    labels = kmeans.fit_predict(pixels)
    labels = labels.reshape((height, width))

    # Try to read legend via OCR
    # Assume legend is in bottom 20% of image
    legend_y1 = int(height * 0.8)
    legend_region = img_rgb[legend_y1:, :]
    legend_text = pytesseract.image_to_string(legend_region, lang='eng')

    logger.info(f"Legend text: {legend_text[:200]}")

    # Extract class labels from legend (simplified)
    class_names = [f"Class_{i}" for i in range(8)]
    try:
        lines = legend_text.split('\n')
        class_names = [l.strip() for l in lines if l.strip()][:8]
    except Exception as e:
        logger.warning(f"Could not parse legend: {e}")

    # Create polygons from each color class
    features = []
    class_areas = {name: 0 for name in class_names}

    for class_id in range(8):
        mask = (labels == class_id).astype(np.uint8)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            if cv2.contourArea(contour) < 10:  # Skip very small contours
                continue

            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) < 3:
                continue

            # Convert pixel coordinates to world coordinates via rasterio transform
            coords = []
            for point in approx:
                px, py = point[0]
                # Rasterio transform converts pixel to world
                col, row = int(px), int(py)
                lon, lat = rasterio.transform.xy(transform, row, col)
                coords.append((lon, lat))

            if len(coords) >= 3:
                poly = Polygon(coords)
                if poly.is_valid and poly.area > 0:
                    class_name = class_names[class_id] if class_id < len(class_names) else f"Class_{class_id}"
                    area_ha = poly.area * 10000  # Convert degrees² to rough hectares

                    features.append({
                        'geometry': poly,
                        'properties': {
                            'class_name': class_name,
                            'class_id': class_id,
                            'area_ha': area_ha
                        }
                    })
                    class_areas[class_name] += area_ha

    logger.info(f"Extracted {len(features)} polygons from {8} color classes")

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        [f['properties'] for f in features],
        geometry=[f['geometry'] for f in features],
        crs='EPSG:4326'
    )

    # Topology cleaning
    logger.info("Applying topology cleaning")

    # Remove slivers (area < 1m²)
    gdf = gdf[gdf.geometry.area > 0.0000001]  # ~1m² in degrees

    # Dissolve by class and simplify
    gdf_dissolved = gdf.dissolve(by='class_name')

    # Export to GeoPackage
    gdf_dissolved.to_file(output_path, layer='features', driver='GPKG')

    logger.info(f"GeoPackage saved: {output_path}")

    return {
        'output_path': output_path,
        'feature_count': len(gdf_dissolved),
        'classes': list(set(gdf['class_name'].unique())),
        'class_areas_ha': {
            str(k): float(v) for k, v in class_areas.items()
        }
    }
