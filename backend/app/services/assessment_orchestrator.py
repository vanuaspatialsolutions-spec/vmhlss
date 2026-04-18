"""
Assessment Orchestrator Service

Coordinates the entire land suitability assessment workflow:
1. Data validation and preparation
2. Composite hazard indexing
3. Weighted linear combination (WLC) suitability analysis
4. Knowledge base integration
5. Persona analysis generation
6. Report assembly and export
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import numpy as np
import geopandas as gpd
from shapely.geometry import shape, mapping
from sqlalchemy.orm import Session

from app.services.document_intelligence import process_document
from app.services.knowledge_base import (
    query_kb_for_aoi,
    get_kb_stats,
    confirm_kb_record
)
from app.services.georeferencing import detect_gcps, compute_transformation, digitise_features
from app.services.persona_engine import run_all_personas
from app.services.report_generator import (
    generate_report_reference,
    generate_pdf_report,
    export_as_shapefile,
    export_as_geojson,
    export_as_geopackage
)

logger = logging.getLogger(__name__)


class AssessmentOrchestrator:
    """
    Coordinates multi-step land suitability assessment workflow.
    """

    def __init__(self, db: Session):
        """Initialize orchestrator with database session."""
        self.db = db
        self.assessment_id = None
        self.assessment_data = {}

    def validate_aoi(self, aoi_geom: Dict) -> Tuple[bool, List[str]]:
        """
        Validate Area of Interest geometry.

        Checks:
        - Valid GeoJSON format
        - Geometry type (Polygon or MultiPolygon)
        - Coordinates within Vanuatu bounds
        - Area > 0.1 ha

        Returns (is_valid, error_messages)
        """
        logger.info("Validating AOI geometry")

        errors = []

        try:
            geom = shape(aoi_geom)
        except Exception as e:
            return False, [f"Invalid GeoJSON geometry: {e}"]

        if geom.geom_type not in ['Polygon', 'MultiPolygon']:
            errors.append(f"Unsupported geometry type: {geom.geom_type}")

        # Check bounds (rough Vanuatu extent)
        bounds = geom.bounds  # (minx, miny, maxx, maxy)
        if not (160 <= bounds[0] and bounds[2] <= 175 and -22 <= bounds[1] and bounds[3] <= -12):
            errors.append("Geometry outside Vanuatu extent (160-175E, 12-22S)")

        # Check area
        area_ha = geom.area * 10000  # Convert degrees² to hectares (rough)
        if area_ha < 0.1:
            errors.append(f"Area too small: {area_ha:.4f} ha (minimum 0.1 ha)")

        if errors:
            return False, errors

        logger.info(f"AOI validation passed: {area_ha:.1f} ha")
        return True, []

    def compute_composite_hazard_index(
        self,
        aoi_geom: Dict,
        hazard_layers: Dict[str, float]
    ) -> Dict:
        """
        Compute Composite Hazard Index (CHI) from multiple hazard layers.

        Combines hazard scores using normalized weights:
        - Cyclone: 0.25 (strongest impact in Vanuatu)
        - Tsunami: 0.20 (coastal risk)
        - Volcanic: 0.15 (fixed hazard zones)
        - Flood: 0.15 (rainfall-dependent)
        - Earthquake: 0.15 (seismic activity)
        - Landslide: 0.10 (slope + rainfall interaction)

        Args:
            aoi_geom: AOI boundary as GeoJSON
            hazard_layers: Dict mapping hazard type to score (0.0-1.0)

        Returns:
            Dict with individual hazard scores and composite score
        """
        logger.info("Computing Composite Hazard Index")

        # Default weights (AHP-derived)
        weights = {
            'cyclone': 0.25,
            'tsunami': 0.20,
            'volcanic': 0.15,
            'flood': 0.15,
            'earthquake': 0.15,
            'landslide': 0.10
        }

        # Normalize hazard scores to [0, 1]
        normalized_scores = {}
        for hazard_type, weight in weights.items():
            score = hazard_layers.get(hazard_type, 0.0)
            normalized_scores[hazard_type] = max(0.0, min(1.0, float(score)))

        # Compute weighted composite
        composite = sum(
            normalized_scores.get(h, 0.0) * w
            for h, w in weights.items()
        )

        chi_result = {
            'composite_score': float(composite),
            'cyclone': normalized_scores.get('cyclone', 0.0),
            'tsunami': normalized_scores.get('tsunami', 0.0),
            'volcanic': normalized_scores.get('volcanic', 0.0),
            'flood': normalized_scores.get('flood', 0.0),
            'earthquake': normalized_scores.get('earthquake', 0.0),
            'landslide': normalized_scores.get('landslide', 0.0),
            'weights': weights,
            'computation_date': datetime.utcnow().isoformat()
        }

        logger.info(f"CHI Score: {composite:.3f}")

        return chi_result

    def compute_wlc_suitability(
        self,
        chi_score: float,
        fao_class: str,
        engineering_score: float,
        policy_constraints: List[str]
    ) -> Dict:
        """
        Compute Weighted Linear Combination (WLC) suitability score.

        Combines multiple criteria:
        - Hazard Index (weight: 0.40) - inverse (lower hazard = higher suitability)
        - FAO Land Capability (weight: 0.35) - direct conversion S1-N2 to score
        - Engineering Suitability (weight: 0.20) - user-provided assessment
        - Policy Score (weight: 0.05) - constraints reduce suitability

        FAO Class to Score Mapping:
        S1: 1.0, S2: 0.85, S3: 0.65, S4: 0.35, S5: 0.15, N1/N2: 0.0

        Output Classification:
        >= 0.75: S1 (Highly suitable)
        0.60-0.75: S2 (Suitable)
        0.45-0.60: S3 (Moderately suitable)
        0.25-0.45: S4 (Marginally suitable)
        0.10-0.25: S5 (Currently not suitable)
        < 0.10: NS (Not suitable)

        Args:
            chi_score: Composite Hazard Index (0.0-1.0)
            fao_class: FAO Land Capability Class (S1-N2)
            engineering_score: Engineering suitability (0.0-1.0)
            policy_constraints: List of constraint descriptions

        Returns:
            Dict with WLC score and suitability class
        """
        logger.info("Computing WLC Suitability Score")

        # FAO class to score
        fao_scores = {
            'S1': 1.0, 'S2': 0.85, 'S3': 0.65, 'S4': 0.35, 'S5': 0.15,
            'N1': 0.0, 'N2': 0.0
        }
        fao_score = fao_scores.get(fao_class, 0.5)

        # Hazard score (inverse: high hazard = low suitability)
        hazard_score = 1.0 - chi_score

        # Policy score (reduce for constraints)
        policy_penalty = len(policy_constraints) * 0.05
        policy_score = max(0.0, 1.0 - policy_penalty)

        # WLC computation
        wlc_score = (
            0.40 * hazard_score +
            0.35 * fao_score +
            0.20 * engineering_score +
            0.05 * policy_score
        )

        # Classify suitability
        if wlc_score >= 0.75:
            suitability_class = 'S1'
        elif wlc_score >= 0.60:
            suitability_class = 'S2'
        elif wlc_score >= 0.45:
            suitability_class = 'S3'
        elif wlc_score >= 0.25:
            suitability_class = 'S4'
        elif wlc_score >= 0.10:
            suitability_class = 'S5'
        else:
            suitability_class = 'NS'

        result = {
            'wlc_score': float(wlc_score),
            'overall_class': suitability_class,
            'component_scores': {
                'hazard': float(hazard_score),
                'fao_capability': float(fao_score),
                'engineering': float(engineering_score),
                'policy': float(policy_score)
            },
            'fao_class': fao_class,
            'policy_constraints': policy_constraints,
            'computation_date': datetime.utcnow().isoformat()
        }

        logger.info(f"WLC Score: {wlc_score:.3f} → Class {suitability_class}")

        return result

    def run_assessment(
        self,
        assessment_params: Dict,
        user_id: str
    ) -> Dict:
        """
        Execute complete assessment workflow.

        Args:
            assessment_params: Dict containing:
                - aoi_geom: GeoJSON geometry
                - aoi_name: Area name
                - province: Province name
                - island: Island name
                - elevation_m: Elevation in meters
                - annual_rainfall_mm: Annual rainfall
                - hazard_layers: {cyclone, tsunami, ...: scores}
                - fao_class: FAO Land Capability Class
                - engineering_score: Engineering suitability (0-1)
                - policy_constraints: List of constraint names
                - assessment_type: 'development' | 'agriculture' | 'both'
                - requested_personas: List of persona names
                - generate_report: bool
                - export_formats: List of export formats (shp, geojson, gpkg)
            user_id: User ID performing assessment

        Returns:
            Dict with complete assessment results
        """
        logger.info(f"Starting assessment: {assessment_params.get('aoi_name')}")

        # 1. Validate AOI
        is_valid, errors = self.validate_aoi(assessment_params['aoi_geom'])
        if not is_valid:
            raise ValueError(f"Invalid AOI: {', '.join(errors)}")

        # 2. Compute Composite Hazard Index
        chi_result = self.compute_composite_hazard_index(
            assessment_params['aoi_geom'],
            assessment_params.get('hazard_layers', {})
        )

        # 3. Compute WLC Suitability
        suitability_result = self.compute_wlc_suitability(
            chi_result['composite_score'],
            assessment_params.get('fao_class', 'S3'),
            assessment_params.get('engineering_score', 0.5),
            assessment_params.get('policy_constraints', [])
        )

        # 4. Query Knowledge Base
        kb_records = query_kb_for_aoi(
            assessment_params['aoi_geom'],
            ['HAZARD_EVENT', 'HAZARD_ZONE', 'SOIL_DATA', 'ENGINEERING_DATA', 'POLICY_LEGAL'],
            self.db
        )

        logger.info(f"KB records: {len(kb_records)}")

        # 5. Build assessment data
        self.assessment_data = {
            'aoi_name': assessment_params.get('aoi_name', 'Unnamed'),
            'province': assessment_params.get('province', 'Unknown'),
            'island': assessment_params.get('island', 'Unknown'),
            'aoi_area_ha': assessment_params.get('aoi_area_ha', 0),
            'elevation_m': assessment_params.get('elevation_m', 0),
            'annual_rainfall_mm': assessment_params.get('annual_rainfall_mm', 0),
            'dominant_soil_type': assessment_params.get('dominant_soil_type', 'Not determined'),
            'result_geom': assessment_params['aoi_geom'],
            'chi_result': chi_result,
            'suitability_result': suitability_result,
            'kb_records': kb_records,
            'assessment_type': assessment_params.get('assessment_type', 'both'),
            'assessment_date': datetime.utcnow().isoformat(),
            'assessment_by': user_id,
            'auto_fixes': [],
            'datasets_used': assessment_params.get('datasets_used', [])
        }

        # 6. Run personas
        requested_personas = assessment_params.get('requested_personas', [])
        if requested_personas:
            logger.info(f"Running {len(requested_personas)} personas")
            persona_responses = run_all_personas(
                self.assessment_data,
                requested_personas,
                kb_records,
                self.db
            )
            self.assessment_data['persona_responses'] = persona_responses

        # 7. Generate report
        if assessment_params.get('generate_report', False):
            logger.info("Generating PDF report")
            report_ref = generate_report_reference(self.db)
            report_path = f"/tmp/vmhlss_report_{report_ref}.pdf"

            generate_pdf_report(
                self.assessment_data,
                language='en',
                personas=requested_personas,
                output_path=report_path,
                db=self.db
            )
            self.assessment_data['report_path'] = report_path
            self.assessment_data['report_reference'] = report_ref

        # 8. Export formats
        export_formats = assessment_params.get('export_formats', [])
        export_paths = {}

        if 'geojson' in export_formats:
            geojson_str = export_as_geojson(self.assessment_data)
            export_paths['geojson'] = geojson_str

        if 'shp' in export_formats or 'shapefile' in export_formats:
            shp_path = export_as_shapefile(self.assessment_data, '/tmp/vmhlss_exports')
            export_paths['shapefile'] = shp_path

        if 'gpkg' in export_formats or 'geopackage' in export_formats:
            gpkg_path = export_as_geopackage(self.assessment_data, '/tmp/vmhlss_exports')
            export_paths['geopackage'] = gpkg_path

        self.assessment_data['exports'] = export_paths

        logger.info(f"Assessment complete: {assessment_params.get('aoi_name')}")

        return self.assessment_data

    def process_and_integrate_document(
        self,
        file_path: str,
        document_name: str,
        user_id: str
    ) -> Dict:
        """
        Process uploaded document and extract knowledge base records.

        Supports: PDF, DOCX, XLSX, PNG, JPG, TIFF

        Args:
            file_path: Path to uploaded file
            document_name: Name for the document
            user_id: User ID extracting document

        Returns:
            Dict with extraction results and record IDs
        """
        logger.info(f"Processing document: {document_name}")

        result = process_document(
            file_path,
            document_name,
            user_id,
            self.db
        )

        logger.info(f"Document processing complete: {len(result['record_ids'])} records created")

        return result

    def process_map_image(
        self,
        image_path: str,
        output_dir: str
    ) -> Dict:
        """
        Georeference a map image and digitise features.

        Args:
            image_path: Path to map image
            output_dir: Directory for georeferenced image and features

        Returns:
            Dict with georeferencing and digitization results
        """
        logger.info(f"Processing map image: {image_path}")

        # Detect GCPs
        gcps = detect_gcps(image_path)

        if len(gcps) < 2:
            raise ValueError(f"Insufficient GCPs detected: {len(gcps)} (minimum 2)")

        logger.info(f"Detected {len(gcps)} GCPs")

        # Compute transformation
        georef_path = f"{output_dir}/georeferenced_map.tif"
        transform_result = compute_transformation(gcps, image_path, georef_path)

        # Digitise features
        features_path = f"{output_dir}/digitised_features.gpkg"
        digitise_result = digitise_features(georef_path, features_path)

        result = {
            'georeferencing': transform_result,
            'digitisation': digitise_result,
            'gcp_count': len(gcps),
            'georeferenced_image': georef_path,
            'features_geopackage': features_path
        }

        logger.info(f"Map image processing complete")

        return result

    def confirm_kb_records(
        self,
        record_ids: List[str],
        user_id: str
    ) -> Dict:
        """
        Confirm multiple knowledge base records.

        Args:
            record_ids: List of record IDs to confirm
            user_id: User ID confirming records

        Returns:
            Dict with confirmation results
        """
        logger.info(f"Confirming {len(record_ids)} KB records")

        confirmed = 0
        failed = 0

        for record_id in record_ids:
            try:
                if confirm_kb_record(record_id, user_id, self.db):
                    confirmed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.warning(f"Failed to confirm {record_id}: {e}")
                failed += 1

        result = {
            'confirmed_count': confirmed,
            'failed_count': failed,
            'total': len(record_ids)
        }

        logger.info(f"Confirmation complete: {confirmed} confirmed, {failed} failed")

        return result

    def get_kb_statistics(self) -> Dict:
        """Get knowledge base statistics."""
        logger.info("Retrieving KB statistics")
        return get_kb_stats(self.db)
