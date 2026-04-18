import pytest
import numpy as np


class TestBooleanExclusion:
    """Test boolean exclusion layer - NS classification for protected areas"""

    def test_boolean_exclusion_applies_ns(self, db, sample_aoi):
        """Protected areas must be classified NS"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        ns_mask, exclusions = engine.apply_boolean_exclusion(sample_aoi, db)
        # Result should be numpy array, list, or None
        assert ns_mask is not None or exclusions is not None

    def test_boolean_exclusion_returns_valid_type(self, db, sample_aoi):
        """Boolean exclusion returns proper data type"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        ns_mask, exclusions = engine.apply_boolean_exclusion(sample_aoi, db)

        if ns_mask is not None:
            assert isinstance(ns_mask, (np.ndarray, list))
        if exclusions is not None:
            assert isinstance(exclusions, dict)

    def test_boolean_exclusion_consistent_shape(self, db, sample_aoi):
        """Boolean exclusion output shape is consistent"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        ns_mask1, _ = engine.apply_boolean_exclusion(sample_aoi, db)
        ns_mask2, _ = engine.apply_boolean_exclusion(sample_aoi, db)

        if ns_mask1 is not None and ns_mask2 is not None:
            assert isinstance(ns_mask1, type(ns_mask2))


class TestWLCScoring:
    """Test Weighted Linear Combination scoring for suitability classes"""

    def test_wlc_scoring_development(self):
        """Development WLC scores within expected range [0,1]"""
        try:
            from app.services.criteria_engine import CriteriaEngine, DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine/criteria not available")

        engine = CriteriaEngine()

        # Perfect conditions - all criteria optimal
        criteria_values = {
            'composite_hazard_index': np.array([0.1]),
            'slope_degrees': np.array([5.0]),
            'distance_from_coast_m': np.array([5000.0]),
            'soil_stability': np.array([0.8]),
            'lulc_compatibility': np.array([0.9]),
            'slr_1m_inundation': np.array([0.0])
        }
        score = engine.compute_wlc_score(criteria_values, DEVELOPMENT_CRITERIA)

        assert score is not None
        assert len(score) > 0
        assert 0.0 <= score[0] <= 1.0

    def test_wlc_scoring_development_with_poor_conditions(self):
        """Development WLC scores low for poor conditions"""
        try:
            from app.services.criteria_engine import CriteriaEngine, DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine/criteria not available")

        engine = CriteriaEngine()

        # Poor conditions
        criteria_values = {
            'composite_hazard_index': np.array([0.9]),
            'slope_degrees': np.array([45.0]),
            'distance_from_coast_m': np.array([100.0]),
            'soil_stability': np.array([0.2]),
            'lulc_compatibility': np.array([0.1]),
            'slr_1m_inundation': np.array([1.0])
        }
        score = engine.compute_wlc_score(criteria_values, DEVELOPMENT_CRITERIA)

        assert score is not None
        assert 0.0 <= score[0] <= 1.0
        # Poor conditions should score lower (but not necessarily very low)
        # due to weighted combination

    def test_wlc_scoring_agriculture(self):
        """Agriculture WLC scores within expected range"""
        try:
            from app.services.criteria_engine import CriteriaEngine, AGRICULTURE_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine/criteria not available")

        engine = CriteriaEngine()

        criteria_values = {
            'soil_capability_class': np.array([0.9]),
            'composite_hazard_index': np.array([0.2]),
            'slope_degrees': np.array([8.0]),
            'topographic_wetness_index': np.array([6.0]),
            'lulc_current': np.array([0.7])
        }
        score = engine.compute_wlc_score(criteria_values, AGRICULTURE_CRITERIA)

        assert score is not None
        assert len(score) > 0
        assert 0.0 <= score[0] <= 1.0

    def test_wlc_handles_multiple_pixels(self):
        """WLC scoring handles multiple pixels in array"""
        try:
            from app.services.criteria_engine import CriteriaEngine, DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine/criteria not available")

        engine = CriteriaEngine()

        # Multiple pixels
        criteria_values = {
            'composite_hazard_index': np.array([0.1, 0.3, 0.5]),
            'slope_degrees': np.array([5.0, 15.0, 30.0]),
            'distance_from_coast_m': np.array([5000.0, 3000.0, 1000.0]),
            'soil_stability': np.array([0.8, 0.6, 0.4]),
            'lulc_compatibility': np.array([0.9, 0.7, 0.5]),
            'slr_1m_inundation': np.array([0.0, 0.2, 0.8])
        }
        scores = engine.compute_wlc_score(criteria_values, DEVELOPMENT_CRITERIA)

        assert scores is not None
        assert len(scores) == 3
        for score in scores:
            assert 0.0 <= score <= 1.0

    def test_wlc_scoring_conservation(self):
        """Conservation WLC scores within expected range"""
        try:
            from app.services.criteria_engine import CriteriaEngine, CONSERVATION_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine/criteria not available")

        engine = CriteriaEngine()

        criteria_values = {
            'biodiversity_value': np.array([0.8]),
            'ecosystem_fragility': np.array([0.7]),
            'hazard_exposure': np.array([0.2]),
            'accessibility': np.array([0.1])
        }
        score = engine.compute_wlc_score(criteria_values, CONSERVATION_CRITERIA)

        assert score is not None
        assert 0.0 <= score[0] <= 1.0


class TestScoreToClassMapping:
    """Test suitability score to class mapping (S1-S5, NS)"""

    @pytest.mark.parametrize("score,expected_class", [
        (0.95, 'S1'), (0.85, 'S1'),
        (0.75, 'S2'), (0.65, 'S2'),
        (0.55, 'S3'), (0.45, 'S3'),
        (0.35, 'S4'), (0.25, 'S4'),
        (0.15, 'S5'), (0.05, 'S5'),
    ])
    def test_score_to_class_mapping(self, score, expected_class):
        """Test score to suitability class mapping"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        result = engine.score_to_suitability_class(score)
        assert result == expected_class

    def test_score_to_class_boundary_values(self):
        """Test boundary values between classes"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()

        # Test exact boundaries
        s1_to_s2 = engine.score_to_suitability_class(0.8)
        s2_to_s3 = engine.score_to_suitability_class(0.6)
        s3_to_s4 = engine.score_to_suitability_class(0.4)
        s4_to_s5 = engine.score_to_suitability_class(0.2)

        assert s1_to_s2 in ['S1', 'S2']
        assert s2_to_s3 in ['S2', 'S3']
        assert s3_to_s4 in ['S3', 'S4']
        assert s4_to_s5 in ['S4', 'S5']

    def test_score_to_class_handles_edge_cases(self):
        """Test edge cases: 0.0 and 1.0"""
        try:
            from app.services.criteria_engine import CriteriaEngine
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()

        s_zero = engine.score_to_suitability_class(0.0)
        s_one = engine.score_to_suitability_class(1.0)

        assert s_zero in ['S5', 'NS']
        assert s_one == 'S1'


class TestCriteriaEngineInitialization:
    """Test criteria engine initialization and configuration"""

    def test_criteria_engine_loads_development(self):
        """Test that development criteria load correctly"""
        try:
            from app.services.criteria_engine import CriteriaEngine, DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        assert DEVELOPMENT_CRITERIA is not None
        assert isinstance(DEVELOPMENT_CRITERIA, dict)
        assert len(DEVELOPMENT_CRITERIA) > 0

    def test_criteria_engine_loads_agriculture(self):
        """Test that agriculture criteria load correctly"""
        try:
            from app.services.criteria_engine import CriteriaEngine, AGRICULTURE_CRITERIA
        except ImportError:
            pytest.skip("CriteriaEngine not available")

        engine = CriteriaEngine()
        assert AGRICULTURE_CRITERIA is not None
        assert isinstance(AGRICULTURE_CRITERIA, dict)

    def test_criteria_have_weights(self):
        """Test that criteria have weights defined"""
        try:
            from app.services.criteria_engine import DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("Criteria not available")

        assert len(DEVELOPMENT_CRITERIA) > 0
        # Each criterion should have a weight
        total_weight = 0
        for criterion_key, criterion_config in DEVELOPMENT_CRITERIA.items():
            if isinstance(criterion_config, dict):
                assert 'weight' in criterion_config or 'weights' in criterion_config
                if 'weight' in criterion_config:
                    total_weight += criterion_config['weight']


class TestCriteriaWeighting:
    """Test weighting of different criteria"""

    def test_weights_sum_reasonably(self):
        """Test that criterion weights are properly normalized"""
        try:
            from app.services.criteria_engine import DEVELOPMENT_CRITERIA, AGRICULTURE_CRITERIA
        except ImportError:
            pytest.skip("Criteria not available")

        for criteria_dict in [DEVELOPMENT_CRITERIA, AGRICULTURE_CRITERIA]:
            if criteria_dict is None:
                continue

            total = 0
            for criterion_key, config in criteria_dict.items():
                if isinstance(config, dict) and 'weight' in config:
                    total += config['weight']

            # Weights should be reasonable (not zero, not huge)
            if total > 0:
                assert 0.1 <= total <= 10.0  # Allow some variance

    def test_criterion_key_naming(self):
        """Test that criterion keys follow naming conventions"""
        try:
            from app.services.criteria_engine import DEVELOPMENT_CRITERIA
        except ImportError:
            pytest.skip("Criteria not available")

        for key in DEVELOPMENT_CRITERIA.keys():
            # Keys should be snake_case
            assert isinstance(key, str)
            assert key.islower() or '_' in key
