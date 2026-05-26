import { useEffect, useState, useCallback } from 'react';
import type { ThemeKey } from '../data/types';

const STORAGE_KEY = 'pv-theme';

function readInitial(): ThemeKey {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // localStorage unavailable
  }
  const attr = document.documentElement.getAttribute('data-theme');
  if (attr === 'dark' || attr === 'light') return attr;
  return 'dark';
}

export function useTheme() {
  const [theme, setTheme] = useState<ThemeKey>(readInitial);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggle, setTheme };
}
