import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useAuthStore, useDatasetStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import type { DatasetSlot } from '../../types/index';

interface UploadPanelProps {
  slot: DatasetSlot;
  onComplete: () => void;
}

export default function UploadPanel({ slot, onComplete }: UploadPanelProps) {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { addUpload, updateUpload } = useDatasetStore();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setError(null);
      setUploading(true);

      try {
        // Create upload record
        const uploadId = `upload-${Date.now()}`;
        addUpload({
          id: uploadId,
          slotCode: slot.code,
          fileName: file.name,
          fileSize: file.size,
          uploadedAt: new Date().toISOString(),
          uploadedBy: 'current-user',
          status: 'uploading',
          progress: 0,
        });

        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
          progress = Math.min(progress + Math.random() * 30, 90);
          updateUpload(uploadId, { progress });
        }, 300);

        // Upload file
        const upload = await apiService.uploadFile(slot.code, file);

        clearInterval(progressInterval);
        updateUpload(uploadId, {
          ...upload,
          status: 'processing',
          progress: 100,
        });

        // Wait a bit before completing
        setTimeout(() => {
          onComplete();
        }, 1000);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
        setUploading(false);
      }
    },
    [slot, addUpload, updateUpload, onComplete]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading,
    accept: Object.fromEntries(
      [
        slot.acceptedFormats.includes('Shapefile') && ['application/zip', ['.zip']],
        slot.acceptedFormats.includes('GeoTIFF') && ['image/tiff', ['.tif', '.tiff']],
        slot.acceptedFormats.includes('CSV') && ['text/csv', ['.csv']],
        slot.acceptedFormats.includes('GeoJSON') && ['application/json', ['.geojson']],
        slot.acceptedFormats.includes('GeoPackage') && [
          'application/geopackage+sqlite3',
          ['.gpkg'],
        ],
        slot.acceptedFormats.includes('NetCDF') && ['application/x-netcdf', ['.nc', '.nc4']],
      ].filter(Boolean) as [string, string[]][]
    ),
  });

  return (
    <div className="space-y-4">
      {/* Drag & Drop Zone */}
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
          {isDragActive
            ? 'Drop files here'
            : t('dashboard.dragdrop')}
        </p>
        <p className="text-xs text-gray-600">
          {slot.acceptedFormats.join(', ')}
        </p>
      </div>

      {/* Formats Info */}
      <div className="bg-blue-50 border border-blue-200 rounded p-3">
        <p className="text-xs font-semibold text-blue-900 mb-1">
          {t('dashboard.minimum')}:
        </p>
        <p className="text-xs text-blue-800">{slot.minimumStandard}</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-800">{error}</p>
        </div>
      )}

      {/* Upload Status */}
      {uploading && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-xs font-medium text-yellow-900">
            {t('dashboard.processing')}...
          </p>
          <div className="w-full h-2 bg-yellow-200 rounded-full overflow-hidden mt-2">
            <div
              className="h-full bg-yellow-500 transition-all"
              style={{ width: '45%' }}
            />
          </div>
        </div>
      )}

      {/* Close Button */}
      <button
        onClick={() => onComplete()}
        disabled={uploading}
        className="w-full py-2 px-3 bg-gray-200 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-300 transition-all disabled:opacity-50"
      >
        {t('common.close')}
      </button>
    </div>
  );
}
