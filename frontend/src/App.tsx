import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Emails from './pages/Emails';
import Documents from './pages/Documents';
import FileBrowser from './pages/FileBrowser';
import SearchPage from './pages/SearchPage';
import ReggiePage from './pages/ReggiePage';
import LogsPage from './pages/LogsPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-warm-50">
        <Sidebar />
        <div className="flex-1 ml-64 flex flex-col">
          <Header />
          <main className="flex-1 p-6">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/emails" element={<Emails />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/files" element={<FileBrowser />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/reggie" element={<ReggiePage />} />
              <Route path="/logs" element={<LogsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
