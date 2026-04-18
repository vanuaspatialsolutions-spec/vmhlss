import type { QAReport } from '../../types/index';

interface QAProgressBarProps {
  report: QAReport;
}

const stageLabels: Record<number, string> = {
  1: 'Format',
  2: 'Geometry',
  3: 'Metadata',
  4: 'CRS',
  5: 'Fields',
  6: 'Review',
};

const resultIcon = {
  pass: '✓',
  fail: '✕',
  auto_fixed: '◆',
  pending: '○',
};

const resultColor = {
  pass: '#10b981',
  fail: '#ef4444',
  auto_fixed: '#3b82f6',
  pending: '#d1d5db',
};

export default function QAProgressBar({ report }: QAProgressBarProps) {
  return (
    <div className="space-y-2">
      {/* Stage bars */}
      <div className="flex gap-1">
        {report.stages.map((stage) => (
          <div
            key={stage.stage}
            className="flex-1 relative"
            title={`Stage ${stage.stage}: ${stage.result}`}
          >
            <div
              className="h-3 rounded transition-all"
              style={{
                backgroundColor: resultColor[stage.result],
                opacity: stage.result === 'pending' ? 0.3 : 1,
              }}
            />
            <span
              className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white"
              style={{
                textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
              }}
            >
              {resultIcon[stage.result]}
            </span>
          </div>
        ))}
      </div>

      {/* Stage labels */}
      <div className="flex gap-1 text-xs font-medium text-gray-600">
        {report.stages.map((stage) => (
          <div key={stage.stage} className="flex-1 text-center">
            {stageLabels[stage.stage]}
          </div>
        ))}
      </div>

      {/* Overall status */}
      <div className="text-xs">
        <span
          className="inline-block px-2 py-1 rounded font-semibold text-white"
          style={{ backgroundColor: resultColor[report.overallResult] }}
        >
          {report.overallResult === 'pass'
            ? 'All Passed'
            : report.overallResult === 'fail'
              ? 'Failed'
              : 'Auto-fixed'}
        </span>
      </div>
    </div>
  );
}
