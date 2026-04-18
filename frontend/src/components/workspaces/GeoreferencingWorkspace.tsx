import { useState } from 'react';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { useDropzone } from 'react-dropzone';

export default function GeoreferencingWorkspace() {
  const { language } = useAuthStore();
  const { t: _t } = useTranslation(language);
  const [mapImage, setMapImage] = useState<File | null>(null);
  const [gcpCount, setGcpCount] = useState(0);
  const [processingGeoreference, setProcessingGeoreference] = useState(false);

  const onDrop = (files: File[]) => {
    if (files.length > 0) {
      setMapImage(files[0]);
      setGcpCount(0);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.tif', '.tiff'],
    },
  });

  const handleComputeTransformation = async () => {
    setProcessingGeoreference(true);
    // Simulate computation
    setTimeout(() => {
      setProcessingGeoreference(false);
    }, 3000);
  };

  return (
    <div className="w-full h-full overflow-auto bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Georeferencing</h1>
          <p className="text-gray-600">
            Georeference scanned maps using ground control points
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Map Image Upload */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Map Image</h2>

            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
                isDragActive
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 bg-white'
              }`}
            >
              <input {...getInputProps()} />
              <div className="text-4xl mb-2">🗺️</div>
              <p className="font-semibold text-gray-900 mb-1">
                {mapImage ? mapImage.name : 'Drop map image here or click'}
              </p>
              <p className="text-xs text-gray-600">
                PNG, JPG, TIFF, GeoTIFF
              </p>
            </div>

            {mapImage && (
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-900">File Info</p>
                <p className="text-xs text-gray-600">
                  {(mapImage.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            )}
          </div>

          {/* Right: GCP Management */}
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Ground Control Points</h2>

            <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-1">
                  GCPs Identified
                </label>
                <div className="text-3xl font-bold text-green-600">
                  {gcpCount}
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-gray-600 mb-2">
                  Recommended: 4+ GCPs
                </p>
                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-green-500 transition-all"
                    style={{ width: `${Math.min((gcpCount / 4) * 100, 100)}%` }}
                  />
                </div>
              </div>

              {gcpCount >= 4 && (
                <button
                  onClick={handleComputeTransformation}
                  disabled={processingGeoreference}
                  className="w-full py-2 px-4 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {processingGeoreference
                    ? 'Computing...'
                    : 'Compute Transformation'}
                </button>
              )}
            </div>

            {processingGeoreference && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-sm font-medium text-blue-900">
                  Computing affine transformation...
                </p>
                <div className="mt-2 w-full h-2 bg-blue-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 animate-pulse"
                    style={{ width: '60%' }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Preview Area */}
        {mapImage && (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="font-bold text-gray-900 mb-3">Map Preview</h3>
            <div className="w-full h-96 bg-gray-100 rounded-lg flex items-center justify-center">
              <p className="text-gray-600">Map image preview would display here</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
