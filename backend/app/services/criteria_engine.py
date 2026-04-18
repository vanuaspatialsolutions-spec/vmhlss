"""
Criteria Engine for Vanuatu Multi-Hazard Land Suitability System.

AHP + WLC + Boolean exclusion classification engine for suitability assessment.
"""

import logging
from typing import Dict, Tuple, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Development suitability criteria
DEVELOPMENT_CRITERIA = {
    'composite_hazard_index': {'weight': 0.35, 'invert': True},
    'slope_degrees': {'weight': 0.20, 'invert': True, 'threshold': 30},
    'distance_from_coast_m': {'weight': 0.15, 'invert': False, 'min_distance': 50},
    'soil_stability': {'weight': 0.15, 'invert': False},
    'lulc_compatibility': {'weight': 0.10, 'invert': False},
    'slr_1m_inundation': {'weight': 0.05, 'invert': True}
}

# Agriculture suitability criteria
AGRICULTURE_CRITERIA = {
    'soil_capability_class': {'weight': 0.30, 'invert': False},
    'composite_hazard_index': {'weight': 0.25, 'invert': True},
    'slope_degrees': {'weight': 0.20, 'invert': True, 'threshold': 25},
    'topographic_wetness_index': {'weight': 0.15, 'invert': False},
    'lulc_current': {'weight': 0.10, 'invert': False}
}

# Suitability class mapping
SCORE_TO_CLASS = {
    (0.80, 1.00): 'S1',
    (0.60, 0.80): 'S2',
    (0.40, 0.60): 'S3',
    (0.20, 0.40): 'S4',
    (0.00, 0.20): 'S5'
}

# Not Suitable class
NOT_SUITABLE = 'NS'


@dataclass
class KnowledgeBaseRecord:
    """Record from knowledge base."""
    record_id: str
    location: dict  # GeoJSON geometry
    confidence: float
    data_type: str  # 'engineering', 'soil', 'historical'
    findings: Dict
    source: str
    date: str


@dataclass
class CriteriaEngineResult:
    """Result from criteria engine analysis."""
    overall_class: str
    wlc_score: float
    class_percentages: Dict[str, float]
    ns_areas: List[str]
    wlc_breakdown: Dict[str, float]
    kb_records_used: List[str] = field(default_factory=list)
    criteria_rasters: Optional[Dict[str, str]] = None


class CriteriaEngine:
    """AHP + WLC + Boolean exclusion classification engine."""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Step 1: Boolean Exclusion
    # =========================================================================

    async def apply_boolean_exclusion(
        self,
        aoi_geom: dict,
        db: Session
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Apply boolean exclusion using Protected Areas (DS-08).

        Parameters
        ----------
        aoi_geom : dict
            Area of Interest geometry (GeoJSON-like)
        db : Session
            Database session

        Returns
        -------
        Tuple[np.ndarray, List[str]]
            (NS_mask, list of exclusion polygon names that triggered NS)
        """
        logger.info("Applying boolean exclusion (Protected Areas)")

        # Create AOI raster template
        aoi_gdf = gpd.GeoDataFrame(
            [{'geometry': gpd.geometry.shape(aoi_geom)}],
            crs='EPSG:4326'
        )

        # Load Protected Areas (DS-08)
        # Placeholder: in production, query datasets table for DS-08
        protected_areas_gdf = self._load_protected_areas(db)

        if protected_areas_gdf is None or len(protected_areas_gdf) == 0:
            logger.warning("No protected areas found")
            return np.zeros(1, dtype=np.uint8), []

        # Create NS mask
        ns_mask = np.zeros((100, 100), dtype=np.uint8)  # Placeholder dimensions
        triggered_exclusions = []

        # Find intersections
        intersecting = gpd.clip(protected_areas_gdf, aoi_gdf)

        if len(intersecting) > 0:
            ns_mask[:] = 1
            triggered_exclusions = intersecting['name'].tolist() if 'name' in intersecting.columns else ['Protected Area']

            logger.info(f"Boolean exclusion triggered: {len(triggered_exclusions)} areas")

        return ns_mask, triggered_exclusions

    def _load_protected_areas(self, db: Session) -> Optional[gpd.GeoDataFrame]:
        """Load Protected Areas dataset (DS-08) from database."""
        # Placeholder: implement actual DB query
        logger.info("Loading Protected Areas (DS-08)")
        return None

    # =========================================================================
    # Step 2: WLC Score Computation
    # =========================================================================

    @staticmethod
    def compute_wlc_score(
        criteria_values: Dict[str, np.ndarray],
        criteria_config: Dict
    ) -> np.ndarray:
        """
        Compute Weighted Linear Combination (WLC) score.

        WLC = sum(normalised_criterion_i * weight_i)
        For inverted criteria: score = 1 - normalised_value

        Parameters
        ----------
        criteria_values : Dict[str, np.ndarray]
            Dictionary of criterion rasters
        criteria_config : Dict
            Configuration with weights and invert flags

        Returns
        -------
        np.ndarray
            WLC score in range [0, 1]
        """
        logger.info("Computing WLC score")

        # Get dimensions from first criterion
        first_array = next(iter(criteria_values.values()))
        wlc_score = np.zeros_like(first_array, dtype=np.float32)

        total_weight = sum(c['weight'] for c in criteria_config.values())

        for criterion_name, criterion_data in criteria_values.items():
            if criterion_name not in criteria_config:
                logger.warning(f"No configuration for criterion '{criterion_name}'")
                continue

            config = criteria_config[criterion_name]
            weight = config['weight']
            invert = config.get('invert', False)

            # Normalise criterion
            valid_mask = criterion_data != -9999
            if not valid_mask.any():
                logger.warning(f"All NoData values in criterion '{criterion_name}'")
                continue

            valid_data = criterion_data[valid_mask]
            data_min = np.nanmin(valid_data)
            data_max = np.nanmax(valid_data)

            # Handle constant values
            if np.isclose(data_max, data_min):
                normalised = np.full_like(criterion_data, 0.5, dtype=np.float32)
            else:
                normalised = np.zeros_like(criterion_data, dtype=np.float32)
                normalised[valid_mask] = (valid_data - data_min) / (data_max - data_min)

            # Apply inversion if needed
            if invert:
                normalised = 1.0 - normalised

            # Apply threshold if specified
            if 'threshold' in config:
                threshold = config['threshold']
                normalised[criterion_data > threshold] = 0.0

            # Normalise weight and add to WLC
            normalised_weight = weight / total_weight
            wlc_score += normalised * normalised_weight

            logger.info(f"WLC: added '{criterion_name}' (weight={normalised_weight:.3f}, "
                       f"invert={invert})")

        # Clip to valid range
        wlc_score = np.clip(wlc_score, 0.0, 1.0)
        logger.info(f"WLC computed. Range: [{np.nanmin(wlc_score):.3f}, {np.nanmax(wlc_score):.3f}]")

        return wlc_score

    # =========================================================================
    # Step 3: Score to Class Mapping
    # =========================================================================

    @staticmethod
    def score_to_suitability_class(score: float) -> str:
        """
        Map WLC score to suitability class (S1-S5).

        Parameters
        ----------
        score : float
            WLC score in range [0, 1]

        Returns
        -------
        str
            Suitability class: S1, S2, S3, S4, or S5
        """
        for (low, high), class_name in sorted(SCORE_TO_CLASS.items()):
            if low <= score <= high:
                return class_name

        # Default to S5 if score < 0.0
        if score < 0.0:
            return 'S5'

        return 'S1'

    @staticmethod
    def score_array_to_classes(wlc_array: np.ndarray) -> np.ndarray:
        """
        Convert WLC score array to class array.

        Parameters
        ----------
        wlc_array : np.ndarray
            WLC scores

        Returns
        -------
        np.ndarray
            Class array (S1-S5 as strings)
        """
        class_array = np.empty_like(wlc_array, dtype='<U2')

        for (low, high), class_name in sorted(SCORE_TO_CLASS.items()):
            mask = (wlc_array >= low) & (wlc_array <= high)
            class_array[mask] = class_name

        # Handle edge cases
        class_array[wlc_array < 0.0] = 'S5'
        class_array[wlc_array > 1.0] = 'S1'

        return class_array

    # =========================================================================
    # Step 4: Knowledge Base Query
    # =========================================================================

    async def query_knowledge_base(
        self,
        aoi_geom: dict,
        db: Session
    ) -> Dict:
        """
        Query knowledge base for records intersecting AOI.

        Returns confirmed records and suggested adjustments.

        Parameters
        ----------
        aoi_geom : dict
            Area of Interest geometry
        db : Session
            Database session

        Returns
        -------
        Dict
            {
                'engineering_records': List[KnowledgeBaseRecord],
                'soil_records': List[KnowledgeBaseRecord],
                'soil_adjustments': Dict[str, float],
                'kb_used': List[str]
            }
        """
        logger.info("Querying knowledge base")

        # Create AOI GeoDataFrame
        aoi_gdf = gpd.GeoDataFrame(
            [{'geometry': gpd.geometry.shape(aoi_geom)}],
            crs='EPSG:4326'
        )

        # Placeholder: query knowledge_base_records table
        kb_records = self._query_kb_records(db, aoi_gdf)

        if not kb_records:
            logger.info("No knowledge base records found for AOI")
            return {
                'engineering_records': [],
                'soil_records': [],
                'soil_adjustments': {},
                'kb_used': []
            }

        engineering_records = [r for r in kb_records if r.data_type == 'engineering']
        soil_records = [r for r in kb_records if r.data_type == 'soil' and r.confidence >= 0.75]

        soil_adjustments = {}
        if soil_records:
            # Aggregate soil findings
            for record in soil_records:
                if 'soil_capability_class' in record.findings:
                    class_key = record.findings['soil_capability_class']
                    # Convert class to numeric for averaging
                    soil_adjustments[class_key] = soil_adjustments.get(class_key, 0) + record.confidence

        kb_used = [r.record_id for r in kb_records]
        logger.info(f"Knowledge base: {len(engineering_records)} engineering, "
                   f"{len(soil_records)} soil records")

        return {
            'engineering_records': engineering_records,
            'soil_records': soil_records,
            'soil_adjustments': soil_adjustments,
            'kb_used': kb_used
        }

    def _query_kb_records(self, db: Session, aoi_gdf: gpd.GeoDataFrame) -> List[KnowledgeBaseRecord]:
        """
        Query knowledge base records intersecting AOI.

        Placeholder: implement actual DB query.
        """
        logger.info("Querying knowledge_base_records table")
        return []

    # =========================================================================
    # Main Engine
    # =========================================================================

    async def run_criteria_engine(
        self,
        analysis_id: str,
        assessment_type: str,
        aoi_geom: dict,
        db: Session
    ) -> CriteriaEngineResult:
        """
        Run complete criteria engine: Boolean exclusion, WLC, KB integration.

        Parameters
        ----------
        analysis_id : str
            Unique analysis identifier
        assessment_type : str
            Type of assessment: 'development' or 'agriculture'
        aoi_geom : dict
            Area of Interest geometry
        db : Session
            Database session

        Returns
        -------
        CriteriaEngineResult
            Complete suitability assessment result
        """
        logger.info(f"Running criteria engine: {assessment_type} assessment")

        # Select criteria configuration
        if assessment_type == 'agriculture':
            criteria_config = AGRICULTURE_CRITERIA
        else:
            criteria_config = DEVELOPMENT_CRITERIA

        # Step 1: Apply boolean exclusion
        ns_mask, triggered_exclusions = await self.apply_boolean_exclusion(aoi_geom, db)
        logger.info(f"Boolean exclusion: {len(triggered_exclusions)} areas marked NS")

        # Step 2: Load criterion rasters and compute WLC
        criteria_rasters = await self._load_criteria_rasters(assessment_type, aoi_geom, db)

        if not criteria_rasters:
            logger.error("Could not load criteria rasters")
            return CriteriaEngineResult(
                overall_class='NS',
                wlc_score=0.0,
                class_percentages={},
                ns_areas=triggered_exclusions,
                wlc_breakdown={}
            )

        wlc_score = self.compute_wlc_score(criteria_rasters, criteria_config)

        # Step 3: Apply NS mask
        wlc_score[ns_mask == 1] = 0.0

        # Step 4: Query knowledge base for adjustments
        kb_info = await self.query_knowledge_base(aoi_geom, db)

        # Step 5: Map to suitability classes
        class_array = self.score_array_to_classes(wlc_score)
        class_array[ns_mask == 1] = 'NS'

        # Compute class percentages
        unique, counts = np.unique(class_array, return_counts=True)
        class_percentages = {
            cls: float(count / len(class_array) * 100)
            for cls, count in zip(unique, counts)
        }

        # Compute WLC breakdown (contribution of each criterion)
        wlc_breakdown = {}
        for criterion_name, config in criteria_config.items():
            wlc_breakdown[criterion_name] = {
                'weight': config['weight'],
                'invert': config.get('invert', False)
            }

        # Determine overall class (most common, excluding NS)
        non_ns_classes = class_array[class_array != 'NS']
        if len(non_ns_classes) > 0:
            overall_class = np.bincount(
                [int(c.replace('S', '')) for c in non_ns_classes],
                minlength=6
            ).argmax()
            overall_class = f'S{overall_class}' if overall_class > 0 else 'S5'
        else:
            overall_class = 'NS'

        logger.info(f"Criteria engine complete: Overall class = {overall_class}")

        return CriteriaEngineResult(
            overall_class=overall_class,
            wlc_score=float(np.nanmean(wlc_score[ns_mask == 0])),
            class_percentages=class_percentages,
            ns_areas=triggered_exclusions,
            wlc_breakdown=wlc_breakdown,
            kb_records_used=kb_info['kb_used'],
            criteria_rasters=criteria_rasters
        )

    async def _load_criteria_rasters(
        self,
        assessment_type: str,
        aoi_geom: dict,
        db: Session
    ) -> Dict[str, np.ndarray]:
        """
        Load all required criteria rasters for AOI.

        Placeholder: implement actual raster loading from database.
        """
        logger.info(f"Loading criteria rasters for {assessment_type} assessment")

        criteria_config = AGRICULTURE_CRITERIA if assessment_type == 'agriculture' else DEVELOPMENT_CRITERIA
        criteria_rasters = {}

        for criterion_name in criteria_config.keys():
            # In production:
            # 1. Query datasets table for raster matching criterion_name
            # 2. Load raster for AOI
            # 3. Reproject/resample to common grid if needed
            # 4. Store in dictionary

            logger.info(f"Loading criterion: {criterion_name}")

        return criteria_rasters

    # =========================================================================
    # Reporting
    # =========================================================================

    @staticmethod
    def generate_suitability_report(
        result: CriteriaEngineResult,
        analysis_id: str
    ) -> Dict:
        """
        Generate comprehensive suitability assessment report.

        Parameters
        ----------
        result : CriteriaEngineResult
            Result from criteria engine
        analysis_id : str
            Analysis identifier

        Returns
        -------
        Dict
            Complete report for output/storage
        """
        logger.info(f"Generating suitability report for {analysis_id}")

        return {
            'analysis_id': analysis_id,
            'overall_suitability_class': result.overall_class,
            'mean_wlc_score': result.wlc_score,
            'class_distribution': result.class_percentages,
            'exclusion_zones': result.ns_areas,
            'criteria_weights': result.wlc_breakdown,
            'knowledge_base_records_used': result.kb_records_used,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
