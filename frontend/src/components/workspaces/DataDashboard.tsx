import { useEffect, useState } from 'react';
import { useAuthStore, useDatasetStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import DataSlotCard from '../data/DataSlotCard';
import type { DatasetSlot } from '../../types/index';

const PHASE_1_SLOTS = ['DS-01', 'DS-02', 'DS-03', 'DS-04', 'DS-05', 'DS-06', 'DS-07', 'DS-08', 'DS-09', 'DS-10'];
const PHASE_2_SLOTS = ['DS-11', 'DS-12', 'DS-13', 'DS-14'];

export default function DataDashboard() {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { slots, setSlots } = useDatasetStore();
  const [error, setError] = useState<string | null>(null);

  // Fetch dataset slots on mount
  useEffect(() => {
    const fetchSlots = async () => {
      try {
        const data = await apiService.getSlots();
        setSlots(data);
      } catch (err) {
        console.error('Failed to fetch slots:', err);
        setError('Failed to load dataset slots');
        // Load mock data for demo
        loadMockSlots();
      }
    };

    fetchSlots();
  }, [setSlots]);

  const loadMockSlots = () => {
    const mockSlots: DatasetSlot[] = [
      {
        code: 'DS-01',
        name: 'Digital Elevation Model (DEM)',
        description: 'High-resolution elevation data for terrain analysis',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['GeoTIFF', 'HDF5', 'NetCDF'],
        minimumStandard: '30m resolution, WGS84 projection',
        recommendedSource: 'SRTM, ASTER GDEM',
        dataSourceName: 'SRTM v3',
        uploadedAt: '2024-03-15',
        lastUpdated: '2024-03-15',
      },
      {
        code: 'DS-02',
        name: 'Precipitation Data',
        description: 'Annual rainfall and seasonal patterns',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['NetCDF', 'GeoTIFF', 'CSV'],
        minimumStandard: '10+ years monthly data',
        recommendedSource: 'CHIRPS, MERRA-2',
        lastUpdated: '2024-02-20',
      },
      {
        code: 'DS-03',
        name: 'Soil Data',
        description: 'Soil properties, texture, and characteristics',
        status: 'conditional',
        phase: 1,
        acceptedFormats: ['Shapefile', 'GeoPackage', 'GeoJSON'],
        minimumStandard: 'Soil types and profiles',
        dataSourceName: 'HWSD v2.0',
        uploadedAt: '2024-03-10',
        lastUpdated: '2024-03-10',
      },
      {
        code: 'DS-04',
        name: 'Hazard Zonation Maps',
        description: 'Cyclone, tsunami, volcanic, flood, earthquake, landslide risks',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['Shapefile', 'GeoTIFF', 'GeoJSON'],
        minimumStandard: 'Multi-hazard coverage, validated',
        dataSourceName: 'National Hazard Maps',
        uploadedAt: '2024-03-01',
        lastUpdated: '2024-03-01',
      },
      {
        code: 'DS-05',
        name: 'Land Use / Land Cover (LULC)',
        description: 'Current and historical land use classification',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['GeoTIFF', 'Shapefile', 'NetCDF'],
        minimumStandard: 'Multi-class LULC, recent',
        recommendedSource: 'ESA Worldcover, Sentinel-2',
        uploadedAt: '2024-02-28',
        lastUpdated: '2024-02-28',
      },
      {
        code: 'DS-06',
        name: 'Crop Suitability Reference Data',
        description: 'Known suitability zones for major crops',
        status: 'failed',
        phase: 1,
        acceptedFormats: ['Shapefile', 'GeoPackage', 'CSV'],
        minimumStandard: 'Crop-specific zones, validated',
        lastUpdated: '2024-01-15',
      },
      {
        code: 'DS-07',
        name: 'Development Infrastructure',
        description: 'Existing buildings, roads, utilities',
        status: 'empty',
        phase: 1,
        acceptedFormats: ['Shapefile', 'GeoJSON', 'OSM'],
        minimumStandard: 'Vector features, recent',
        recommendedSource: 'OpenStreetMap, local surveys',
      },
      {
        code: 'DS-08',
        name: 'Population Density',
        description: 'Population distribution and density',
        status: 'empty',
        phase: 1,
        acceptedFormats: ['GeoTIFF', 'GeoJSON', 'Shapefile'],
        minimumStandard: '1km resolution or better',
        recommendedSource: 'WorldPop, SEDAC',
      },
      {
        code: 'DS-09',
        name: 'Climate Data (Temperature)',
        description: 'Mean annual temperature and extremes',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['NetCDF', 'GeoTIFF', 'CSV'],
        minimumStandard: '10+ years monthly mean temps',
        recommendedSource: 'WorldClim, MERRA-2',
        uploadedAt: '2024-03-12',
        lastUpdated: '2024-03-12',
      },
      {
        code: 'DS-10',
        name: 'Administrative Boundaries',
        description: 'National and regional administrative divisions',
        status: 'pass',
        phase: 1,
        acceptedFormats: ['Shapefile', 'GeoJSON', 'GeoPackage'],
        minimumStandard: 'All provinces and municipalities',
        uploadedAt: '2024-01-20',
        lastUpdated: '2024-01-20',
      },
      {
        code: 'DS-11',
        name: 'Historical Hazard Events',
        description: 'Records of past natural disasters',
        status: 'empty',
        phase: 2,
        acceptedFormats: ['Shapefile', 'CSV', 'GeoJSON'],
        minimumStandard: '20+ years of event records',
      },
      {
        code: 'DS-12',
        name: 'Crop Yield Data',
        description: 'Historical crop production and yields',
        status: 'empty',
        phase: 2,
        acceptedFormats: ['CSV', 'GeoJSON', 'Shapefile'],
        minimumStandard: '10+ years temporal coverage',
      },
      {
        code: 'DS-13',
        name: 'Property Value Data',
        description: 'Land and property values for development analysis',
        status: 'empty',
        phase: 2,
        acceptedFormats: ['CSV', 'Shapefile', 'GeoJSON'],
        minimumStandard: 'Recent valuation data',
      },
      {
        code: 'DS-14',
        name: 'Groundwater Data',
        description: 'Water table depth and aquifer characteristics',
        status: 'empty',
        phase: 2,
        acceptedFormats: ['CSV', 'GeoJSON', 'NetCDF'],
        minimumStandard: 'Well location and depth data',
      },
    ];

    setSlots(mockSlots);
  };

  const phase1Slots = slots.filter((s) => PHASE_1_SLOTS.includes(s.code));
  const phase2Slots = slots.filter((s) => PHASE_2_SLOTS.includes(s.code));

  const slotsPassed = slots.filter((s) => s.status === 'pass').length;

  return (
    <div className="w-full h-full overflow-auto bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {t('dashboard.slots')}
          </h1>
          <p className="text-gray-600">
            {slotsPassed}/{slots.length} {t('dashboard.phase1')} slots completed
          </p>
        </div>

        {/* Phase 1 Section */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            {t('dashboard.phase1')}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {phase1Slots.map((slot) => (
              <DataSlotCard key={slot.code} slot={slot} />
            ))}
          </div>
        </section>

        {/* Phase 2 Section */}
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            {t('dashboard.phase2')}
            <span className="text-sm font-medium px-3 py-1 bg-gray-200 text-gray-700 rounded-full">
              Coming Soon
            </span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {phase2Slots.map((slot) => (
              <DataSlotCard key={slot.code} slot={slot} disabled />
            ))}
          </div>
        </section>

        {/* Info Box */}
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
