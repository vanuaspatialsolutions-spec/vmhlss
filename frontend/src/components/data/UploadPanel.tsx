import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { processUpload } from '../../services/localEngine';
import type { DatasetSlot, QAReport } from '../../types/index';

interface UploadPanelProps {
  slot: DatasetSlot;
  onComplete: () => void;
}

const STAGE_ICONS: Record<string, string> = {
  pass: '✓',
  auto_fixed: '◆',
  fail: '✕',
  pending: '○',
};
const STAGE_COLORS: Record<string, string> = {
  pass: 'text-green-600',
  auto_fixed: 'text-blue-600',
  fail: 'text-red-600',
  pending: 'text-gray-400',
};

export default function UploadPanel({ slot, onComplete }: UploadPanelProps) {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [qaResult, setQaResult] = useState<QAReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      const file = acceptedFiles[0];
      setError(null);
      setQaResult(null);
      setUploading(true);
      setProgress(0);

      try {
        const { qa } = await processUpload(slot.code, file, p => setProgress(p));
        setQaResult(qa);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [slot]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading,
    maxFiles: 1,
  });

  const resultColor =
    qaResult?.overallResult === 'pass'
      ? 'bg-green-50 border-green-300'
      : qaResult?.overallResult === 'auto_fixed'
        ? 'bg-yellow-50 border-yellow-300'
        : qaResult?.overallResult === 'fail'
          ? 'bg-red-50 border-red-300'
          : '';

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
      {!qaResult && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-green-500 bg-green-50'
              : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          <div className="text-4xl mb-2">📁</div>
          <p className="font-semibold text-gray-900 mb-1">
            {isDragActive ? 'Drop file here' : t('dashboard.dragdrop')}
          </p>
          <p className="text-xs text-gray-500 mb-1">
            {slot.acceptedFormats.join(' · ')}
          </p>
          <p className="text-xs text-gray-400">
            Minimum: {slot.minimumStandard}
          </p>
        </div>
      )}

      {/* Progress Bar */}
      {uploading && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-gray-600">
            <span>Running QA validation…</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* QA Result */}
      {qaResult && (
        <div className={`border rounded-lg p-4 space-y-3 ${resultColor}`}>
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-gray-900 text-sm">QA Validation Complete</h4>
            <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase ${
              qaResult.overallResult === 'pass'
                ? 'bg-green-100 text-green-800'
                : qaResult.overallResult === 'auto_fixed'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-red-100 text-red-800'
            }`}>
              {qaResult.overallResult}
            </span>
          </div>

          <div className="space-y-1.5">
            {qaResult.stages?.map((stage) => (
              <div key={stage.stage} className="flex items-start gap-2 text-xs">
                <span className={`shrink-0 font-bold w-4 text-center ${STAGE_COLORS[stage.result]}`}>
                  {STAGE_ICONS[stage.result]}
                </span>
                <div>
                  <span className="font-medium text-gray-700">{stage.name}: </span>
                  <span className="text-gray-600">{stage.description}</span>
                </div>
              </div>
            ))}
          </div>

          {qaResult.overallResult !== 'fail' ? (
            <button
              onClick={onComplete}
              className="w-full py-2 px-3 bg-green-600 text-white rounded-lg font-semibold text-sm hover:bg-green-700 transition-all"
            >
              ✓ Dataset Registered
            </button>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-red-700 font-medium">
                Dataset did not pass validation. Please fix the issues and re-upload.
              </p>
              <button
                onClick={() => { setQaResult(null); setProgress(0); }}
                className="w-full py-2 px-3 bg-red-600 text-white rounded-lg font-semibold text-sm hover:bg-red-700 transition-all"
              >
                Try Again
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-300 rounded p-3">
          <p className="text-xs text-red-800 font-medium">Error: {error}</p>
        </div>
      )}

      {/* Close */}
      {!qaResult && (
        <button
          onClick={onComplete}
          disabled={uploading}
          className="w-full py-2 px-3 bg-gray-200 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-300 transition-all disabled:opacity-50"
        >
          {t('common.close')}
        </button>
      )}
    </div>
  );
}
