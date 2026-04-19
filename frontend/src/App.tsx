import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore, useUIStore } from './store/index';
import { login as localLogin, getStoredUser } from './services/localEngine';
import MapQueryWorkspace from './components/workspaces/MapQueryWorkspace';
import DataDashboard from './components/workspaces/DataDashboard';
import DocumentWorkspace from './components/workspaces/DocumentWorkspace';
import GeoreferencingWorkspace from './components/workspaces/GeoreferencingWorkspace';
import ReportsWorkspace from './components/workspaces/ReportsWorkspace';
import TopNavBar from './components/common/TopNavBar';
import StatusBar from './components/common/StatusBar';

function App() {
  useUIStore(); // ensure store is initialized
  const { setUser, setToken, isAuthenticated } = useAuthStore();

  useEffect(() => {
    // Auto-authenticate with local VSS admin user — no server required
    if (!isAuthenticated()) {
      const stored = getStoredUser();
      if (stored) {
        setUser(stored);
        setToken(`local-token-${Date.now()}`);
      } else {
        const { user, tokens } = localLogin({ email: 'admin@vss.vu', password: '' });
        setUser(user);
        setToken(tokens.accessToken);
      }
    }
  }, [isAuthenticated, setUser, setToken]);

  return (
    <Router basename="/vmhlss">
      <div className="flex flex-col h-screen bg-gray-50">
        <TopNavBar />
        <div className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<MapQueryWorkspace />} />
            <Route path="/data" element={<DataDashboard />} />
            <Route path="/documents" element={<DocumentWorkspace />} />
            <Route path="/georef" element={<GeoreferencingWorkspace />} />
            <Route path="/reports" element={<ReportsWorkspace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <StatusBar />
      </div>
    </Router>
  );
}

export default App;
