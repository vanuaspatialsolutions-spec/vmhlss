import { useState, useEffect } from 'react';
import { useAuthStore, useDatasetStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import UploadPanel from './UploadPanel';
import QAProgressBar from './QAProgressBar';
import type { DatasetSlot, QAReport } from '../../types/index';

interface DataSlotCardProps {
  slot: DatasetSlot;
  disabled?: boolean;
}

const statusConfig = {
  empty: { color: '#d1d5db', label: 'Empty', icon: '○' },
  pass: { color: '#10b981', label: 'Passed', icon: '✓' },
  conditional: { color: '#f59e0b', label: 'Conditional', icon: '⚠' },
  failed: { color: '#ef4444', label: 'Failed', icon: '✕' },
  auto_fixed: { color: '#3b82f6', label: 'Auto-fixed', icon: '◆' },
};

export default function DataSlotCard({ slot, disabled = false }: DataSlotCardProps) {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { uploads, setQAReport } = useDatasetStore();
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [qaReport, setLocalQAReport] = useState<QAReport | null>(null);

  const status = statusConfig[slot.status];
  const slotUploads = Object.values(uploads).filter((u) => u.slotCode === slot.code);
  const activeUpload = slotUploads.find(
    (u) => u.status === 'uploading' || u.status === 'processing'
  );

  // Poll QA status while processing
  useEffect(() => {
    if (!activeUpload) return;

    const interval = setInterval(async () => {
      try {
        const report = await apiService.getQAStatus(activeUpload.id);
        setLocalQAReport(report);
        setQAReport(activeUpload.id, report);

        if (report.overallResult !== 'pending') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to fetch QA status:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [activeUpload, setQAReport]);

  const handleUploadComplete = () => {
    setShowUploadPanel(false);
  };

  if (disabled) {
    return (
      <div className="bg-gray-100 rounded-lg p-4 border-2 border-dashed border-gray-300 opacity-60 relative">
        <div className="absolute top-3 right-3">
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-400 text-white text-xs font-semibold rounded-full">
            🔒 Phase 2
          </span>
        </div>
        <h3 className="font-bold text-gray-600 mb-1">{slot.code}</h3>
        <p className="text-sm text-gray-600">{slot.name}</p>
        <p className="text-xs text-gray-500 mt-2">Coming in Phase 2</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-all">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-white text-sm font-bold"
              style={{ backgroundColor: status.color }}>
              {status.icon}
            </span>
            <div>
              <h3 className="font-bold text-gray-900">{slot.code}</h3>
              <p className="text-xs text-gray-500">{status.label}</p>
            </div>
          </div>
        </div>
        <h4 className="font-semibold text-gray-900 text-sm mb-1">{slot.name}</h4>
        <p className="text-xs text-gray-600 line-clamp-2">{slot.description}</p>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Status Display */}
        {slot.dataSourceName && (
          <div className="bg-blue-50 rounded p-2">
            <p className="text-xs font-medium text-blue-900">
              Source: {slot.dataSourceName}
            </p>
            {slot.uploadedAt && (
              <p className="text-xs text-blue-700">
                Uploaded: {new Date(slot.uploadedAt).toLocaleDateString()}
              </p>
            )}
          </div>
        )}

        {/* QA Progress */}
        {activeUpload && qaReport && (
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">QA Process:</p>
            <QAProgressBar report={qaReport} />
          </div>
        )}

        {/* Accepted Formats */}
        <div>
          <p className="text-xs font-semibold text-gray-700 mb-1">{t('dashboard.formats')}:</p>
          <div className="flex flex-wrap gap-1">
            {slot.acceptedFormats.slice(0, 3).map((format) => (
              <span key={format} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                {format}
              </span>
            ))}
            {slot.acceptedFormats.length > 3 && (
              <span className="text-xs text-gray-500 px-2 py-1">
                +{slot.acceptedFormats.length - 3} more
              </span>
            )}
          </div>
        </div>

        {/* Minimum Standard */}
        <div>
          <p className="text-xs font-semibold text-gray-700 mb-1">{t('dashboard.minimum')}:</p>
          <p className="text-xs text-gray-600">{slot.minimumStandard}</p>
        </div>

        {/* Recommended Source */}
        {slot.recommendedSource && (
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-1">{t('dashboard.recommended')}:</p>
            <p className="text-xs text-gray-600">{slot.recommendedSource}</p>
          </div>
        )}
      </div>

      {/* Footer - Actions */}
      <div className="border-t border-gray-100 p-4">
        {slot.status === 'empty' ? (
          <button
            onClick={() => setShowUploadPanel(!showUploadPanel)}
            className="w-full py-2 px-3 bg-green-600 text-white rounded-lg font-medium text-sm hover:bg-green-700 transition-all"
          >
            {t('dashboard.upload')}
          </button>
        ) : (
          <button
            onClick={() => setShowUploadPanel(!showUploadPanel)}
            className="w-full py-2 px-3 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 transition-all"
          >
            {t('dashboard.replace')}
          </button>
        )}
      </div>

      {/* Upload Panel */}
      {showUploadPanel && (
        <div className="bg-gray-50 border-t border-gray-200 p-4">
          <UploadPanel slot={slot} onComplete={handleUploadComplete} />
        </div>
      )}
    </div>
  );
}
