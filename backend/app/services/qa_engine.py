"""
Quality Assurance Engine for Vanuatu Multi-Hazard Land Suitability System.

Six-stage QA pipeline for geospatial data validation and auto-correction.
Each stage returns a QAStageResult with detailed fix records and diagnostic info.
"""

import logging
import zipfile
import tempfile
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Literal
from pathlib import Path
from datetime import datetime
import csv

import numpy as np
import geopandas as gpd
import fiona
import rasterio
from rasterio.transform import from_bounds
from osgeo import gdal, osr
import pyproj
from pyproj import Transformer, CRS
from sqlalchemy.orm import Session
import difflib

logger = logging.getLogger(__name__)

# Vanuatu spatial reference parameters
VANUATU_BBOX = {
    'min_lat': -22.0,
    'max_lat': -12.0,
    'min_lon': 165.0,
    'max_lon': 172.0
}

VANUATU_CRS_LIST = ['EPSG:4326', 'EPSG:32759', 'EPSG:32760', 'EPSG:3141', 'EPSG:3142']


@dataclass
class FixRecord:
    """Record of a single fix applied during QA."""
    fix_type: str
    description: str
    before: Optional[str] = None
    after: Optional[str] = None


@dataclass
class QAStageResult:
    """Result of a single QA stage."""
    stage_number: int
    stage_name: str
    status: Literal['pass', 'auto_fixed', 'partial_fix_required', 'failed']
    fixes_applied: List[FixRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failure_message: Optional[str] = None
    recommended_source: Optional[str] = None
    partial_fix_data: Optional[dict] = None


class QAEngine:
    """Six-stage QA pipeline for geospatial data ingestion."""

    def __init__(self, upload_id: str, db: Session):
        self.upload_id = upload_id
        self.db = db
        self.results = []

    # =========================================================================
    # STAGE 1: Format and Readability
    # =========================================================================

    async def stage_1_format_and_readability(self, file_path: str) -> QAStageResult:
        """
        Detect true file format and auto-convert to standard formats.
        - GeoPackage for vectors
        - COG GeoTIFF for rasters
        """
        logger.info(f"Stage 1: Format and Readability - {file_path}")
        result = QAStageResult(
            stage_number=1,
            stage_name='Format and Readability',
            status='pass'
        )

        try:
            file_ext = Path(file_path).suffix.lower()

            # Handle shapefile ZIP archives
            if file_ext == '.zip':
                try:
                    return await self._handle_shapefile_zip(file_path, result)
                except Exception as e:
                    logger.error(f"Shapefile ZIP extraction failed: {str(e)}")
                    result.status = 'failed'
                    result.failure_message = f"Corrupt or invalid ZIP file: {str(e)}"
                    return result

            # Handle KMZ archives
            if file_ext == '.kmz':
                try:
                    return await self._handle_kmz(file_path, result)
                except Exception as e:
                    logger.error(f"KMZ extraction failed: {str(e)}")
                    result.status = 'failed'
                    result.failure_message = f"Corrupt or invalid KMZ file: {str(e)}"
                    return result

            # Handle CSV
            if file_ext == '.csv':
                try:
                    return await self._handle_csv(file_path, result)
                except Exception as e:
                    logger.error(f"CSV processing failed: {str(e)}")
                    result.status = 'failed'
                    result.failure_message = f"Invalid CSV file: {str(e)}"
                    return result

            # Try GDAL detection for vectors
            try:
                ds = gdal.OpenEx(file_path, gdal.OF_VECTOR)
                if ds is not None:
                    gdal.Dataset = None
                    return await self._convert_vector_to_geopackage(file_path, result)
            except Exception:
                pass

            # Try rasterio for rasters
            try:
                with rasterio.open(file_path) as src:
                    return await self._convert_raster_to_cog(file_path, result)
            except Exception:
                pass

            result.status = 'failed'
            result.failure_message = f"Unable to detect file format for {Path(file_path).name}"
            return result

        except Exception as e:
            logger.error(f"Stage 1 unexpected error: {str(e)}")
            result.status = 'failed'
            result.failure_message = f"Unexpected error in format detection: {str(e)}"
            return result

    async def _handle_shapefile_zip(self, zip_path: str, result: QAStageResult) -> QAStageResult:
        """Extract and validate shapefile ZIP archive."""
        temp_dir = tempfile.mkdtemp()
        required_files = ['.shp', '.dbf', '.shx', '.prj']

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(temp_dir)

        shp_files = list(Path(temp_dir).glob('*.shp'))
        if not shp_files:
            raise ValueError("No .shp file found in ZIP archive")

        shp_path = str(shp_files[0])
        base_path = Path(shp_path).stem

        for ext in required_files:
            sidecar = Path(temp_dir) / f"{base_path}{ext}"
            if not sidecar.exists():
                raise ValueError(f"Missing required sidecar file: {ext}")

        # Convert to GeoPackage
        output_path = Path(temp_dir) / f"{base_path}.gpkg"
        gdal.VectorTranslate(
            str(output_path),
            shp_path,
            format='GPKG'
        )

        result.status = 'auto_fixed'
        result.fixes_applied.append(FixRecord(
            fix_type='format_conversion',
            description=f'Converted Shapefile ZIP to GeoPackage',
            before=Path(zip_path).name,
            after=output_path.name
        ))
        result.recommended_source = str(output_path)
        return result

    async def _handle_kmz(self, kmz_path: str, result: QAStageResult) -> QAStageResult:
        """Extract and convert KMZ to GeoPackage."""
        temp_dir = tempfile.mkdtemp()

        with zipfile.ZipFile(kmz_path, 'r') as zf:
            zf.extractall(temp_dir)

        kml_files = list(Path(temp_dir).glob('*.kml'))
        if not kml_files:
            raise ValueError("No .kml file found in KMZ archive")

        kml_path = str(kml_files[0])
        output_path = Path(temp_dir) / f"{Path(kmz_path).stem}.gpkg"

        gdal.VectorTranslate(
            str(output_path),
            kml_path,
            format='GPKG'
        )

        result.status = 'auto_fixed'
        result.fixes_applied.append(FixRecord(
            fix_type='format_conversion',
            description='Converted KMZ to GeoPackage',
            before=Path(kmz_path).name,
            after=output_path.name
        ))
        result.recommended_source = str(output_path)
        return result

    async def _handle_csv(self, csv_path: str, result: QAStageResult) -> QAStageResult:
        """Detect lat/lon columns and convert to GeoPackage."""
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        lat_col = self._find_column(headers, ['lat', 'latitude', 'y'])
        lon_col = self._find_column(headers, ['lon', 'longitude', 'x'])

        if not lat_col or not lon_col:
            raise ValueError(f"Could not detect lat/lon columns. Found: {headers}")

        df = gpd.read_file(csv_path)
        geometry = gpd.points_from_xy(df[lon_col], df[lat_col])
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

        output_path = Path(csv_path).parent / f"{Path(csv_path).stem}.gpkg"
        gdf.to_file(str(output_path), driver='GPKG')

        result.status = 'auto_fixed'
        result.fixes_applied.append(FixRecord(
            fix_type='format_conversion',
            description=f'Converted CSV to GeoPackage (lat: {lat_col}, lon: {lon_col})',
            before=Path(csv_path).name,
            after=output_path.name
        ))
        result.recommended_source = str(output_path)
        return result

    async def _convert_vector_to_geopackage(self, file_path: str, result: QAStageResult) -> QAStageResult:
        """Convert vector to GeoPackage."""
        output_path = Path(file_path).parent / f"{Path(file_path).stem}.gpkg"

        gdal.VectorTranslate(
            str(output_path),
            file_path,
            format='GPKG'
        )

        result.status = 'auto_fixed'
        result.fixes_applied.append(FixRecord(
            fix_type='format_conversion',
            description='Converted to GeoPackage format',
            before=Path(file_path).name,
            after=output_path.name
        ))
        result.recommended_source = str(output_path)
        return result

    async def _convert_raster_to_cog(self, file_path: str, result: QAStageResult) -> QAStageResult:
        """Convert raster to COG GeoTIFF."""
        output_path = Path(file_path).parent / f"{Path(file_path).stem}_cog.tif"

        gdal.Translate(
            str(output_path),
            file_path,
            format='GTiff',
            creationOptions=['TILED=YES', 'COMPRESS=LZW', 'COPY_SRC_OVERVIEWS=YES']
        )

        # Add overviews
        ds = gdal.Open(str(output_path), gdal.GA_Update)
        ds.BuildOverviews('AVERAGE', [2, 4, 8, 16])
        ds = None

        result.status = 'auto_fixed'
        result.fixes_applied.append(FixRecord(
            fix_type='format_conversion',
            description='Converted to Cloud Optimised GeoTIFF with overviews',
            before=Path(file_path).name,
            after=output_path.name
        ))
        result.recommended_source = str(output_path)
        return result

    @staticmethod
    def _find_column(headers: List[str], candidates: List[str]) -> Optional[str]:
        """Find column matching any candidate name (case-insensitive)."""
        headers_lower = {h.lower(): h for h in headers}
        for candidate in candidates:
            if candidate.lower() in headers_lower:
                return headers_lower[candidate.lower()]
        return None

    # =========================================================================
    # STAGE 2: CRS and Projection
    # =========================================================================

    async def stage_2_crs_projection(self, file_path: str) -> QAStageResult:
        """Check for defined CRS, reproject if needed, or infer if missing."""
        logger.info(f"Stage 2: CRS and Projection - {file_path}")
        result = QAStageResult(
            stage_number=2,
            stage_name='CRS and Projection',
            status='pass'
        )

        try:
            is_raster = self._is_raster(file_path)
            crs = self._get_crs(file_path, is_raster)

            if crs:
                # CRS is defined; reproject to EPSG:4326 if needed
                if crs != 'EPSG:4326':
                    self._reproject_to_4326(file_path, is_raster)
                    result.status = 'auto_fixed'
                    result.fixes_applied.append(FixRecord(
                        fix_type='crs_reprojection',
                        description=f'Reprojected from {crs} to EPSG:4326',
                        before=crs,
                        after='EPSG:4326'
                    ))
                return result

            # CRS undefined; infer from coordinates
            bounds = self._get_bounds(file_path, is_raster)
            inferred_crs, confidence = self._infer_crs(bounds)

            if confidence >= 0.90:
                self._reproject_to_4326(file_path, is_raster, source_crs=inferred_crs)
                result.status = 'auto_fixed'
                result.fixes_applied.append(FixRecord(
                    fix_type='crs_inference',
                    description=f'Inferred CRS {inferred_crs} with {confidence:.1%} confidence and reprojected to EPSG:4326',
                    before='Undefined',
                    after='EPSG:4326'
                ))
                return result

            # Confidence too low; return candidates for user selection
            candidates = self._get_top_crs_candidates(bounds, 3)
            result.status = 'partial_fix_required'
            result.warnings.append(f'CRS inference confidence too low ({confidence:.1%})')
            result.partial_fix_data = {
                'inferred_bounds': bounds,
                'candidate_crs': candidates
            }
            return result

        except Exception as e:
            logger.error(f"Stage 2 error: {str(e)}")
            result.status = 'failed'
            result.failure_message = str(e)
            return result

    def _is_raster(self, file_path: str) -> bool:
        """Detect if file is raster or vector."""
        try:
            with rasterio.open(file_path):
                return True
        except Exception:
            return False

    def _get_crs(self, file_path: str, is_raster: bool) -> Optional[str]:
        """Get CRS from file."""
        try:
            if is_raster:
                with rasterio.open(file_path) as src:
                    return src.crs.to_string() if src.crs else None
            else:
                with fiona.open(file_path) as src:
                    return src.crs['init'] if src.crs else None
        except Exception:
            return None

    def _get_bounds(self, file_path: str, is_raster: bool) -> Dict:
        """Get bounds in lat/lon."""
        if is_raster:
            with rasterio.open(file_path) as src:
                bounds = src.bounds
                return {'min_lat': bounds.bottom, 'max_lat': bounds.top,
                        'min_lon': bounds.left, 'max_lon': bounds.right}
        else:
            with fiona.open(file_path) as src:
                bounds = src.bounds
                return {'min_lat': bounds[1], 'max_lat': bounds[3],
                        'min_lon': bounds[0], 'max_lon': bounds[2]}

    def _infer_crs(self, bounds: Dict) -> Tuple[str, float]:
        """Infer CRS from bounds with confidence score."""
        best_crs = None
        best_overlap = 0.0

        for crs_code in VANUATU_CRS_LIST:
            try:
                crs_obj = CRS.from_string(crs_code)
                if crs_obj.is_geographic:
                    overlap = self._calculate_overlap(bounds, VANUATU_BBOX)
                else:
                    # For projected CRS, transform Vanuatu bbox and check
                    transformer = Transformer.from_crs('EPSG:4326', crs_code, always_xy=True)
                    vanuatu_bounds_proj = self._transform_bounds(VANUATU_BBOX, transformer)
                    overlap = self._calculate_overlap(bounds, vanuatu_bounds_proj)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_crs = crs_code
            except Exception:
                continue

        confidence = max(0.0, min(1.0, best_overlap))
        return best_crs or 'EPSG:4326', confidence

    def _get_top_crs_candidates(self, bounds: Dict, n: int) -> List[Dict]:
        """Get top N CRS candidates by overlap."""
        candidates = []
        for crs_code in VANUATU_CRS_LIST:
            try:
                overlap = self._calculate_overlap(bounds, VANUATU_BBOX)
                candidates.append({
                    'crs': crs_code,
                    'overlap_percentage': overlap * 100,
                    'description': f"{crs_code} ({overlap*100:.1f}% overlap)"
                })
            except Exception:
                continue

        return sorted(candidates, key=lambda x: x['overlap_percentage'], reverse=True)[:n]

    @staticmethod
    def _calculate_overlap(bounds1: Dict, bounds2: Dict) -> float:
        """Calculate overlap percentage between two bounding boxes."""
        x_overlap = max(0, min(bounds1['max_lon'], bounds2['max_lon']) -
                       max(bounds1['min_lon'], bounds2['min_lon']))
        y_overlap = max(0, min(bounds1['max_lat'], bounds2['max_lat']) -
                       max(bounds1['min_lat'], bounds2['min_lat']))

        if x_overlap == 0 or y_overlap == 0:
            return 0.0

        area1 = (bounds1['max_lon'] - bounds1['min_lon']) * (bounds1['max_lat'] - bounds1['min_lat'])
        overlap_area = x_overlap * y_overlap

        return min(1.0, overlap_area / area1) if area1 > 0 else 0.0

    @staticmethod
    def _transform_bounds(bounds: Dict, transformer) -> Dict:
        """Transform bounds using pyproj transformer."""
        corners = [
            (bounds['min_lon'], bounds['min_lat']),
            (bounds['max_lon'], bounds['max_lat'])
        ]
        transformed = [transformer.transform(x, y) for x, y in corners]
        return {
            'min_lon': min(t[0] for t in transformed),
            'max_lon': max(t[0] for t in transformed),
            'min_lat': min(t[1] for t in transformed),
            'max_lat': max(t[1] for t in transformed)
        }

    def _reproject_to_4326(self, file_path: str, is_raster: bool, source_crs: Optional[str] = None):
        """Reproject file to EPSG:4326."""
        if is_raster:
            output_path = str(Path(file_path).parent / f"{Path(file_path).stem}_4326.tif")
            gdal.Warp(output_path, file_path, dstSRS='EPSG:4326')
        else:
            gdf = gpd.read_file(file_path)
            if source_crs:
                gdf = gdf.set_crs(source_crs)
            gdf = gdf.to_crs('EPSG:4326')
            output_path = str(Path(file_path).parent / f"{Path(file_path).stem}_4326.gpkg")
            gdf.to_file(output_path, driver='GPKG')

    # =========================================================================
    # STAGE 3: Geometry Validation (vectors only)
    # =========================================================================

    async def stage_3_geometry_validation(self, file_path: str, db: Session) -> QAStageResult:
        """Validate and fix vector geometries."""
        logger.info(f"Stage 3: Geometry Validation - {file_path}")
        result = QAStageResult(
            stage_number=3,
            stage_name='Geometry Validation',
            status='pass'
        )

        try:
            if self._is_raster(file_path):
                result.warnings.append('Skipping geometry validation for raster dataset')
                return result

            gdf = gpd.read_file(file_path)

            # Check for NULL geometries
            null_geoms = gdf[gdf.geometry.isna()]
            if len(null_geoms) > 0:
                gdf = gdf[~gdf.geometry.isna()]
                result.status = 'auto_fixed'
                result.fixes_applied.append(FixRecord(
                    fix_type='null_geometry_removal',
                    description=f'Removed {len(null_geoms)} rows with NULL geometry',
                    before=str(len(gdf) + len(null_geoms)),
                    after=str(len(gdf))
                ))

            # Check for invalid geometries
            invalid_mask = ~gdf.geometry.is_valid
            if invalid_mask.any():
                gdf.loc[invalid_mask, 'geometry'] = gdf.loc[invalid_mask, 'geometry'].apply(
                    lambda geom: geom.buffer(0) if geom else geom
                )
                result.status = 'auto_fixed'
                result.fixes_applied.append(FixRecord(
                    fix_type='geometry_validation',
                    description=f'Fixed {invalid_mask.sum()} invalid geometries using buffer(0)',
                    before='invalid',
                    after='valid'
                ))

            # Remove Z/M dimensions
            gdf.geometry = gdf.geometry.apply(lambda geom: self._force_2d(geom))

            # Check for slivers (area < 1 sq meter)
            if gdf.geometry.type.str.contains('Polygon').any():
                slivers = gdf[gdf.geometry.area < 1]
                if len(slivers) > 0:
                    result.warnings.append(f'Detected {len(slivers)} sliver polygons (< 1 sq meter)')

            gdf.to_file(file_path, driver='GPKG', engine='fiona')

            return result

        except Exception as e:
            logger.error(f"Stage 3 error: {str(e)}")
            result.status = 'failed'
            result.failure_message = str(e)
            return result

    @staticmethod
    def _force_2d(geom):
        """Remove Z/M dimensions from geometry."""
        try:
            if hasattr(geom, 'has_z') and geom.has_z:
                return geom.simplify(0)
            return geom
        except Exception:
            return geom

    # =========================================================================
    # STAGE 4: Attribute Completeness
    # =========================================================================

    async def stage_4_attribute_completeness(self, file_path: str, slot_code: str, db: Session) -> QAStageResult:
        """Check attribute completeness and suggest fixes."""
        logger.info(f"Stage 4: Attribute Completeness - {file_path}")
        result = QAStageResult(
            stage_number=4,
            stage_name='Attribute Completeness',
            status='pass'
        )

        try:
            # Get required attributes for this slot
            # Placeholder: in production, query dataset_slots table
            required_attrs = self._get_required_attributes(slot_code, db)

            gdf = gpd.read_file(file_path)
            available_attrs = set(gdf.columns)

            missing_attrs = required_attrs - available_attrs
            candidates = {}

            for attr in missing_attrs:
                matches = self._find_attribute_candidates(attr, available_attrs)
                if matches:
                    candidates[attr] = matches
                    result.status = 'partial_fix_required'
                    result.partial_fix_data = candidates
                else:
                    result.status = 'failed'
                    result.failure_message = f'Required attribute "{attr}" not found and no candidates available'
                    return result

            # Auto-fix: normalize field names
            rename_map = {}
            for col in gdf.columns:
                normalized = col.strip().replace(' ', '_')[:10]
                if normalized != col:
                    rename_map[col] = normalized

            if rename_map:
                gdf = gdf.rename(columns=rename_map)
                result.status = 'auto_fixed'
                result.fixes_applied.append(FixRecord(
                    fix_type='field_normalization',
                    description=f'Normalized {len(rename_map)} field names',
                    before=str(list(rename_map.keys())),
                    after=str(list(rename_map.values()))
                ))

            # Auto-fix: cast numeric-looking fields
            for col in gdf.columns:
                if gdf[col].dtype == 'object':
                    try:
                        gdf[col] = pd.to_numeric(gdf[col])
                        result.fixes_applied.append(FixRecord(
                            fix_type='type_conversion',
                            description=f'Cast field "{col}" to numeric',
                            before='text',
                            after='numeric'
                        ))
                    except (ValueError, TypeError):
                        pass

            gdf.to_file(file_path, driver='GPKG', engine='fiona')
            return result

        except Exception as e:
            logger.error(f"Stage 4 error: {str(e)}")
            result.status = 'failed'
            result.failure_message = str(e)
            return result

    @staticmethod
    def _get_required_attributes(slot_code: str, db: Session) -> set:
        """Fetch required attributes for slot from database."""
        # Placeholder: implement actual DB query
        return {'name', 'type', 'value'}

    @staticmethod
    def _find_attribute_candidates(attr: str, available: set) -> List[str]:
        """Find candidate attributes using sequence matching."""
        candidates = []
        for col in available:
            ratio = difflib.SequenceMatcher(None, attr.lower(), col.lower()).ratio()
            if ratio >= 0.7:
                candidates.append((col, ratio))

        return [c[0] for c in sorted(candidates, key=lambda x: x[1], reverse=True)]

    # =========================================================================
    # STAGE 5: Spatial Coverage
    # =========================================================================

    async def stage_5_spatial_coverage(
        self, file_path: str, slot_code: str, aoi_geom: Dict, db: Session
    ) -> QAStageResult:
        """Check spatial coverage and merge with fallback if needed."""
        logger.info(f"Stage 5: Spatial Coverage - {file_path}")
        result = QAStageResult(
            stage_number=5,
            stage_name='Spatial Coverage',
            status='pass'
        )

        try:
            gdf = gpd.read_file(file_path)
            aoi_gdf = gpd.GeoDataFrame([{'geometry': gpd.geometry.shape(aoi_geom)}], crs='EPSG:4326')

            # Calculate intersection percentage
            intersection = gpd.clip(gdf, aoi_gdf)
            coverage_pct = (len(intersection) / len(gdf) * 100) if len(gdf) > 0 else 0

            if coverage_pct >= 80:
                return result

            if 60 <= coverage_pct < 80:
                # Merge with fallback
                fallback_source = self._get_fallback_source(slot_code, db)
                if fallback_source:
                    fallback_gdf = gpd.read_file(fallback_source)
                    merged = gpd.clip(fallback_gdf, aoi_gdf)
                    combined = gpd.pd.concat([gdf, merged], ignore_index=True)
                    combined.to_file(file_path, driver='GPKG')

                    result.status = 'auto_fixed'
                    result.fixes_applied.append(FixRecord(
                        fix_type='data_merge',
                        description=f'Merged with fallback dataset ({coverage_pct:.1f}% coverage)',
                        before=f"{len(gdf)} features",
                        after=f"{len(combined)} features"
                    ))
                    result.warnings.append(f'Coverage {coverage_pct:.1f}% merged with fallback source')
                    return result

            result.status = 'failed'
            result.failure_message = f'Spatial coverage {coverage_pct:.1f}% below 60% threshold'
            result.recommended_source = self._get_fallback_source(slot_code, db)
            return result

        except Exception as e:
            logger.error(f"Stage 5 error: {str(e)}")
            result.status = 'failed'
            result.failure_message = str(e)
            return result

    @staticmethod
    def _get_fallback_source(slot_code: str, db: Session) -> Optional[str]:
        """Fetch fallback source for slot from database."""
        # Placeholder: implement actual DB query
        return None

    # =========================================================================
    # STAGE 6: Quality Flags
    # =========================================================================

    async def stage_6_quality_flags(self, file_path: str, slot_code: str) -> QAStageResult:
        """Check quality metrics and flag issues."""
        logger.info(f"Stage 6: Quality Flags - {file_path}")
        result = QAStageResult(
            stage_number=6,
            stage_name='Quality Flags',
            status='pass'
        )

        try:
            is_raster = self._is_raster(file_path)

            if is_raster:
                return await self._check_raster_quality(file_path, result)
            else:
                return await self._check_vector_quality(file_path, result)

        except Exception as e:
            logger.error(f"Stage 6 error: {str(e)}")
            result.status = 'failed'
            result.failure_message = str(e)
            return result

    async def _check_raster_quality(self, file_path: str, result: QAStageResult) -> QAStageResult:
        """Check raster-specific quality metrics."""
        with rasterio.open(file_path) as src:
            data = src.read(1)
            meta = src.meta

            # Check NoData value
            if src.nodata is None:
                meta['nodata'] = -9999
                with rasterio.open(file_path, 'w', **meta) as dst:
                    dst.write(data, 1)

                result.status = 'auto_fixed'
                result.fixes_applied.append(FixRecord(
                    fix_type='nodata_assignment',
                    description='Assigned NoData value (-9999)',
                    before='None',
                    after='-9999'
                ))

            # Check metadata date
            tags = src.tags()
            if 'TIFFTAG_DATETIME' in tags:
                date_str = tags['TIFFTAG_DATETIME']
                data_date = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                age_years = (datetime.now() - data_date).days / 365.25

                if age_years > 5:
                    result.warnings.append(f'Data is {age_years:.1f} years old (> 5 years)')

                if 'volcanic' in file_path.lower() and data_date.year < 2018:
                    result.warnings.append('Volcanic zone data predates 2018-01-01 threshold')

            # Check for erroneous values
            nodata = src.nodata or -9999
            valid_data = data[data != nodata]
            if len(valid_data) > 0:
                erroneous = np.sum((valid_data < -100) | (valid_data > 1e10)) / len(valid_data)
                if erroneous > 0.30:
                    result.status = 'failed'
                    result.failure_message = f'{erroneous*100:.1f}% of values appear erroneous'
                    return result

        return result

    async def _check_vector_quality(self, file_path: str, result: QAStageResult) -> QAStageResult:
        """Check vector-specific quality metrics."""
        gdf = gpd.read_file(file_path)

        # Check metadata
        if hasattr(gdf, 'attrs'):
            if 'DATE' in gdf.attrs:
                date_str = gdf.attrs['DATE']
                try:
                    data_date = datetime.fromisoformat(date_str)
                    age_years = (datetime.now() - data_date).days / 365.25
                    if age_years > 5:
                        result.warnings.append(f'Data is {age_years:.1f} years old (> 5 years)')
                except Exception:
                    pass

        return result

    # =========================================================================
    # Main Pipeline
    # =========================================================================

    async def run_qa_pipeline(
        self,
        file_path: str,
        slot_code: str,
        aoi_geom: Optional[Dict],
        db: Session
    ) -> Dict:
        """Execute complete six-stage QA pipeline."""
        logger.info(f"Starting QA pipeline for {Path(file_path).name}")

        stages_results = []

        # Stage 1: Format and Readability
        result1 = await self.stage_1_format_and_readability(file_path)
        stages_results.append(result1)
        if result1.status == 'failed':
            return self._assemble_report(stages_results)
        if result1.recommended_source:
            file_path = result1.recommended_source

        # Stage 2: CRS and Projection
        result2 = await self.stage_2_crs_projection(file_path)
        stages_results.append(result2)

        # Stage 3: Geometry Validation
        result3 = await self.stage_3_geometry_validation(file_path, db)
        stages_results.append(result3)

        # Stage 4: Attribute Completeness
        result4 = await self.stage_4_attribute_completeness(file_path, slot_code, db)
        stages_results.append(result4)

        # Stage 5: Spatial Coverage
        if aoi_geom:
            result5 = await self.stage_5_spatial_coverage(file_path, slot_code, aoi_geom, db)
            stages_results.append(result5)
        else:
            stages_results.append(QAStageResult(
                stage_number=5,
                stage_name='Spatial Coverage',
                status='pass',
                warnings=['Skipped: no AOI geometry provided']
            ))

        # Stage 6: Quality Flags
        result6 = await self.stage_6_quality_flags(file_path, slot_code)
        stages_results.append(result6)

        return self._assemble_report(stages_results)

    def _assemble_report(self, stages: List[QAStageResult]) -> Dict:
        """Assemble complete QA report."""
        # Determine overall status
        statuses = [s.status for s in stages]
        if 'failed' in statuses:
            overall_status = 'failed'
        elif 'partial_fix_required' in statuses:
            overall_status = 'partial_fix_required'
        elif 'auto_fixed' in statuses:
            overall_status = 'auto_fixed'
        else:
            overall_status = 'pass'

        # Collect all fixes and warnings
        all_fixes = []
        all_warnings = []
        for stage in stages:
            all_fixes.extend(stage.fixes_applied)
            all_warnings.extend(stage.warnings)

        return {
            'overall_status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'upload_id': self.upload_id,
            'stage_results': [
                {
                    'stage_number': s.stage_number,
                    'stage_name': s.stage_name,
                    'status': s.status,
                    'fixes_applied': [
                        {
                            'fix_type': f.fix_type,
                            'description': f.description,
                            'before': f.before,
                            'after': f.after
                        } for f in s.fixes_applied
                    ],
                    'warnings': s.warnings,
                    'failure_message': s.failure_message,
                    'partial_fix_data': s.partial_fix_data
                } for s in stages
            ],
            'fix_log': all_fixes,
            'warnings': all_warnings,
            'fix_count': len(all_fixes)
        }


# Import pandas for type conversion helper
import pandas as pd
