import React from 'react';

type SuitabilityClass = 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'NS';
type BadgeSize = 'sm' | 'md' | 'lg';

interface SuitabilityBadgeProps {
  suitabilityClass: SuitabilityClass;
  size?: BadgeSize;
  showLabel?: boolean;
}

const CLASS_CONFIG: Record<SuitabilityClass, { color: string; bg: string; label: string; shortLabel: string }> = {
  S1: { color: '#ffffff', bg: '#1a5c30', label: 'Highly Suitable', shortLabel: 'S1' },
  S2: { color: '#ffffff', bg: '#4aa040', label: 'Suitable with Conditions', shortLabel: 'S2' },
  S3: { color: '#ffffff', bg: '#c8a000', label: 'Marginally Suitable', shortLabel: 'S3' },
  S4: { color: '#ffffff', bg: '#c85000', label: 'Currently Not Suitable', shortLabel: 'S4' },
  S5: { color: '#ffffff', bg: '#8b2000', label: 'Permanently Unsuitable', shortLabel: 'S5' },
  NS: { color: '#ffffff', bg: '#1a1a1a', label: 'No-Go / Protected', shortLabel: 'NS' },
};

const SIZE_CLASSES: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-xs font-semibold rounded',
  md: 'px-3 py-1 text-sm font-bold rounded-md',
  lg: 'px-4 py-2 text-base font-bold rounded-lg',
};

export const SuitabilityBadge: React.FC<SuitabilityBadgeProps> = ({
  suitabilityClass,
  size = 'md',
  showLabel = false,
}) => {
  const config = CLASS_CONFIG[suitabilityClass];
  return (
    <span
      className={`inline-flex items-center gap-1.5 ${SIZE_CLASSES[size]}`}
      style={{ backgroundColor: config.bg, color: config.color }}
      title={config.label}
    >
      <span>{config.shortLabel}</span>
      {showLabel && <span className="font-normal opacity-90">{config.label}</span>}
    </span>
  );
};

export default SuitabilityBadge;
