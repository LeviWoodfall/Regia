import { createContext, useContext, useEffect, useState } from 'react';
import { getAuthStatus, login as apiLogin, logout as apiLogout } from './api';

interface User {
  username: string;
  display_name: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  authenticated: boolean;
  setupCompleted: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  authenticated: false,
  setupCompleted: false,
  loading: true,
  login: async () => false,
  logout: async () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authenticated, setAuthenticated] = useState(false);
  const [setupCompleted, setSetupCompleted] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const resp = await getAuthStatus();
      setSetupCompleted(resp.data.setup_completed);
      setAuthenticated(resp.data.authenticated);
      if (resp.data.user) {
        setUser(resp.data.user);
      } else {
        setUser(null);
      }
    } catch {
      // API not available — allow access (dev mode)
      setSetupCompleted(false);
      setAuthenticated(false);
    }
    setLoading(false);
  };

  useEffect(() => {
    refresh();
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const resp = await apiLogin({ username, password });
      localStorage.setItem('regia_token', resp.data.token);
      setUser({ username: resp.data.username, display_name: resp.data.display_name, is_admin: true });
      setAuthenticated(true);
      return true;
    } catch {
      return false;
    }
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch { /* ignore */ }
    localStorage.removeItem('regia_token');
    setUser(null);
    setAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ user, authenticated, setupCompleted, loading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
