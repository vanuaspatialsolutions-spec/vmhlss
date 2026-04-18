from typing import Tuple, List, Optional, Dict
import logging
import os

logger = logging.getLogger(__name__)

# List of Vanuatu-relevant CRS codes
VANUATU_CRS_LIST = [
    "EPSG:4326",  # WGS 84 (Geographic)
    "EPSG:32759",  # WGS 84 / UTM zone 59S
    "EPSG:32760",  # WGS 84 / UTM zone 60S
    "EPSG:3141",  # Vanuatu Viti Levu Grid
    "EPSG:3142"  # Vanuatu Vanua Levu Grid
]


def detect_crs(file_path: str) -> Optional[str]:
    """
    Detect the CRS of a raster or vector file.

    Args:
        file_path: Path to the geospatial file

    Returns:
        CRS code string (e.g., "EPSG:4326") or None if detection fails
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    try:
        # Try rasterio first for raster files
        try:
            import rasterio

            with rasterio.open(file_path) as src:
                crs = src.crs
                if crs:
                    crs_string = crs.to_string()
                    logger.info(f"Detected CRS from raster: {crs_string}")
                    return crs_string
        except Exception as raster_error:
            logger.debug(f"Could not detect CRS as raster: {raster_error}")

        # Try fiona for vector files
        try:
            import fiona

            with fiona.open(file_path) as src:
                crs = src.crs
                if crs:
                    # Handle different CRS dict formats
                    if isinstance(crs, dict):
                        if "init" in crs:
                            crs_string = crs["init"].upper()
                        elif "authority" in crs and "code" in crs:
                            crs_string = f"EPSG:{crs['code']}"
                        else:
                            crs_string = None
                    else:
                        crs_string = str(crs).upper()

                    if crs_string:
                        logger.info(f"Detected CRS from vector: {crs_string}")
                        return crs_string
        except Exception as vector_error:
            logger.debug(f"Could not detect CRS as vector: {vector_error}")

        logger.warning(f"Could not detect CRS for {file_path}")
        return None

    except Exception as e:
        logger.error(f"Error detecting CRS: {e}")
        return None


def infer_crs_from_bounds(
    bounds: Tuple[float, float, float, float]
) -> Tuple[List[str], Dict[str, float]]:
    """
    Infer likely CRS from geometry bounds.
    Returns candidate CRS codes and confidence scores.

    Args:
        bounds: Tuple of (minx, miny, maxx, maxy)

    Returns:
        Tuple of (candidate_crs_list, confidence_scores_dict)
    """
    try:
        minx, miny, maxx, maxy = bounds

        candidates = []
        confidence_scores = {}

        # Check if bounds look like geographic (WGS84)
        if -180 <= minx <= 180 and -90 <= miny <= 90 and -180 <= maxx <= 180 and -90 <= maxy <= 90:
            # Check if within Vanuatu geographic bounds
            if 165.0 <= minx and maxx <= 172.0 and -22.0 <= miny and maxy <= -12.0:
                candidates.append("EPSG:4326")
                confidence_scores["EPSG:4326"] = 0.95
            else:
                # Likely geographic but not Vanuatu
                candidates.append("EPSG:4326")
                confidence_scores["EPSG:4326"] = 0.70

        # Check if bounds look like UTM zones 59S or 60S
        elif 200000 <= minx <= 900000 and 7300000 <= miny <= 8700000:
            if minx < 500000:
                candidates.append("EPSG:32759")
                confidence_scores["EPSG:32759"] = 0.85
            else:
                candidates.append("EPSG:32760")
                confidence_scores["EPSG:32760"] = 0.85

        # Check if bounds look like Vanuatu projected grid
        elif -500000 <= minx <= 500000 and -1000000 <= miny <= 1000000:
            candidates.append("EPSG:3141")
            candidates.append("EPSG:3142")
            confidence_scores["EPSG:3141"] = 0.80
            confidence_scores["EPSG:3142"] = 0.80

        # If no matches, return all Vanuatu CRS with low confidence
        if not candidates:
            candidates = VANUATU_CRS_LIST.copy()
            for crs in candidates:
                confidence_scores[crs] = 0.30

        logger.info(
            f"Inferred CRS from bounds {bounds}: {candidates} "
            f"with scores {confidence_scores}"
        )

        return (candidates, confidence_scores)

    except Exception as e:
        logger.error(f"Error inferring CRS from bounds: {e}")
        return (VANUATU_CRS_LIST.copy(), {crs: 0.1 for crs in VANUATU_CRS_LIST})


def reproject_to_wgs84(
    input_file: str,
    output_file: str,
    input_crs: Optional[str] = None
) -> bool:
    """
    Reproject a geospatial file to WGS84 (EPSG:4326).

    Args:
        input_file: Path to input file
        output_file: Path to output file
        input_crs: Optional CRS of input file (detected if not provided)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Detect CRS if not provided
        if input_crs is None:
            input_crs = detect_crs(input_file)

        if input_crs is None:
            logger.error(f"Could not determine CRS for {input_file}")
            return False

        # For raster files
        try:
            import rasterio
            from rasterio.vrt import WarpedVRT
            from rasterio.io import MemoryFile

            with rasterio.open(input_file) as src:
                # Create warped VRT to WGS84
                with WarpedVRT(
                    src,
                    crs="EPSG:4326",
                    resampling=rasterio.enums.Resampling.bilinear
                ) as vrt:
                    # Copy to output
                    with rasterio.open(
                        output_file,
                        "w",
                        driver="GTiff",
                        height=vrt.height,
                        width=vrt.width,
                        count=vrt.count,
                        dtype=vrt.dtypes[0],
                        crs=vrt.crs,
                        transform=vrt.transform,
                        nodata=vrt.nodata
                    ) as dst:
                        dst.write(vrt.read())

            logger.info(f"Reprojected raster {input_file} to WGS84")
            return True

        except Exception as raster_error:
            logger.debug(f"Could not reproject as raster: {raster_error}")

        # For vector files
        try:
            import fiona
            from fiona.transform import transform
            from pyproj import Transformer

            # Create transformer
            transformer = Transformer.from_crs(
                input_crs,
                "EPSG:4326",
                always_xy=True
            )

            with fiona.open(input_file) as src:
                output_schema = src.schema.copy()
                output_schema["crs"] = "EPSG:4326"

                with fiona.open(
                    output_file,
                    "w",
                    driver=src.driver,
                    schema=output_schema,
                    crs="EPSG:4326"
                ) as dst:
                    for feature in src:
                        # Transform coordinates
                        def transform_coords(coords):
                            if isinstance(coords[0], (list, tuple)):
                                return [transform_coords(c) for c in coords]
                            else:
                                lon, lat = transformer.transform(coords[0], coords[1])
                                return (lon, lat)

                        feature["geometry"]["coordinates"] = transform_coords(
                            feature["geometry"]["coordinates"]
                        )
                        dst.write(feature)

            logger.info(f"Reprojected vector {input_file} to WGS84")
            return True

        except Exception as vector_error:
            logger.error(f"Could not reproject as vector: {vector_error}")
            return False

    except Exception as e:
        logger.error(f"Error reprojecting file: {e}")
        return False


def validate_crs(crs_string: str) -> bool:
    """
    Validate that a CRS string is recognized and valid.

    Args:
        crs_string: CRS code (e.g., "EPSG:4326")

    Returns:
        True if CRS is valid, False otherwise
    """
    try:
        from pyproj import CRS

        crs = CRS.from_string(crs_string)
        return crs.is_valid
    except Exception as e:
        logger.warning(f"Invalid CRS: {crs_string}: {e}")
        return False


def is_vanuatu_crs(crs_string: str) -> bool:
    """
    Check if a CRS is one of the standard Vanuatu CRS codes.

    Args:
        crs_string: CRS code (e.g., "EPSG:4326")

    Returns:
        True if CRS is in Vanuatu's standard list, False otherwise
    """
    return crs_string in VANUATU_CRS_LIST


def get_crs_info(crs_string: str) -> Optional[Dict]:
    """
    Get information about a CRS.

    Args:
        crs_string: CRS code (e.g., "EPSG:4326")

    Returns:
        Dictionary with CRS information or None if invalid
    """
    try:
        from pyproj import CRS

        crs = CRS.from_string(crs_string)

        return {
            "code": crs_string,
            "name": crs.name,
            "type": crs.type_string if hasattr(crs, "type_string") else "unknown",
            "area_of_use": str(crs.area_of_use) if crs.area_of_use else None,
            "is_geographic": crs.is_geographic,
            "is_projected": crs.is_projected
        }

    except Exception as e:
        logger.error(f"Error getting CRS info for {crs_string}: {e}")
        return None
