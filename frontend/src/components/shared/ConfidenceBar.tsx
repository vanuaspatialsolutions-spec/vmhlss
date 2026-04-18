import React from 'react';

interface ConfidenceBarProps {
  value: number; // 0.0 - 1.0
  showLabel?: boolean;
  height?: number;
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({
  value,
  showLabel = true,
  height = 8,
}) => {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.75 ? '#22c55e' : value >= 0.5 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 rounded-full bg-gray-200 overflow-hidden"
        style={{ height }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-gray-600 w-10 text-right">
          {pct}%
        </span>
      )}
    </div>
  );
};

export default ConfidenceBar;
