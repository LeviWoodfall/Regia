import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './lib/theme';
import { AuthProvider, useAuth } from './lib/auth';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import Emails from './pages/Emails';
import Documents from './pages/Documents';
import FileBrowser from './pages/FileBrowser';
import SearchPage from './pages/SearchPage';
import ReggiePage from './pages/ReggiePage';
import LogsPage from './pages/LogsPage';
import SettingsPage from './pages/SettingsPage';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { authenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-warm-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-sunset-400 border-t-transparent" />
      </div>
    );
  }

  // Check if URL has a reset token — always show login page for that
  const hasResetToken = window.location.search.includes('token=');

  if (!authenticated || hasResetToken) {
    return <LoginPage />;
  }

  return <>{children}</>;
}

function AppLayout() {
  return (
    <AuthGuard>
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
    </AuthGuard>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
