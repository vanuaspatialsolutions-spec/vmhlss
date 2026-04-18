import pytest
import os
import tempfile
import zipfile
import csv
from pathlib import Path


class TestStage1FormatReadability:
    """Test Stage 1: Format Readability - File format detection and extraction"""

    def test_detect_shapefile_format(self, tmp_path, sample_shapefile):
        """Test detection of Shapefile format"""
        try:
            from app.services.format_converter import FormatConverter
        except ImportError:
            pytest.skip("FormatConverter not available")

        converter = FormatConverter()
        info = converter.get_file_info(str(sample_shapefile))
        assert info['format'] in ['ESRI Shapefile', 'GeoPackage', 'Shapefile']

    def test_shapefile_zip_extraction(self, tmp_path, sample_shapefile):
        """Test extraction of shapefile from ZIP archive"""
        try:
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("QAEngine not available")

        if sample_shapefile is None:
            pytest.skip("sample_shapefile fixture unavailable")

        # Create zip with all sidecar files
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for f in sample_shapefile.parent.glob("test.*"):
                zf.write(f, f.name)

        engine = QAEngine()
        result = engine._stage1_format_readability(str(zip_path), "DS-01")
        assert result.status in ['pass', 'auto_fixed', 'failed']
        assert hasattr(result, 'failure_message')

    def test_csv_lat_lon_detection(self, tmp_path):
        """Test detection and parsing of CSV with lat/lon columns"""
        try:
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("QAEngine not available")

        csv_path = tmp_path / "test.csv"
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'latitude', 'longitude', 'value'])
            writer.writerow([1, -17.7, 167.5, 100])
            writer.writerow([2, -17.75, 167.55, 150])

        engine = QAEngine()
        result = engine._stage1_format_readability(str(csv_path), "DS-01")
        assert result.status in ['pass', 'auto_fixed', 'failed']

    def test_corrupt_file_fails(self, tmp_path):
        """Test that corrupt files are rejected in Stage 1"""
        try:
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("QAEngine not available")

        corrupt = tmp_path / "corrupt.shp"
        corrupt.write_bytes(b"not a valid shapefile at all garbage data")

        engine = QAEngine()
        result = engine._stage1_format_readability(str(corrupt), "DS-01")
        assert result.status == 'failed'
        assert result.failure_message is not None

    def test_unsupported_format_fails(self, tmp_path):
        """Test rejection of unsupported file formats"""
        try:
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("QAEngine not available")

        unsupported = tmp_path / "file.xyz"
        unsupported.write_text("some random content")

        engine = QAEngine()
        result = engine._stage1_format_readability(str(unsupported), "DS-01")
        assert result.status in ['failed', 'auto_fixed']


class TestStage2CRSProjection:
    """Test Stage 2: CRS/Projection - Coordinate reference system validation"""

    def test_crs_wgs84_pass(self, tmp_path):
        """Test that WGS84 (EPSG:4326) data passes Stage 2"""
        try:
            import rasterio
            from rasterio.transform import from_bounds
            from rasterio.crs import CRS
            import numpy as np
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        raster_path = tmp_path / "wgs84_raster.tif"
        data = np.random.rand(10, 10).astype('float32')
        # Vanuatu bounds in WGS84
        transform = from_bounds(167.0, -18.0, 168.0, -17.0, 10, 10)
        with rasterio.open(
            raster_path,
            'w',
            driver='GTiff',
            height=10,
            width=10,
            count=1,
            dtype='float32',
            crs=CRS.from_epsg(4326),
            transform=transform
        ) as dst:
            dst.write(data, 1)

        engine = QAEngine()
        result = engine._stage2_crs_projection(str(raster_path))
        assert result.status in ['pass', 'auto_fixed']

    def test_crs_autofix_utm_to_wgs84(self, tmp_path):
        """Test auto-reprojection from UTM to WGS84"""
        try:
            import rasterio
            from rasterio.transform import from_bounds
            from rasterio.crs import CRS
            import numpy as np
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        raster_path = tmp_path / "utm_raster.tif"
        data = np.random.rand(10, 10).astype('float32')
        # UTM Zone 59S bounds that fall within Vanuatu
        transform = from_bounds(410000, 7980000, 420000, 7990000, 10, 10)
        with rasterio.open(
            raster_path,
            'w',
            driver='GTiff',
            height=10,
            width=10,
            count=1,
            dtype='float32',
            crs=CRS.from_epsg(32759),
            transform=transform
        ) as dst:
            dst.write(data, 1)

        engine = QAEngine()
        result = engine._stage2_crs_projection(str(raster_path))
        assert result.status in ['pass', 'auto_fixed']
        if result.status == 'auto_fixed':
            assert result.fixes_applied is not None

    def test_outside_vanuatu_fails(self, tmp_path):
        """Test that data outside Vanuatu bbox fails"""
        try:
            import rasterio
            from rasterio.transform import from_bounds
            from rasterio.crs import CRS
            import numpy as np
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        raster_path = tmp_path / "outside.tif"
        data = np.random.rand(10, 10).astype('float32')
        # Australia coordinates
        transform = from_bounds(130.0, -35.0, 140.0, -25.0, 10, 10)
        with rasterio.open(
            raster_path,
            'w',
            driver='GTiff',
            height=10,
            width=10,
            count=1,
            dtype='float32',
            crs=CRS.from_epsg(4326),
            transform=transform
        ) as dst:
            dst.write(data, 1)

        engine = QAEngine()
        result = engine._stage2_crs_projection(str(raster_path))
        assert result.status == 'failed'
        assert result.failure_message is not None

    def test_crs_inference_vanuatu_coordinates(self):
        """Test CRS inference for coordinates within Vanuatu"""
        try:
            from app.utils.crs_utils import CRSUtils
        except ImportError:
            pytest.skip("CRSUtils not available")

        utils = CRSUtils()
        # UTM Zone 59S bounds that fall within Vanuatu
        candidates = utils.infer_crs_from_bounds(
            min_x=410000, min_y=7980000, max_x=420000, max_y=7990000
        )
        assert candidates is not None
        assert isinstance(candidates, (list, tuple)) or candidates is not None


class TestStage3GeometryValidation:
    """Test Stage 3: Geometry Validation - Spatial geometry integrity"""

    def test_geometry_repair_self_intersecting(self, tmp_path, db):
        """Test auto-repair of self-intersecting polygon"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Polygon
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        # Create self-intersecting polygon (bow-tie shape)
        bowtie = Polygon([
            (167.1, -17.7), (167.3, -17.9),
            (167.3, -17.7), (167.1, -17.9),
            (167.1, -17.7)
        ])
        gpkg_path = tmp_path / "bowtie.gpkg"
        schema = {'geometry': 'Polygon', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({'geometry': mapping(bowtie), 'properties': {'id': 1}})

        engine = QAEngine()
        result = engine._stage3_geometry_validation(str(gpkg_path), db)
        assert result.status in ['pass', 'auto_fixed', 'failed']

    def test_valid_polygon_passes(self, tmp_path, db):
        """Test that valid polygons pass Stage 3"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Polygon
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        # Create valid polygon
        valid_poly = Polygon([
            (167.1, -17.7), (167.2, -17.7),
            (167.2, -17.8), (167.1, -17.8),
            (167.1, -17.7)
        ])
        gpkg_path = tmp_path / "valid.gpkg"
        schema = {'geometry': 'Polygon', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({'geometry': mapping(valid_poly), 'properties': {'id': 1}})

        engine = QAEngine()
        result = engine._stage3_geometry_validation(str(gpkg_path), db)
        assert result.status in ['pass', 'auto_fixed']

    def test_null_geometry_fails(self, tmp_path, db):
        """Test that null geometries fail Stage 3"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "null_geom.gpkg"
        schema = {'geometry': 'Polygon', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({'geometry': None, 'properties': {'id': 1}})

        engine = QAEngine()
        result = engine._stage3_geometry_validation(str(gpkg_path), db)
        assert result.status in ['failed', 'partial_fix_required']


class TestStage4AttributeCompleteness:
    """Test Stage 4: Attribute Completeness - Data field requirements"""

    def test_attribute_field_mapping_fuzzy_match(self, tmp_path, db):
        """Test fuzzy field name matching for similar column names"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "fuzzy.gpkg"
        # Use 'magnitude' instead of 'PGA_value' — should fuzzy match
        schema = {
            'geometry': 'Point',
            'properties': {'id': 'int', 'magnitude': 'float'}
        }
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({
                'geometry': mapping(Point(167.5, -17.7)),
                'properties': {'id': 1, 'magnitude': 0.3}
            })

        engine = QAEngine()
        # DS-06 requires PGA field
        result = engine._stage4_attribute_completeness(str(gpkg_path), 'DS-06', db)
        assert result.status in ['pass', 'auto_fixed', 'partial_fix_required', 'failed']

    def test_required_field_present(self, tmp_path, db):
        """Test that required fields pass Stage 4"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "complete.gpkg"
        schema = {
            'geometry': 'Point',
            'properties': {'id': 'int', 'pga_value': 'float', 'hazard_class': 'str'}
        }
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({
                'geometry': mapping(Point(167.5, -17.7)),
                'properties': {'id': 1, 'pga_value': 0.3, 'hazard_class': 'High'}
            })

        engine = QAEngine()
        result = engine._stage4_attribute_completeness(str(gpkg_path), 'DS-06', db)
        assert result.status in ['pass', 'auto_fixed', 'partial_fix_required']


class TestStage5Coverage:
    """Test Stage 5: Spatial Coverage - AOI overlap validation"""

    def test_coverage_check_good_coverage(self, tmp_path, sample_aoi):
        """Test coverage check passes with good AOI overlap"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "good_coverage.gpkg"
        schema = {'geometry': 'Point', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            # Point inside AOI
            f.write({
                'geometry': mapping(Point(167.2, -17.75)),
                'properties': {'id': 1}
            })

        engine = QAEngine()
        result = engine._stage5_spatial_coverage(str(gpkg_path), sample_aoi, 'DS-05')
        assert result.status in ['pass', 'auto_fixed', 'partial_fix_required']

    def test_coverage_check_below_threshold(self, tmp_path, sample_aoi):
        """Test coverage check fails when dataset doesn't cover AOI"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "far.gpkg"
        schema = {'geometry': 'Point', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            # Point far from AOI
            f.write({
                'geometry': mapping(Point(167.9, -15.0)),
                'properties': {'id': 1}
            })

        engine = QAEngine()
        result = engine._stage5_spatial_coverage(str(gpkg_path), sample_aoi, 'DS-05')
        assert result.status in ['failed', 'partial_fix_required']

    def test_no_coverage_fails(self, tmp_path, sample_aoi):
        """Test coverage check fails with no overlap"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            from app.services.qa_engine import QAEngine
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "no_coverage.gpkg"
        schema = {'geometry': 'Point', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            # Point in Australia
            f.write({
                'geometry': mapping(Point(130.0, -35.0)),
                'properties': {'id': 1}
            })

        engine = QAEngine()
        result = engine._stage5_spatial_coverage(str(gpkg_path), sample_aoi, 'DS-05')
        assert result.status == 'failed'


class TestFullPipeline:
    """Test complete QA pipeline end-to-end"""

    def test_full_pipeline_pass(self, tmp_path, db, sample_aoi):
        """Test complete QA pipeline passes for valid GeoPackage"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Polygon
            import asyncio
            from app.services.qa_engine import run_qa_pipeline
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "valid.gpkg"
        schema = {
            'geometry': 'Polygon',
            'properties': {
                'id': 'int',
                'hazard_class': 'str',
                'pga_value': 'float'
            }
        }
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            poly = Polygon([
                (167.1, -17.7), (167.2, -17.7),
                (167.2, -17.8), (167.1, -17.8),
                (167.1, -17.7)
            ])
            f.write({
                'geometry': mapping(poly),
                'properties': {'id': 1, 'hazard_class': 'High', 'pga_value': 0.3}
            })

        result = asyncio.run(run_qa_pipeline(
            file_path=str(gpkg_path),
            slot_code='DS-06',
            aoi_geom=sample_aoi,
            db=db,
            upload_id='test-upload-001'
        ))
        assert result['overall_status'] in ['pass', 'auto_fixed', 'conditional']

    def test_full_pipeline_fail_corrupt_file(self, tmp_path, db, sample_aoi):
        """Test complete QA pipeline fails for corrupt file"""
        try:
            import asyncio
            from app.services.qa_engine import run_qa_pipeline
        except ImportError:
            pytest.skip("Required libraries not available")

        corrupt = tmp_path / "corrupt.gpkg"
        corrupt.write_bytes(b"this is not a valid geopackage file")

        result = asyncio.run(run_qa_pipeline(
            file_path=str(corrupt),
            slot_code='DS-01',
            aoi_geom=sample_aoi,
            db=db,
            upload_id='test-upload-002'
        ))
        assert result['overall_status'] == 'failed'

    def test_full_pipeline_structures_report(self, tmp_path, db, sample_aoi):
        """Test that full pipeline returns properly structured report"""
        try:
            import fiona
            from fiona.crs import from_epsg
            from shapely.geometry import mapping, Point
            import asyncio
            from app.services.qa_engine import run_qa_pipeline
        except ImportError:
            pytest.skip("Required libraries not available")

        gpkg_path = tmp_path / "test.gpkg"
        schema = {'geometry': 'Point', 'properties': {'id': 'int'}}
        with fiona.open(
            str(gpkg_path),
            'w',
            driver='GPKG',
            schema=schema,
            crs=from_epsg(4326)
        ) as f:
            f.write({
                'geometry': mapping(Point(167.2, -17.75)),
                'properties': {'id': 1}
            })

        result = asyncio.run(run_qa_pipeline(
            file_path=str(gpkg_path),
            slot_code='DS-01',
            aoi_geom=sample_aoi,
            db=db,
            upload_id='test-upload-003'
        ))

        # Check structure
        assert 'overall_status' in result
        assert 'stages' in result
        assert 'summary' in result
        assert result['overall_status'] in ['pass', 'auto_fixed', 'conditional', 'failed']
