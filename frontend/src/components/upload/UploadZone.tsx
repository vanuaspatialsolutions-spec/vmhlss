import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadZoneProps {
  onUpload: (file: File) => void;
  acceptedFormats: string[];
  maxSizeMB?: number;
  label?: string;
  isUploading?: boolean;
  uploadProgress?: number;
  currentFile?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onUpload,
  acceptedFormats,
  maxSizeMB = 500,
  label = 'Upload file',
  isUploading = false,
  uploadProgress = 0,
  currentFile,
}) => {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onUpload(accepted[0]);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    maxSize: maxSizeMB * 1024 * 1024,
    multiple: false,
  });

  const rejection = fileRejections[0];

  return (
    <div className="space-y-2">
      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
          ${isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="space-y-2">
            <div className="text-sm text-gray-600">
              Uploading {currentFile}…
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <div className="text-xs text-gray-400">{uploadProgress}%</div>
          </div>
        ) : (
          <>
            <div className="text-3xl mb-2">📂</div>
            <p className="text-sm font-medium text-gray-700">
              {isDragActive ? 'Drop file here' : label}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Drag & drop or click to browse
            </p>
            <p className="text-xs text-gray-400">
              Max {maxSizeMB} MB
            </p>
          </>
        )}
      </div>

      {/* Accepted formats */}
      <div className="flex flex-wrap gap-1">
        {acceptedFormats.map((fmt) => (
          <span
            key={fmt}
            className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded border border-gray-200"
          >
            {fmt}
          </span>
        ))}
      </div>

      {/* Rejection error */}
      {rejection && (
        <p className="text-xs text-red-600">
          ❌ {rejection.errors.map((e) => e.message).join(', ')}
        </p>
      )}
    </div>
  );
};

export default UploadZone;
