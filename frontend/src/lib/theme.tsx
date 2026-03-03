import { createContext, useContext, useEffect, useState } from 'react';
import { getUIPreferences, updateUIPreferences } from './api';

export type ThemeName = 'sunset' | 'synthwave' | 'ocean' | 'metallic' | 'pasture';

export interface ThemeMetadata {
  label: string;
  description: string;
  swatches: string[];
}

const THEME_LIST: ThemeName[] = ['sunset', 'synthwave', 'ocean', 'metallic', 'pasture'];

export const THEME_METADATA: Record<ThemeName, ThemeMetadata> = {
  sunset: {
    label: 'Sunset',
    description: 'Warm amber base with sandy neutrals',
    swatches: ['#ec7520', '#f6b676', '#6d3829'],
  },
  synthwave: {
    label: 'Synthwave',
    description: 'Neon magenta, violet, and teal highlights',
    swatches: ['#ff2d95', '#7130ff', '#23d9d6'],
  },
  ocean: {
    label: 'Ocean',
    description: 'Deep blues with seafoam gradients',
    swatches: ['#0f6fff', '#00b8d9', '#013a63'],
  },
  metallic: {
    label: 'Metallic',
    description: 'Brushed steel with electric cyan accents',
    swatches: ['#6c757d', '#adb5bd', '#1de9b6'],
  },
  pasture: {
    label: 'Pasture',
    description: 'Fresh greens and sunlit yellows',
    swatches: ['#0c8f46', '#9fe870', '#f4d35e'],
  },
};

interface ThemeContextType {
  theme: ThemeName;
  setTheme: (name: ThemeName) => void;
  themes: ThemeName[];
  metadata: typeof THEME_METADATA;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'sunset',
  setTheme: () => {},
  themes: THEME_LIST,
  metadata: THEME_METADATA,
});

const THEME_KEY = 'regia_theme';

const getInitialTheme = (): ThemeName => {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(THEME_KEY) as ThemeName | null;
    if (saved && THEME_LIST.includes(saved)) {
      return saved;
    }
  }
  return 'sunset';
};

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(getInitialTheme);

  const applyTheme = (name: ThemeName) => {
    setThemeState(name);
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', name);
    }
    if (typeof window !== 'undefined') {
      localStorage.setItem(THEME_KEY, name);
    }
  };

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }, [theme]);

  useEffect(() => {
    getUIPreferences()
      .then((r) => {
        const serverTheme = r.data.theme as ThemeName;
        if (serverTheme && THEME_LIST.includes(serverTheme) && serverTheme !== theme) {
          applyTheme(serverTheme);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSetTheme = (name: ThemeName) => {
    applyTheme(name);
    updateUIPreferences({ theme: name }).catch(() => {});
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme: handleSetTheme, themes: THEME_LIST, metadata: THEME_METADATA }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
