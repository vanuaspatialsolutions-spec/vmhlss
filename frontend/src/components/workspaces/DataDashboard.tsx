import { useEffect, useState } from 'react';
import { useAuthStore, useDatasetStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import DataSlotCard from '../data/DataSlotCard';
// DatasetSlot type used by DataSlotCard (no direct import needed here)

const PHASE_1_SLOTS = ['DS-01', 'DS-02', 'DS-03', 'DS-04', 'DS-05', 'DS-06', 'DS-07', 'DS-08', 'DS-09', 'DS-10'];
const PHASE_2_SLOTS = ['DS-11', 'DS-12', 'DS-13', 'DS-14'];

export default function DataDashboard() {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { slots, setSlots } = useDatasetStore();
  const [_error, _setError] = useState<string | null>(null);

  // Load slots from local engine on mount and re-sync on storage events
  useEffect(() => {
    const load = async () => {
      const data = await apiService.getSlots();
      setSlots(data);
    };
    load();
    // Re-fetch whenever the local engine emits a slots update
    const handler = () => load();
    window.addEventListener('vmhlss:slots', handler);
    return () => window.removeEventListener('vmhlss:slots', handler);
  }, [setSlots]);

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

        {/* System status — always operational */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
          <span className="text-green-600 text-lg">✅</span>
          <div>
            <p className="text-sm font-semibold text-green-800">System Operational</p>
            <p className="text-xs text-green-700">
              Upload real datasets to activate each slot. Data is validated automatically and stored locally.
              DS-07 (Infrastructure) pre-loaded from OpenStreetMap.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
