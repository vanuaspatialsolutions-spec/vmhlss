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
    // Load mock reports for demo
    const mockReports: Report[] = [
      {
        id: 'report-1',
        analysisId: currentAnalysis?.id || '',
        type: 'suitability_summary',
        format: 'pdf',
        title: 'Suitability Summary - March 2024',
        status: 'completed',
        generatedAt: new Date().toISOString(),
        generatedBy: 'demo-user',
        pageCount: 24,
      },
    ];
    setReports(mockReports);
  }, [currentAnalysis?.id]);

  const handleGenerateReport = async (reportType: string) => {
    if (!currentAnalysis) {
      alert('Please run an analysis first');
      return;
    }

    setGenerating(reportType);

    try {
      const report = await apiService.generateReport(
        currentAnalysis.id,
        reportType,
        selectedFormat
      );
      setReports((prev) => [report, ...prev]);
    } catch (error) {
      console.error('Report generation failed:', error);
      alert('Failed to generate report');
    } finally {
      setGenerating(null);
    }
  };

  const handleDownloadReport = async (reportId: string) => {
    try {
      const blob = await apiService.downloadReport(reportId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `report-${reportId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download report');
    }
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
