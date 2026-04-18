import { useAuthStore, useAnalysisStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';

const personaOptions = ['Developer', 'Agriculture Expert', 'Farmer', 'GIS User', 'Engineer'];

interface QueryPanelProps {
  onRunAnalysis: () => Promise<void>;
  onExport: () => void;
  isProcessing: boolean;
  hasResults: boolean;
}

export default function QueryPanel({
  onRunAnalysis,
  onExport,
  isProcessing,
  hasResults,
}: QueryPanelProps) {
  const { language } = useAuthStore();
  const { t } = useTranslation(language);
  const { currentAoi, assessmentType, personasRequested, setAssessmentType, setPersonas } =
    useAnalysisStore();

  const handlePersonaToggle = (persona: string) => {
    setPersonas(
      personasRequested.includes(persona)
        ? personasRequested.filter((p) => p !== persona)
        : [...personasRequested, persona]
    );
  };

  return (
    <div className="p-4 space-y-6">
      {/* Assessment Type */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">{t('mapquery.assessmenttype')}</h3>
        <div className="space-y-2">
          {['development', 'agriculture', 'both'].map((type) => (
            <label key={type} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="assessment"
                value={type}
                checked={assessmentType === type}
                onChange={(e) => setAssessmentType(e.target.value as any)}
                className="w-4 h-4 text-green-600 border-gray-300 focus:ring-green-500"
              />
              <span className="text-sm text-gray-700 capitalize">{t(`mapquery.${type}`)}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Personas */}
      <div>
        <h3 className="font-semibold text-gray-900 mb-3">{t('mapquery.personas')}</h3>
        <div className="space-y-2">
          {personaOptions.map((persona) => (
            <label key={persona} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={personasRequested.includes(persona)}
                onChange={() => handlePersonaToggle(persona)}
                className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
              />
              <span className="text-sm text-gray-700">{persona}</span>
            </label>
          ))}
        </div>
      </div>

      {/* AOI Status */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-sm font-medium text-blue-900">
          {currentAoi
            ? '✓ Area of Interest drawn'
            : '○ Draw an area on the map to start'}
        </p>
      </div>

      {/* Run Analysis Button */}
      <button
        onClick={onRunAnalysis}
        disabled={!currentAoi || isProcessing}
        className={`w-full py-2 px-4 rounded-lg font-semibold text-white transition-all ${
          isProcessing || !currentAoi
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-green-600 hover:bg-green-700 active:scale-95'
        }`}
      >
        {isProcessing ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            Processing...
          </span>
        ) : (
          t('mapquery.runanalysis')
        )}
      </button>

      {/* Export Button */}
      {hasResults && (
        <button
          onClick={onExport}
          className="w-full py-2 px-4 rounded-lg font-semibold bg-blue-600 text-white hover:bg-blue-700 active:scale-95 transition-all"
        >
          {t('mapquery.export')}
        </button>
      )}
    </div>
  );
}
