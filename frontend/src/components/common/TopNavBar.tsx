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
      <div className="px-4 py-2">
        <div className="flex items-center justify-between">

          {/* VSS Logo + System Title */}
          <div className="flex items-center gap-3">
            {/* VSS Logo */}
            <img
              src="/vmhlss/vss-logo.svg"
              alt="Vanua Spatial Solutions"
              className="w-12 h-12 rounded-lg shadow-sm"
              title="Vanua Spatial Solutions"
            />

            {/* Title block */}
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold text-gray-900 leading-tight tracking-tight">
                  VMHLSS
                </h1>
                <span className="text-xs font-medium text-white bg-green-700 px-2 py-0.5 rounded-full leading-none">
                  v1.0
                </span>
              </div>
              <p className="text-xs text-gray-500 leading-tight">
                Vanuatu Multi-Hazard Land Suitability System
              </p>
              <p className="text-xs font-semibold text-green-700 leading-tight tracking-wide">
                Vanua Spatial Solutions
              </p>
            </div>
          </div>

          {/* Workspace Tabs */}
          <div className="flex gap-1">
            {workspaceTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => navigate(tab.path)}
                className={`px-3 py-2 rounded-lg font-medium text-sm transition-all ${
                  activeTab === tab.id
                    ? 'bg-green-100 text-green-700 border-b-2 border-green-600'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {t(tab.label)}
              </button>
            ))}
          </div>

          {/* Right side: Language toggle + VSS attribution */}
          <div className="flex items-center gap-3">
            {/* Language Toggle */}
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
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

            {/* VSS small logo badge on right */}
            <div className="hidden lg:flex items-center gap-1.5 border-l border-gray-200 pl-3">
              <img
                src="/vmhlss/vss-logo.svg"
                alt="VSS"
                className="w-6 h-6 rounded"
              />
              <span className="text-xs text-gray-400 font-medium">
                Built by VSS
              </span>
            </div>
          </div>

        </div>
      </div>
    </nav>
  );
}
