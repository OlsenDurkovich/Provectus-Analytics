import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export function usePersistedTab() {
  const location = useLocation();
  useEffect(() => {
    try {
      localStorage.setItem('pv-tab', location.pathname);
    } catch {
      // ignore
    }
  }, [location.pathname]);
}
