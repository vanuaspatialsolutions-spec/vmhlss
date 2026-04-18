import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../store/index';
import { useTranslation } from '../../i18n/index';

const workspaceTabs = [
  { id: 'mapquery', label: 'workspace.mapquery', path: '/' },
  { id: 'data', label: 'workspace.data', path: '/data' },
  { id: 'documents', label: 'workspace.documents', path: '/documents' },
  { id: 'georef', label: 'workspace.georef', path: '/georef' },
  { id: 'reports', label: 'workspace.reports', path: '/reports' },
];

export default function TopNavBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { language, setLanguage } = useAuthStore();
  const { t } = useTranslation(language);

  const getActiveTab = () => {
    const path = location.pathname;
    if (path === '/') return 'mapquery';
    if (path.startsWith('/data')) return 'data';
    if (path.startsWith('/documents')) return 'documents';
    if (path.startsWith('/georef')) return 'georef';
    if (path.startsWith('/reports')) return 'reports';
    return 'mapquery';
  };

  const activeTab = getActiveTab();

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-green-600 to-emerald-700 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">V</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">VMHLSS</h1>
              <p className="text-xs text-gray-600">
                Vanuatu Multi-Hazard Land Suitability System
              </p>
            </div>
          </div>

          {/* Workspace Tabs */}
          <div className="flex gap-2">
            {workspaceTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => navigate(tab.path)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                  activeTab === tab.id
                    ? 'bg-green-100 text-green-700 border-b-2 border-green-600'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {t(tab.label)}
              </button>
            ))}
          </div>

          {/* Language Toggle */}
          <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                language === 'en'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage('bi')}
              className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                language === 'bi'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              BI
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
