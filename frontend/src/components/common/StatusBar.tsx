import { useEffect, useState } from 'react';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { getDashboardMetrics } from '../../services/localEngine';
import type { DashboardMetrics } from '../../types/index';

export default function StatusBar() {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const [metrics, setMetrics] = useState<DashboardMetrics>(getDashboardMetrics());

  const refresh = () => setMetrics(getDashboardMetrics());

  useEffect(() => {
    refresh();
    // Re-compute whenever any local engine emits a change
    const events = ['vmhlss:slots', 'vmhlss:analyses', 'vmhlss:kb', 'vmhlss:uploads'];
    events.forEach(e => window.addEventListener(e, refresh));
    return () => events.forEach(e => window.removeEventListener(e, refresh));
  }, []);

  const lastAnalysisDate = metrics.lastAnalysisDate
    ? new Date(metrics.lastAnalysisDate).toLocaleDateString(
        language === 'en' ? 'en-AU' : 'en-GB',
        { day: 'numeric', month: 'short', year: 'numeric' }
      )
    : 'Never';

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex gap-8">
          {/* Slots Completed */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.slots')}:</span>
            <span className="font-semibold text-gray-900">
              {metrics.slotsCompleted}/{metrics.slotsTotal}
            </span>
          </div>

          {/* KB Records */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.kbrecords')}:</span>
            <span className="font-semibold text-gray-900">
              {metrics.kbRecordsCount}
            </span>
          </div>

          {/* Last Analysis */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.lastanalysis')}:</span>
            <span className="font-semibold text-gray-900">{lastAnalysisDate}</span>
          </div>

          {/* Analyses run */}
          {(metrics.analysesThisMonth ?? 0) > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-600">Analyses:</span>
              <span className="font-semibold text-gray-900">{metrics.analysesThisMonth}</span>
            </div>
          )}
        </div>

        {/* Data Quality Score */}
        <div className="flex items-center gap-2">
          <span className="text-gray-600">Data Quality:</span>
          <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                metrics.dataQualityScore >= 80
                  ? 'bg-green-500'
                  : metrics.dataQualityScore >= 50
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
              }`}
              style={{ width: `${metrics.dataQualityScore}%` }}
            />
          </div>
          <span className="font-semibold text-gray-900 w-12">
            {metrics.dataQualityScore}%
          </span>
        </div>
      </div>
    </div>
  );
}
