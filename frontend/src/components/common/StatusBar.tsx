import { useEffect, useState } from 'react';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import type { DashboardMetrics } from '../../types/index';

export default function StatusBar() {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await apiService.getDashboardMetrics();
        setMetrics(data);
      } catch (error) {
        console.error('Failed to fetch dashboard metrics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();

    // Refresh metrics every 60 seconds
    const interval = setInterval(fetchMetrics, 60000);
    return () => clearInterval(interval);
  }, []);

  const lastAnalysisDate = metrics?.lastAnalysisDate
    ? new Date(metrics.lastAnalysisDate).toLocaleDateString(language === 'en' ? 'en-US' : 'en-GB')
    : 'Never';

  return (
    <div className="bg-white border-t border-gray-200 px-6 py-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex gap-8">
          {/* Slots Completed */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.slots')}:</span>
            {loading ? (
              <span className="text-gray-400">...</span>
            ) : (
              <span className="font-semibold text-gray-900">
                {metrics?.slotsCompleted || 0}/{metrics?.slotsTotal || 0}
              </span>
            )}
          </div>

          {/* KB Records */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.kbrecords')}:</span>
            {loading ? (
              <span className="text-gray-400">...</span>
            ) : (
              <span className="font-semibold text-gray-900">
                {metrics?.kbRecordsCount || 0}
              </span>
            )}
          </div>

          {/* Last Analysis */}
          <div className="flex items-center gap-2">
            <span className="text-gray-600">{t('status.lastanalysis')}:</span>
            {loading ? (
              <span className="text-gray-400">...</span>
            ) : (
              <span className="font-semibold text-gray-900">{lastAnalysisDate}</span>
            )}
          </div>
        </div>

        {/* Data Quality Score */}
        {metrics && (
          <div className="flex items-center gap-2">
            <span className="text-gray-600">Data Quality:</span>
            <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  metrics.dataQualityScore >= 80
                    ? 'bg-green-500'
                    : metrics.dataQualityScore >= 60
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
        )}
      </div>
    </div>
  );
}
