"""
Hazard Modelling Service for Vanuatu Multi-Hazard Land Suitability System.

Composite Hazard Index (CHI) computation and hazard layer analysis.
"""

import logging
from typing import Dict, Optional, Tuple
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile
import geopandas as gpd
from osgeo import gdal
from scipy import ndimage
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Hazard weights (must sum to 1.0)
HAZARD_WEIGHTS = {
    'cyclone':    0.25,
    'tsunami':    0.20,
    'volcanic':   0.20,
    'flood':      0.15,
    'earthquake': 0.12,
    'landslide':  0.08
}

# Suitability class mapping
SCORE_TO_CLASS = {
    (0.80, 1.00): 'S1',
    (0.60, 0.80): 'S2',
    (0.40, 0.60): 'S3',
    (0.20, 0.40): 'S4',
    (0.00, 0.20): 'S5'
}


class HazardModellingService:
    """Service for computing composite hazard indices and DEM derivatives."""

    def __init__(self):
        # Validate weights sum to 1.0
        weight_sum = sum(HAZARD_WEIGHTS.values())
        if not np.isclose(weight_sum, 1.0):
            logger.warning(f"Hazard weights sum to {weight_sum}, not 1.0. Normalising...")
            total = sum(HAZARD_WEIGHTS.values())
            self.weights = {k: v / total for k, v in HAZARD_WEIGHTS.items()}
        else:
            self.weights = HAZARD_WEIGHTS

    # =========================================================================
    # Normalisation and Composition
    # =========================================================================

    @staticmethod
    def normalise_hazard_layer(data: np.ndarray, nodata_val: float = -9999) -> np.ndarray:
        """
        Min-max normalisation of hazard layer to 0.0-1.0 range.

        Parameters
        ----------
        data : np.ndarray
            Input hazard layer data
        nodata_val : float
            NoData value to exclude from normalisation

        Returns
        -------
        np.ndarray
            Normalised data in range [0, 1]
        """
        # Mask NoData values
        valid_mask = data != nodata_val
        if not valid_mask.any():
            logger.warning("All values are NoData in hazard layer")
            return np.zeros_like(data, dtype=np.float32)

        valid_data = data[valid_mask]
        data_min = np.nanmin(valid_data)
        data_max = np.nanmax(valid_data)

        # Handle constant values
        if np.isclose(data_max, data_min):
            logger.warning("Hazard layer has constant values")
            normalised = np.full_like(data, 0.5, dtype=np.float32)
            normalised[~valid_mask] = 0.0
            return normalised

        # Min-max normalisation
        normalised = np.zeros_like(data, dtype=np.float32)
        normalised[valid_mask] = (valid_data - data_min) / (data_max - data_min)
        normalised[~valid_mask] = 0.0

        return np.clip(normalised, 0.0, 1.0)

    def compute_chi(
        self,
        hazard_arrays: Dict[str, np.ndarray],
        weights: Optional[Dict[str, float]] = None,
        nodata: float = -9999
    ) -> np.ndarray:
        """
        Compute Composite Hazard Index (CHI).

        CHI = sum(normalised_hazard_i * weight_i) for all hazard types.

        Parameters
        ----------
        hazard_arrays : Dict[str, np.ndarray]
            Dictionary of hazard layers {hazard_type: data_array}
        weights : Dict[str, float], optional
            Custom weights; defaults to HAZARD_WEIGHTS
        nodata : float
            NoData value

        Returns
        -------
        np.ndarray
            Composite hazard index in range [0, 1]
        """
        if weights is None:
            weights = self.weights

        # Get first array shape for output
        first_array = next(iter(hazard_arrays.values()))
        chi = np.zeros_like(first_array, dtype=np.float32)

        for hazard_type, data in hazard_arrays.items():
            if hazard_type not in weights:
                logger.warning(f"No weight defined for hazard type '{hazard_type}', skipping")
                continue

            # Normalise hazard layer
            normalised = self.normalise_hazard_layer(data, nodata)

            # Add weighted contribution
            weight = weights[hazard_type]
            chi += normalised * weight

            logger.info(f"CHI: added {hazard_type} (weight={weight:.2f})")

        # Clip to valid range
        chi = np.clip(chi, 0.0, 1.0)

        logger.info(f"CHI computed. Range: [{np.nanmin(chi):.3f}, {np.nanmax(chi):.3f}]")
        return chi

    # =========================================================================
    # DEM Derivatives
    # =========================================================================

    @staticmethod
    def compute_dem_derivatives(dem_path: str, output_dir: str) -> Dict[str, str]:
        """
        Compute DEM-derived layers: slope, flow accumulation, TWI, stream network.

        Parameters
        ----------
        dem_path : str
            Path to input DEM file
        output_dir : str
            Output directory for derivative files

        Returns
        -------
        Dict[str, str]
            Dictionary of output file paths:
            {'slope': path, 'flow_accumulation': path, 'twi': path, 'stream_network': path}
        """
        logger.info(f"Computing DEM derivatives from {dem_path}")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        outputs = {}

        # 1. Compute Slope using GDAL
        slope_path = str(output_dir / 'slope_degrees.tif')
        logger.info("Computing slope...")
        gdal.DEMProcessing(
            slope_path,
            dem_path,
            'slope',
            slopeFormat='degree',
            azimuth=315,
            alti=45
        )
        outputs['slope'] = slope_path
        logger.info(f"Slope saved to {slope_path}")

        # 2. Compute Flow Accumulation
        fa_path = str(output_dir / 'flow_accumulation.tif')
        logger.info("Computing flow accumulation...")
        with rasterio.open(dem_path) as dem_src:
            dem_data = dem_src.read(1)
            profile = dem_src.profile
            transform = dem_src.transform

        # Simplified flow accumulation using scipy
        flow_accum = HazardModellingService._compute_flow_accumulation(dem_data)

        profile.update(dtype=rasterio.float32)
        with rasterio.open(fa_path, 'w', **profile) as dst:
            dst.write(flow_accum.astype(np.float32), 1)
        outputs['flow_accumulation'] = fa_path
        logger.info(f"Flow accumulation saved to {fa_path}")

        # 3. Compute TWI (Topographic Wetness Index)
        twi_path = str(output_dir / 'twi.tif')
        logger.info("Computing TWI...")

        with rasterio.open(slope_path) as slope_src:
            slope_data = slope_src.read(1)

        # Convert slope to radians
        slope_rad = np.radians(slope_data)

        # TWI = ln(flow_accum / tan(slope))
        # Handle zero slope and no-flow areas
        twi = np.full_like(slope_rad, np.nan, dtype=np.float32)
        valid_mask = (flow_accum > 0) & (slope_rad > 0)
        twi[valid_mask] = np.log(flow_accum[valid_mask] / np.tan(slope_rad[valid_mask]))

        with rasterio.open(fa_path) as fa_src:
            profile = fa_src.profile

        profile.update(dtype=rasterio.float32)
        with rasterio.open(twi_path, 'w', **profile) as dst:
            dst.write(twi.astype(np.float32), 1)
        outputs['twi'] = twi_path
        logger.info(f"TWI saved to {twi_path}")

        # 4. Compute Stream Network
        stream_path = str(output_dir / 'stream_network.tif')
        logger.info("Computing stream network...")

        flow_threshold = 1000  # cells
        stream_network = (flow_accum >= flow_threshold).astype(np.uint8)

        with rasterio.open(fa_path) as fa_src:
            profile = fa_src.profile

        profile.update(dtype=rasterio.uint8)
        with rasterio.open(stream_path, 'w', **profile) as dst:
            dst.write(stream_network, 1)
        outputs['stream_network'] = stream_path
        logger.info(f"Stream network saved to {stream_path}")

        return outputs

    @staticmethod
    def _compute_flow_accumulation(dem: np.ndarray) -> np.ndarray:
        """
        Simplified flow accumulation computation using D8 algorithm.

        Parameters
        ----------
        dem : np.ndarray
            Digital Elevation Model

        Returns
        -------
        np.ndarray
            Flow accumulation grid
        """
        dem = np.asarray(dem, dtype=np.float32)
        rows, cols = dem.shape

        # Initialize flow accumulation
        flow_accum = np.ones_like(dem, dtype=np.float32)

        # D8 flow directions (3x3 neighborhood)
        for _ in range(3):  # Multiple passes for flow accumulation
            flow_temp = flow_accum.copy()

            for i in range(1, rows - 1):
                for j in range(1, cols - 1):
                    neighborhood = dem[i-1:i+2, j-1:j+2]
                    center = dem[i, j]

                    # Find steepest descent neighbor
                    max_slope = 0.0
                    steepest_idx = None

                    for di in range(3):
                        for dj in range(3):
                            if (di, dj) == (1, 1):
                                continue

                            neighbor_elev = neighborhood[di, dj]
                            if neighbor_elev < center:
                                distance = np.sqrt(di**2 + dj**2)
                                slope = (center - neighbor_elev) / distance
                                if slope > max_slope:
                                    max_slope = slope
                                    steepest_idx = (i + di - 1, j + dj - 1)

                    # Route flow to steepest neighbor
                    if steepest_idx:
                        ni, nj = steepest_idx
                        if 0 <= ni < rows and 0 <= nj < cols:
                            flow_accum[ni, nj] += flow_temp[i, j]

        return flow_accum

    # =========================================================================
    # Sea Level Rise (SLR) Enhancement
    # =========================================================================

    @staticmethod
    def apply_slr_boost(
        chi_array: np.ndarray,
        slr_1m_path: str,
        slr_2m_path: str,
        boost_1m: float = 0.3,
        boost_2m: float = 0.5,
        transform=None,
        crs=None
    ) -> np.ndarray:
        """
        Apply Sea Level Rise inundation boost to CHI.

        Areas within SLR inundation extent get hazard boost applied.

        Parameters
        ----------
        chi_array : np.ndarray
            Composite Hazard Index array
        slr_1m_path : str
            Path to 1m SLR inundation scenario
        slr_2m_path : str
            Path to 2m SLR inundation scenario
        boost_1m : float
            Hazard boost for 1m SLR areas (default 0.3)
        boost_2m : float
            Hazard boost for 2m SLR areas (default 0.5)
        transform : rasterio.transform.Affine, optional
            Geotransform for alignment
        crs : str, optional
            Coordinate reference system

        Returns
        -------
        np.ndarray
            CHI array with SLR boost applied, clipped to [0, 1]
        """
        logger.info("Applying SLR boost to CHI")
        chi_boosted = chi_array.copy()

        try:
            # Load 2m SLR (highest priority)
            with rasterio.open(slr_2m_path) as src:
                slr_2m = src.read(1)
                slr_2m_mask = slr_2m > 0

            chi_boosted[slr_2m_mask] += boost_2m
            logger.info(f"Applied {boost_2m} boost to {slr_2m_mask.sum()} cells for 2m SLR")

        except Exception as e:
            logger.warning(f"Could not load 2m SLR scenario: {str(e)}")

        try:
            # Load 1m SLR (only where 2m doesn't apply)
            with rasterio.open(slr_1m_path) as src:
                slr_1m = src.read(1)
                slr_1m_mask = (slr_1m > 0) & ~slr_2m_mask

            chi_boosted[slr_1m_mask] += boost_1m
            logger.info(f"Applied {boost_1m} boost to {slr_1m_mask.sum()} cells for 1m SLR")

        except Exception as e:
            logger.warning(f"Could not load 1m SLR scenario: {str(e)}")

        # Clip to valid range
        chi_boosted = np.clip(chi_boosted, 0.0, 1.0)
        logger.info(f"SLR boost applied. CHI range: [{np.nanmin(chi_boosted):.3f}, {np.nanmax(chi_boosted):.3f}]")

        return chi_boosted

    # =========================================================================
    # Output Writing
    # =========================================================================

    @staticmethod
    def save_chi_as_cog(
        chi_array: np.ndarray,
        transform,
        crs,
        output_path: str
    ) -> None:
        """
        Save CHI as Cloud Optimised GeoTIFF (COG).

        Parameters
        ----------
        chi_array : np.ndarray
            CHI data
        transform : rasterio.transform.Affine
            Geospatial transform
        crs : str
            Coordinate reference system
        output_path : str
            Output file path
        """
        logger.info(f"Saving CHI to COG: {output_path}")

        profile = {
            'driver': 'GTiff',
            'dtype': rasterio.float32,
            'width': chi_array.shape[1],
            'height': chi_array.shape[0],
            'count': 1,
            'crs': crs,
            'transform': transform,
            'compress': 'lzw',
            'TILED': 'YES',
            'BLOCKXSIZE': 512,
            'BLOCKYSIZE': 512,
            'COPY_SRC_OVERVIEWS': 'YES'
        }

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(chi_array.astype(np.float32), 1)
            # Add overviews
            dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)

        logger.info(f"CHI COG saved: {output_path}")

    # =========================================================================
    # Main Analysis Entry Point
    # =========================================================================

    def compute_hazard_index_for_analysis(
        self,
        analysis_id: str,
        aoi_geom: dict,
        db: Session
    ) -> Dict:
        """
        Main entry point: compute CHI and per-hazard scores for AOI.

        Parameters
        ----------
        analysis_id : str
            Unique analysis identifier
        aoi_geom : dict
            Area of Interest geometry (GeoJSON-like dict)
        db : Session
            Database session

        Returns
        -------
        Dict
            Dictionary containing:
            {
                'analysis_id': str,
                'composite_hazard_index': np.ndarray,
                'per_hazard_scores': {hazard_type: np.ndarray},
                'hazard_statistics': {
                    hazard_type: {'min': float, 'max': float, 'mean': float, ...}
                },
                'output_path': str,
                'timestamp': str
            }
        """
        logger.info(f"Computing hazard index for analysis {analysis_id}")

        from datetime import datetime

        # Create AOI mask from geometry
        aoi_gdf = gpd.GeoDataFrame(
            [{'geometry': gpd.geometry.shape(aoi_geom)}],
            crs='EPSG:4326'
        )

        # Load hazard datasets for AOI
        # Placeholder: in production, query hazard_datasets table
        hazard_arrays = self._load_hazard_datasets_for_aoi(aoi_gdf, db)

        if not hazard_arrays:
            logger.error(f"No hazard datasets found for analysis {analysis_id}")
            return {
                'analysis_id': analysis_id,
                'status': 'failed',
                'error': 'No hazard datasets available for AOI'
            }

        # Compute CHI
        chi = self.compute_chi(hazard_arrays)

        # Compute per-hazard statistics
        stats = {}
        for hazard_type, data in hazard_arrays.items():
            valid_mask = data != -9999
            valid_data = data[valid_mask]
            if len(valid_data) > 0:
                stats[hazard_type] = {
                    'min': float(np.nanmin(valid_data)),
                    'max': float(np.nanmax(valid_data)),
                    'mean': float(np.nanmean(valid_data)),
                    'std': float(np.nanstd(valid_data)),
                    'percentile_25': float(np.nanpercentile(valid_data, 25)),
                    'percentile_50': float(np.nanpercentile(valid_data, 50)),
                    'percentile_75': float(np.nanpercentile(valid_data, 75))
                }

        # Save CHI as COG
        output_dir = Path(f'/tmp/hazard_analysis/{analysis_id}')
        output_dir.mkdir(parents=True, exist_ok=True)

        chi_path = str(output_dir / 'chi.tif')
        # Get transform from first hazard dataset
        first_array = next(iter(hazard_arrays.values()))
        dummy_transform = from_bounds(-180, -90, 180, 90, first_array.shape[1], first_array.shape[0])

        self.save_chi_as_cog(chi, dummy_transform, 'EPSG:4326', chi_path)

        return {
            'analysis_id': analysis_id,
            'status': 'success',
            'composite_hazard_index': chi,
            'per_hazard_scores': hazard_arrays,
            'hazard_statistics': stats,
            'output_path': chi_path,
            'timestamp': datetime.now().isoformat(),
            'chi_min': float(np.nanmin(chi)),
            'chi_max': float(np.nanmax(chi)),
            'chi_mean': float(np.nanmean(chi))
        }

    def _load_hazard_datasets_for_aoi(
        self,
        aoi_gdf: gpd.GeoDataFrame,
        db: Session
    ) -> Dict[str, np.ndarray]:
        """
        Load all hazard datasets intersecting AOI.

        Placeholder: implement actual database query.

        Parameters
        ----------
        aoi_gdf : gpd.GeoDataFrame
            Area of Interest
        db : Session
            Database session

        Returns
        -------
        Dict[str, np.ndarray]
            Dictionary of hazard arrays
        """
        # Placeholder implementation
        logger.info("Loading hazard datasets for AOI")
        hazard_arrays = {}

        # In production:
        # 1. Query hazard_datasets table for datasets intersecting AOI
        # 2. Load each dataset as raster
        # 3. Clip/reproject to common grid if needed
        # 4. Return dictionary

        return hazard_arrays
