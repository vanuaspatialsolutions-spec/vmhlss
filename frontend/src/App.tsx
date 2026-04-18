import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore, useUIStore } from './store/index';
import MapQueryWorkspace from './components/workspaces/MapQueryWorkspace';
import DataDashboard from './components/workspaces/DataDashboard';
import DocumentWorkspace from './components/workspaces/DocumentWorkspace';
import GeoreferencingWorkspace from './components/workspaces/GeoreferencingWorkspace';
import ReportsWorkspace from './components/workspaces/ReportsWorkspace';
import TopNavBar from './components/common/TopNavBar';
import StatusBar from './components/common/StatusBar';

function App() {
  useUIStore(); // ensure store is initialized

  useEffect(() => {
    // Initialize auth check if needed
    const token = useAuthStore.getState().token;
    if (!token) {
      console.log('No auth token found');
    }
  }, []);

  return (
    <Router>
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
