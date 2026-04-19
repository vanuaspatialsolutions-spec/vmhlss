import { useEffect, useState } from 'react';
import { useAuthStore, useAnalysisStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';
import { apiService } from '../../services/api';
import type { Report } from '../../types/index';

const reportTypes = [
  {
    id: 'suitability_summary',
    name: 'Suitability Summary',
    description: 'Overall suitability assessment and classification',
    icon: '📊',
  },
  {
    id: 'hazard_assessment',
    name: 'Hazard Assessment',
    description: 'Detailed hazard analysis and risk mapping',
    icon: '⚠️',
  },
  {
    id: 'data_quality',
    name: 'Data Quality Report',
    description: 'Input data quality and gap analysis',
    icon: '✓',
  },
  {
    id: 'decision_support',
    name: 'Decision Support',
    description: 'Recommendations for planners and decision-makers',
    icon: '💡',
  },
  {
    id: 'technical_analysis',
    name: 'Technical Analysis',
    description: 'Detailed methodology and technical specifications',
    icon: '🔬',
  },
];

const reportFormats = ['pdf', 'html', 'geojson', 'csv'];

export default function ReportsWorkspace() {
  const { language } = useAuthStore();
  const { t: _t } = useTranslation(language);
  const { currentAnalysis } = useAnalysisStore();
  const [reports, setReports] = useState<Report[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'html' | 'geojson' | 'csv'>('pdf');

  useEffect(() => {
    const load = () => { /* placeholder */ };
    // Load persisted reports from local engine
    import('../../services/localEngine').then(({ getReports }) => {
      setReports(getReports());
    });
    const handler = () => {
      import('../../services/localEngine').then(({ getReports }) => setReports(getReports()));
    };
    window.addEventListener('vmhlss:reports', handler);
    return () => window.removeEventListener('vmhlss:reports', handler);
    void load;
  }, []);

  const handleGenerateReport = async (reportType: string) => {
    // Generate against latest analysis in history, or current
    const { getAnalysisHistory } = await import('../../services/localEngine');
    const history = getAnalysisHistory();
    const target = currentAnalysis ?? history[0];
    if (!target) {
      alert('Run an analysis on the Map & Query tab first, then come back to generate a report.');
      return;
    }
    setGenerating(reportType);
    try {
      const report = await apiService.generateReport(target.id, reportType, selectedFormat);
      setReports(prev => [report, ...prev]);
    } catch (err) {
      console.error('Report generation failed:', err);
    } finally {
      setGenerating(null);
    }
  };

  const handleDownloadReport = async (reportId: string) => {
    const { getReports, downloadReport } = await import('../../services/localEngine');
    const report = getReports().find(r => r.id === reportId);
    if (report) downloadReport(report as Report & { htmlContent?: string });
  };

  return (
    <div className="w-full h-full overflow-auto bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Reports</h1>
          <p className="text-gray-600">
            Generate and export analysis reports in multiple formats
          </p>
        </div>

        {/* Analysis Status */}
        {!currentAnalysis && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm font-medium text-yellow-900">
              ⚠️ No analysis available. Run an analysis first to generate reports.
            </p>
          </div>
        )}

        {currentAnalysis && (
          <>
            {/* Format Selection */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-lg font-bold text-gray-900 mb-4">Output Format</h2>
              <div className="flex gap-4">
                {reportFormats.map((format) => (
                  <label
                    key={format}
                    className="flex items-center gap-2 cursor-pointer"
                  >
                    <input
                      type="radio"
                      value={format}
                      checked={selectedFormat === format}
                      onChange={(e) =>
                        setSelectedFormat(e.target.value as any)
                      }
                      className="w-4 h-4 text-green-600"
                    />
                    <span className="text-sm font-medium text-gray-900 uppercase">
                      {format}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Report Type Selection */}
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4">Report Types</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {reportTypes.map((type) => (
                  <div
                    key={type.id}
                    className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-all"
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-3xl">{type.icon}</span>
                      <div className="flex-1">
                        <h3 className="font-bold text-gray-900">{type.name}</h3>
                        <p className="text-sm text-gray-600 mb-3">
                          {type.description}
                        </p>
                        <button
                          onClick={() => handleGenerateReport(type.id)}
                          disabled={generating === type.id}
                          className={`w-full py-2 px-4 rounded-lg font-medium text-sm transition-all ${
                            generating === type.id
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-green-600 text-white hover:bg-green-700 active:scale-95'
                          }`}
                        >
                          {generating === type.id ? (
                            <span className="flex items-center justify-center gap-2">
                              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                              Generating...
                            </span>
                          ) : (
                            'Generate Report'
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Generated Reports */}
        {reports.length > 0 && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 mb-4">
              Generated Reports ({reports.length})
            </h2>
            <div className="space-y-3">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between"
                >
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-900">{report.title}</h3>
                    <div className="flex gap-3 mt-2 text-xs text-gray-600">
                      <span>📄 {report.format.toUpperCase()}</span>
                      <span>✓ {report.pageCount || 0} pages</span>
                      <span>
                        🕒{' '}
                        {report.generatedAt
                          ? new Date(report.generatedAt).toLocaleDateString()
                          : 'Pending'}
                      </span>
                    </div>
                  </div>
                  {report.status === 'completed' && (
                    <button
                      onClick={() => handleDownloadReport(report.id)}
                      className="ml-4 py-2 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-all"
                    >
                      Download
                    </button>
                  )}
                  {report.status === 'generating' && (
                    <div className="ml-4 text-sm text-gray-600">
                      Generating...
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
