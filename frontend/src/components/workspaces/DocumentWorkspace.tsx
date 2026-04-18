import { useState } from 'react';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import { useDropzone } from 'react-dropzone';

export default function DocumentWorkspace() {
  const { language } = useAuthStore();
  const { t: _t } = useTranslation(language);
  const [uploads, setUploads] = useState<File[]>([]);
  const [extractions, setExtractions] = useState<any[]>([]);
  const [processing, setProcessing] = useState(false);

  const onDrop = async (files: File[]) => {
    setUploads((prev) => [...prev, ...files]);
    setProcessing(true);

    try {
      for (const file of files) {
        const response = await apiService.uploadDocument(file);
        const exts = await apiService.getExtractions(response.documentId);
        setExtractions((prev) => [...prev, ...exts]);
      }
    } catch (error) {
      console.error('Document upload failed:', error);
    } finally {
      setProcessing(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc', '.docx'],
      'text/plain': ['.txt'],
    },
  });

  return (
    <div className="w-full h-full overflow-auto bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Document Extraction</h1>
          <p className="text-gray-600">
            Upload documents to extract knowledge base information
          </p>
        </div>

        {/* Upload Zone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-green-500 bg-green-50'
              : 'border-gray-300 bg-white hover:border-gray-400'
          }`}
        >
          <input {...getInputProps()} />
          <div className="text-5xl mb-4">📄</div>
          <p className="font-semibold text-gray-900 mb-2">
            {isDragActive
              ? 'Drop documents here'
              : 'Drag documents here or click to browse'}
          </p>
          <p className="text-sm text-gray-600">
            Supported: PDF, Word, Text documents
          </p>
        </div>

        {/* Processing Status */}
        {processing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm font-medium text-blue-900">Processing documents...</p>
          </div>
        )}

        {/* Uploaded Files */}
        {uploads.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-3">
              Uploaded Files ({uploads.length})
            </h2>
            <div className="space-y-2">
              {uploads.map((file, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200"
                >
                  <span className="text-xl">📄</span>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-600">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <span className="text-green-600 font-semibold">✓</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Extractions */}
        {extractions.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-3">
              Extracted Information ({extractions.length})
            </h2>
            <div className="space-y-3">
              {extractions.map((extraction, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-white rounded-lg border border-gray-200"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-semibold text-gray-900">
                        {extraction.theme}
                      </p>
                      <p className="text-xs text-gray-600">
                        {extraction.source}
                      </p>
                    </div>
                    <span
                      className="text-xs font-semibold px-2 py-1 rounded-full"
                      style={{
                        backgroundColor:
                          extraction.confidence > 0.8
                            ? '#d1fae5'
                            : '#fef3c7',
                        color:
                          extraction.confidence > 0.8
                            ? '#047857'
                            : '#b45309',
                      }}
                    >
                      {(extraction.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">
                    {extraction.statement}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
