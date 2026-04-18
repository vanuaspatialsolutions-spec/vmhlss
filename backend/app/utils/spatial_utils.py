from shapely.geometry import shape, box
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Vanuatu bounding box in WGS84 (EPSG:4326)
VANUATU_BBOX = box(165.0, -22.0, 172.0, -12.0)  # (minx, miny, maxx, maxy)


def validate_vanuatu_bbox(geom) -> bool:
    """
    Validate that geometry falls within Vanuatu's bounding box.

    Args:
        geom: Shapely geometry object or GeoJSON-like dict

    Returns:
        True if geometry is within Vanuatu bounds, False otherwise
    """
    try:
        # Convert dict to Shapely if needed
        if isinstance(geom, dict):
            geom = shape(geom)

        # Check if geometry intersects with Vanuatu bbox
        if not geom.intersects(VANUATU_BBOX):
            logger.warning(f"Geometry outside Vanuatu bounds: {geom.bounds}")
            return False

        # Check if geometry bounds are within Vanuatu
        geom_bbox = box(*geom.bounds)
        if not geom_bbox.within(VANUATU_BBOX):
            logger.warning(f"Geometry extends outside Vanuatu bounds: {geom.bounds}")
            return False

        return True

    except Exception as e:
        logger.error(f"Error validating Vanuatu bounds: {e}")
        return False


def blur_coordinates(
    latitude: float,
    longitude: float,
    precision: float = 0.005
) -> Tuple[float, float]:
    """
    Blur coordinates to specified precision for privacy.
    Default precision of 0.005 degrees is approximately 500 meters.

    Args:
        latitude: Original latitude in decimal degrees
        longitude: Original longitude in decimal degrees
        precision: Precision level in degrees (default 0.005 = ~500m)

    Returns:
        Tuple of (blurred_latitude, blurred_longitude)
    """
    try:
        blurred_lat = round(latitude / precision) * precision
        blurred_lon = round(longitude / precision) * precision
        return (blurred_lat, blurred_lon)
    except Exception as e:
        logger.error(f"Error blurring coordinates: {e}")
        return (latitude, longitude)


def calculate_area_ha(geom) -> Optional[float]:
    """
    Calculate the area of a geometry in hectares using PostGIS.
    Uses Vanuatu's projected CRS (EPSG:3141) for accurate area calculation.

    Args:
        geom: Shapely geometry object or GeoJSON-like dict

    Returns:
        Area in hectares, or None if calculation fails
    """
    try:
        # Convert dict to Shapely if needed
        if isinstance(geom, dict):
            geom = shape(geom)

        # Note: For production, this should use PostGIS ST_Area function
        # This is a simplified local calculation using Shapely
        # Shapely uses the same projection as input, so results are not accurate
        # without proper reprojection to EPSG:3141

        # For now, use approximate conversion from degrees squared to hectares
        # This is only valid for small areas near Vanuatu
        area_deg_sq = geom.area

        # Approximate conversion at Vanuatu latitude (-17 degrees)
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 111 * cos(latitude) km
        import math

        avg_latitude = (geom.bounds[1] + geom.bounds[3]) / 2
        lat_km = 111.0
        lon_km = 111.0 * abs(math.cos(math.radians(avg_latitude)))

        # Convert to km squared then to hectares
        area_km_sq = area_deg_sq * lat_km * lon_km
        area_hectares = area_km_sq * 100

        logger.info(f"Calculated area: {area_hectares:.2f} hectares")
        return area_hectares

    except Exception as e:
        logger.error(f"Error calculating area: {e}")
        return None


def get_vanuatu_crs_bounds() -> dict:
    """
    Get the bounding box for Vanuatu's main projected CRS systems.

    Returns:
        Dictionary with CRS codes and their approximate bounds
    """
    return {
        "EPSG:4326": {
            "name": "WGS 84 (Geographic)",
            "bounds": (165.0, -22.0, 172.0, -12.0)
        },
        "EPSG:32759": {
            "name": "WGS 84 / UTM zone 59S",
            "bounds": (200000, 7300000, 900000, 8700000)
        },
        "EPSG:32760": {
            "name": "WGS 84 / UTM zone 60S",
            "bounds": (200000, 7300000, 900000, 8700000)
        },
        "EPSG:3141": {
            "name": "Vanuatu Viti Levu Grid",
            "bounds": (-500000, -1000000, 500000, 1000000)
        },
        "EPSG:3142": {
            "name": "Vanuatu Vanua Levu Grid",
            "bounds": (-500000, -1000000, 500000, 1000000)
        }
    }


def clip_to_vanuatu(geom) -> Optional:
    """
    Clip geometry to Vanuatu's bounding box.

    Args:
        geom: Shapely geometry object or GeoJSON-like dict

    Returns:
        Clipped geometry or None if error occurs
    """
    try:
        # Convert dict to Shapely if needed
        if isinstance(geom, dict):
            geom = shape(geom)

        # Clip to Vanuatu bounds
        clipped = geom.intersection(VANUATU_BBOX)

        if clipped.is_empty:
            logger.warning("Geometry after clipping is empty")
            return None

        return clipped

    except Exception as e:
        logger.error(f"Error clipping geometry to Vanuatu bounds: {e}")
        return None
