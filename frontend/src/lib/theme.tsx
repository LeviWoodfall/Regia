import { createContext, useContext, useEffect, useState } from 'react';
import { getUIPreferences, updateUIPreferences } from './api';

interface ThemeContextType {
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'light',
  toggleTheme: () => {},
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('regia_theme') as 'light' | 'dark') || 'light';
  });

  useEffect(() => {
    // Load server preference
    getUIPreferences()
      .then((r) => {
        const serverTheme = r.data.theme as 'light' | 'dark';
        if (serverTheme && serverTheme !== theme) {
          setTheme(serverTheme);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('regia_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    updateUIPreferences({ theme: next }).catch(() => {});
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
