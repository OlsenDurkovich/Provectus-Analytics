import { useEffect } from 'react';

type Handlers = {
  onCmdK?: () => void;
  onCollapseSidebar?: () => void;
  onToggleTheme?: () => void;
  onNavOverview?: () => void;
  onNavRating?: () => void;
  onNavStudent?: () => void;
  onNavInstructor?: () => void;
  onNavFlights?: () => void;
};

function isEditable(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false;
  if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') return true;
  if (el.isContentEditable) return true;
  return false;
}

export function useShortcuts(h: Handlers) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        h.onCmdK?.();
        return;
      }
      if (mod && e.key === '\\') {
        e.preventDefault();
        h.onCollapseSidebar?.();
        return;
      }
      if (mod && e.shiftKey && e.key.toLowerCase() === 't') {
        e.preventDefault();
        h.onToggleTheme?.();
        return;
      }
      if (isEditable(e.target)) return;
      const k = e.key.toLowerCase();
      if (k === 'o') h.onNavOverview?.();
      else if (k === 'r') h.onNavRating?.();
      else if (k === 's') h.onNavStudent?.();
      else if (k === 'i') h.onNavInstructor?.();
      else if (k === 'f') h.onNavFlights?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [h]);
}
