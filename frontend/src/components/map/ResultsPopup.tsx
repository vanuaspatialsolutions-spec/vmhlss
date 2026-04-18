import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';

interface ResultsPopupProps {
  position: [number, number];
  content: {
    suitabilityClass: string;
    chiScore: number;
    confidence: number;
    topHazards?: Array<{ name: string; severity: number; impact: string }>;
  };
}

const suitabilityLabels: Record<string, Record<string, string>> = {
  en: {
    S1: 'Highly Suitable',
    S2: 'Suitable',
    S3: 'Moderately Suitable',
    S4: 'Marginally Suitable',
    S5: 'Not Suitable',
    NS: 'Not Assessed',
  },
  bi: {
    S1: 'I Gud Tumas',
    S2: 'I Gud',
    S3: 'Sampol Gud',
    S4: 'No Gud Much',
    S5: 'No Gud',
    NS: 'No Chekem',
  },
};

const suitabilityColors: Record<string, string> = {
  S1: '#1a5c30',
  S2: '#4aa040',
  S3: '#c8a000',
  S4: '#c85000',
  S5: '#8b2000',
  NS: '#1a1a1a',
};

export default function ResultsPopup({ position, content }: ResultsPopupProps) {
  const { language } = useAuthStore();
  const { t: _t } = useTranslation(language);

  const label = suitabilityLabels[language][content.suitabilityClass] || content.suitabilityClass;
  const color = suitabilityColors[content.suitabilityClass];

  return (
    <div
      className="absolute bg-white rounded-lg shadow-lg border-l-4 p-4 max-w-xs z-50"
      style={{
        left: `${(position[0] - (-15.376)) * 1000}px`,
        top: `${(position[1] - 166.959) * 1000}px`,
        borderLeftColor: color,
      }}
    >
      {/* Header */}
      <div className="mb-3">
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: color }}
          />
          <h4 className="font-bold text-gray-900">{label}</h4>
        </div>
        <p className="text-xs text-gray-600">{content.suitabilityClass}</p>
      </div>

      {/* Metrics */}
      <div className="space-y-2 mb-3 border-t border-gray-200 pt-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">CHI Score:</span>
          <span className="font-semibold text-gray-900">
            {content.chiScore.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Confidence:</span>
          <span className="font-semibold text-gray-900">
            {(content.confidence * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Top Hazards */}
      {content.topHazards && content.topHazards.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-gray-700 mb-2">Top Hazard Factors:</h5>
          <div className="space-y-1">
            {content.topHazards.slice(0, 3).map((hazard, idx) => (
              <div key={idx} className="text-xs">
                <p className="font-medium text-gray-700">{hazard.name}</p>
                <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      hazard.impact === 'high'
                        ? 'bg-red-500'
                        : hazard.impact === 'medium'
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                    }`}
                    style={{ width: `${hazard.severity * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
