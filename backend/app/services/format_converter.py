"""
Format Converter Service for Vanuatu Multi-Hazard Land Suitability System.

GDAL-based format conversion pipeline for geospatial data standardisation.
"""

import logging
import zipfile
import tempfile
import csv
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import geopandas as gpd
import fiona
import rasterio
from rasterio.io import MemoryFile
from osgeo import gdal, osr

logger = logging.getLogger(__name__)

# Enable GDAL exceptions for better error handling
gdal.UseExceptions()


class FormatConverter:
    """GDAL-based format conversion service."""

    @staticmethod
    def detect_format(file_path: str) -> str:
        """
        Detect true file format from file content.

        Uses GDAL for vector detection and rasterio for raster detection.

        Parameters
        ----------
        file_path : str
            Path to input file

        Returns
        -------
        str
            Format string: 'shapefile', 'geopackage', 'kml', 'geotiff', 'geojson', etc.
        """
        logger.info(f"Detecting format: {file_path}")

        file_ext = Path(file_path).suffix.lower()

        # Try GDAL vector detection first
        try:
            ds = gdal.OpenEx(file_path, gdal.OF_VECTOR)
            if ds is not None:
                driver_name = ds.GetDriver().ShortName
                ds = None
                logger.info(f"Detected vector format: {driver_name}")
                return driver_name.lower()
        except Exception:
            pass

        # Try rasterio raster detection
        try:
            with rasterio.open(file_path) as src:
                driver = src.driver
                logger.info(f"Detected raster format: {driver}")
                return driver.lower()
        except Exception:
            pass

        # Fall back to extension-based detection
        extension_map = {
            '.shp': 'shapefile',
            '.gpkg': 'geopackage',
            '.geojson': 'geojson',
            '.json': 'geojson',
            '.kml': 'kml',
            '.kmz': 'kmz',
            '.tif': 'geotiff',
            '.tiff': 'geotiff',
            '.csv': 'csv',
            '.grd': 'surfer',
            '.hdf': 'hdf',
            '.nc': 'netcdf'
        }

        detected = extension_map.get(file_ext, 'unknown')
        logger.warning(f"Using extension-based detection: {detected}")
        return detected

    # =========================================================================
    # Vector Format Conversions
    # =========================================================================

    @staticmethod
    def convert_to_geopackage(
        input_path: str,
        output_path: str,
        layer_name: str = 'layer'
    ) -> str:
        """
        Convert vector format to GeoPackage.

        Parameters
        ----------
        input_path : str
            Input vector file path
        output_path : str
            Output GeoPackage path
        layer_name : str
            Layer name in output GeoPackage (default: 'layer')

        Returns
        -------
        str
            Path to output GeoPackage

        Raises
        ------
        Exception
            If conversion fails
        """
        logger.info(f"Converting {input_path} to GeoPackage: {output_path}")

        try:
            ds = gdal.OpenEx(input_path, gdal.OF_VECTOR)
            if ds is None:
                raise ValueError(f"Cannot open {input_path} as vector dataset")

            # Use VectorTranslate for conversion
            translate_options = gdal.VectorTranslateOptions(
                format='GPKG',
                layerName=layer_name,
                overwrite=True
            )

            output_ds = gdal.VectorTranslate(
                output_path,
                ds,
                options=translate_options
            )

            if output_ds is None:
                raise ValueError("VectorTranslate failed to produce output")

            output_ds = None
            ds = None

            logger.info(f"GeoPackage created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"GeoPackage conversion failed: {str(e)}")
            raise

    # =========================================================================
    # Raster Format Conversions
    # =========================================================================

    @staticmethod
    def convert_to_cog_geotiff(
        input_path: str,
        output_path: str,
        nodata: float = -9999
    ) -> str:
        """
        Convert raster to Cloud Optimised GeoTIFF (COG).

        Applies tiling, LZW compression, and overviews for efficient access.

        Parameters
        ----------
        input_path : str
            Input raster file path
        output_path : str
            Output COG GeoTIFF path
        nodata : float
            NoData value to assign (default: -9999)

        Returns
        -------
        str
            Path to output COG GeoTIFF

        Raises
        ------
        Exception
            If conversion fails
        """
        logger.info(f"Converting {input_path} to COG GeoTIFF: {output_path}")

        try:
            translate_options = gdal.TranslateOptions(
                format='GTiff',
                creationOptions=[
                    'TILED=YES',
                    'BLOCKXSIZE=512',
                    'BLOCKYSIZE=512',
                    'COMPRESS=LZW',
                    'COPY_SRC_OVERVIEWS=YES'
                ],
                noData=nodata
            )

            output_ds = gdal.Translate(
                output_path,
                input_path,
                options=translate_options
            )

            if output_ds is None:
                raise ValueError("Translate failed to produce output")

            # Add overviews for efficient multi-scale access
            ds = gdal.Open(output_path, gdal.GA_Update)
            ds.BuildOverviews('AVERAGE', [2, 4, 8, 16])
            ds = None

            logger.info(f"COG GeoTIFF created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"COG GeoTIFF conversion failed: {str(e)}")
            raise

    # =========================================================================
    # Shapefile ZIP Handling
    # =========================================================================

    @staticmethod
    def extract_shapefile_zip(zip_path: str, output_dir: str) -> str:
        """
        Extract and validate Shapefile ZIP archive.

        Verifies presence of all required sidecar files (.shp, .dbf, .shx, .prj).

        Parameters
        ----------
        zip_path : str
            Path to ZIP archive
        output_dir : str
            Output directory for extraction

        Returns
        -------
        str
            Path to extracted .shp file

        Raises
        ------
        FileNotFoundError
            If required sidecar files are missing
        Exception
            If ZIP is corrupt or unreadable
        """
        logger.info(f"Extracting Shapefile ZIP: {zip_path}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        required_extensions = ['.shp', '.dbf', '.shx', '.prj']

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(output_dir)

            # Find .shp file
            shp_files = list(output_dir.glob('*.shp'))
            if not shp_files:
                raise FileNotFoundError("No .shp file found in ZIP archive")

            shp_path = shp_files[0]
            base_name = shp_path.stem

            # Verify required sidecar files
            for ext in required_extensions:
                sidecar = output_dir / f"{base_name}{ext}"
                if not sidecar.exists():
                    raise FileNotFoundError(f"Missing required sidecar file: {ext}")

            logger.info(f"Shapefile extracted and validated: {shp_path}")
            return str(shp_path)

        except zipfile.BadZipFile as e:
            logger.error(f"Corrupt ZIP file: {str(e)}")
            raise Exception(f"Corrupt or invalid ZIP file: {str(e)}")
        except Exception as e:
            logger.error(f"ZIP extraction failed: {str(e)}")
            raise

    # =========================================================================
    # KMZ Handling
    # =========================================================================

    @staticmethod
    def extract_kmz(kmz_path: str, output_dir: str) -> str:
        """
        Extract and validate KMZ archive.

        KMZ is a ZIP containing KML file(s).

        Parameters
        ----------
        kmz_path : str
            Path to KMZ file
        output_dir : str
            Output directory for extraction

        Returns
        -------
        str
            Path to extracted KML file

        Raises
        ------
        FileNotFoundError
            If no KML file found in archive
        Exception
            If KMZ is corrupt or unreadable
        """
        logger.info(f"Extracting KMZ: {kmz_path}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(kmz_path, 'r') as zf:
                zf.extractall(output_dir)

            # Find KML file (usually doc.kml)
            kml_files = list(output_dir.glob('*.kml'))
            if not kml_files:
                raise FileNotFoundError("No .kml file found in KMZ archive")

            kml_path = kml_files[0]
            logger.info(f"KML extracted: {kml_path}")
            return str(kml_path)

        except zipfile.BadZipFile as e:
            logger.error(f"Corrupt KMZ file: {str(e)}")
            raise Exception(f"Corrupt or invalid KMZ file: {str(e)}")
        except Exception as e:
            logger.error(f"KMZ extraction failed: {str(e)}")
            raise

    # =========================================================================
    # CSV to GeoPackage Conversion
    # =========================================================================

    @staticmethod
    def csv_to_geopackage(csv_path: str, output_path: str) -> str:
        """
        Convert CSV with lat/lon columns to GeoPackage.

        Detects latitude and longitude columns (case-insensitive) and creates
        point geometries.

        Parameters
        ----------
        csv_path : str
            Path to input CSV file
        output_path : str
            Output GeoPackage path

        Returns
        -------
        str
            Path to output GeoPackage

        Raises
        ------
        ValueError
            If lat/lon columns cannot be detected
        Exception
            If conversion fails
        """
        logger.info(f"Converting CSV to GeoPackage: {csv_path}")

        try:
            # Detect lat/lon columns
            lat_col, lon_col = FormatConverter._detect_lat_lon_columns(csv_path)

            if not lat_col or not lon_col:
                raise ValueError(f"Could not detect lat/lon columns in CSV")

            logger.info(f"Detected columns: lat={lat_col}, lon={lon_col}")

            # Read CSV and create GeoDataFrame
            df = gpd.read_file(csv_path)

            # Create point geometry
            geometry = gpd.points_from_xy(df[lon_col], df[lat_col])
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

            # Save to GeoPackage
            gdf.to_file(output_path, driver='GPKG')

            logger.info(f"GeoPackage created: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"CSV conversion failed: {str(e)}")
            raise

    @staticmethod
    def _detect_lat_lon_columns(csv_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect latitude and longitude column names in CSV.

        Parameters
        ----------
        csv_path : str
            Path to CSV file

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            (latitude_column, longitude_column) or (None, None) if not found
        """
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            headers = [h.lower() for h in reader.fieldnames or []]

        lat_candidates = {'lat', 'latitude', 'y', 'latitude_deg', 'lat_deg'}
        lon_candidates = {'lon', 'longitude', 'x', 'longitude_deg', 'lon_deg'}

        lat_col = None
        lon_col = None

        # Find matching columns (case-insensitive)
        for header in headers:
            if header in lat_candidates and lat_col is None:
                # Get original case
                lat_col = [h for h in reader.fieldnames or [] if h.lower() == header][0]
            if header in lon_candidates and lon_col is None:
                lon_col = [h for h in reader.fieldnames or [] if h.lower() == header][0]

        return lat_col, lon_col

    # =========================================================================
    # File Information
    # =========================================================================

    @staticmethod
    def get_file_info(file_path: str) -> Dict:
        """
        Get comprehensive file information.

        Parameters
        ----------
        file_path : str
            Path to geospatial file

        Returns
        -------
        Dict
            File information:
            {
                'format': str,
                'is_raster': bool,
                'crs': str,
                'geometry_type': str,
                'feature_count': int,
                'bounds': [minx, miny, maxx, maxy],
                'file_size_bytes': int,
                'band_count': int (rasters only),
                'data_type': str (rasters only),
                'resolution': (pixel_width, pixel_height) (rasters only)
            }
        """
        logger.info(f"Extracting file info: {file_path}")

        file_info = {
            'format': FormatConverter.detect_format(file_path),
            'is_raster': False,
            'crs': None,
            'geometry_type': None,
            'feature_count': 0,
            'bounds': None,
            'file_size_bytes': os.path.getsize(file_path)
        }

        # Try raster
        try:
            with rasterio.open(file_path) as src:
                file_info['is_raster'] = True
                file_info['crs'] = src.crs.to_string() if src.crs else None
                file_info['bounds'] = list(src.bounds)
                file_info['band_count'] = src.count
                file_info['data_type'] = src.dtypes[0] if src.dtypes else None
                file_info['resolution'] = (src.res[0], src.res[1])
                logger.info(f"Raster info: {src.count} bands, {src.meta['dtype']} type")
                return file_info
        except Exception:
            pass

        # Try vector
        try:
            with fiona.open(file_path) as src:
                file_info['is_raster'] = False
                file_info['crs'] = src.crs['init'] if src.crs else None
                file_info['bounds'] = src.bounds
                file_info['feature_count'] = len(src)

                # Get geometry type from first feature
                if len(src) > 0:
                    first_feature = next(iter(src))
                    file_info['geometry_type'] = first_feature['geometry']['type']

                logger.info(f"Vector info: {len(src)} features, {file_info['geometry_type']}")
                return file_info
        except Exception as e:
            logger.warning(f"Could not extract vector info: {str(e)}")

        logger.warning(f"Could not determine detailed file info for {file_path}")
        return file_info

    # =========================================================================
    # Utility Functions
    # =========================================================================

    @staticmethod
    def validate_crs(crs_string: str) -> bool:
        """
        Validate CRS string.

        Parameters
        ----------
        crs_string : str
            CRS string (e.g., 'EPSG:4326')

        Returns
        -------
        bool
            True if valid, False otherwise
        """
        try:
            from pyproj import CRS
            CRS.from_string(crs_string)
            return True
        except Exception:
            return False

    @staticmethod
    def reproject_to_4326(
        input_path: str,
        output_path: str,
        source_crs: Optional[str] = None
    ) -> str:
        """
        Reproject geospatial file to EPSG:4326.

        Parameters
        ----------
        input_path : str
            Input file path
        output_path : str
            Output file path
        source_crs : str, optional
            Source CRS if not defined in file

        Returns
        -------
        str
            Path to reprojected file
        """
        logger.info(f"Reprojecting {input_path} to EPSG:4326")

        try:
            # Detect if raster or vector
            is_raster = FormatConverter._is_raster_file(input_path)

            if is_raster:
                gdal.Warp(
                    output_path,
                    input_path,
                    dstSRS='EPSG:4326',
                    srcSRS=source_crs
                )
            else:
                gdf = gpd.read_file(input_path)
                if source_crs:
                    gdf = gdf.set_crs(source_crs)
                gdf = gdf.to_crs('EPSG:4326')
                gdf.to_file(output_path, driver='GPKG')

            logger.info(f"Reprojection complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Reprojection failed: {str(e)}")
            raise

    @staticmethod
    def _is_raster_file(file_path: str) -> bool:
        """Check if file is raster."""
        try:
            with rasterio.open(file_path):
                return True
        except Exception:
            return False

    @staticmethod
    def clip_to_aoi(
        input_path: str,
        aoi_geom: dict,
        output_path: str
    ) -> str:
        """
        Clip geospatial file to Area of Interest.

        Parameters
        ----------
        input_path : str
            Input file path
        aoi_geom : dict
            AOI geometry (GeoJSON-like)
        output_path : str
            Output file path

        Returns
        -------
        str
            Path to clipped file
        """
        logger.info(f"Clipping {input_path} to AOI")

        try:
            aoi_gdf = gpd.GeoDataFrame(
                [{'geometry': gpd.geometry.shape(aoi_geom)}],
                crs='EPSG:4326'
            )

            gdf = gpd.read_file(input_path)
            clipped = gpd.clip(gdf, aoi_gdf)

            clipped.to_file(output_path, driver='GPKG')
            logger.info(f"Clipping complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Clipping failed: {str(e)}")
            raise
