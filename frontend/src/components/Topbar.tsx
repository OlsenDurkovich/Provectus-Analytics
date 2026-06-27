// Topbar — ported from design_handoff_provectus_analytics/design/panels.jsx
import { useEffect, useRef, useState } from 'react';
import { Icon } from './Icon';
import { useMeta } from '../data/queries';
import { RANGES } from '../data/ranges';
import type { RangeKey, ThemeKey } from '../data/types';

type Props = {
  breadcrumb: string;
  range: RangeKey;
  onRangeChange: (r: RangeKey) => void;
  onToggleSidebar: () => void;
  onOpenCmdK: () => void;
  theme: ThemeKey;
  onThemeToggle: () => void;
  onImport: () => void;
  importPending?: boolean;
  showRangePicker?: boolean;
  userEmail?: string | null;
  onLogout?: () => void;
};

export function Topbar({
  breadcrumb,
  range,
  onRangeChange,
  onToggleSidebar,
  onOpenCmdK,
  theme,
  onThemeToggle,
  onImport,
  importPending = false,
  showRangePicker = true,
  userEmail = null,
  onLogout,
}: Props) {
  const meta = useMeta();
  const isLive = meta.data?.mode === 'real';
  const liveCount = meta.data?.liveClientCount ?? 0;

  const [dpopOpen, setDpopOpen] = useState(false);
  const dpopRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (dpopRef.current && !dpopRef.current.contains(e.target as Node)) {
        setDpopOpen(false);
      }
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  return (
    <header className="topbar">
      <button
        className="btn btn-icon"
        onClick={onToggleSidebar}
        title="Toggle sidebar"
        type="button"
      >
        <Icon name="sidebar" size={15} />
      </button>
      <div className="breadcrumb">
        <span>Provectus · FSP exports</span>
        <span className="breadcrumb-sep">
          <Icon name="chevronRight" size={12} />
        </span>
        <span className="breadcrumb-current">{breadcrumb}</span>
      </div>

      <div className="topbar-spacer" />

      <button className="search-trigger" onClick={onOpenCmdK} type="button">
        <Icon name="search" size={14} />
        <span className="search-trigger-label">
          Search clients, ratings, flights…
        </span>
        <span style={{ display: 'inline-flex', gap: 3 }}>
          <span className="kbd">⌘</span>
          <span className="kbd">K</span>
        </span>
      </button>

      <div className="live-pill" title={isLive ? 'Real FSP data' : 'Synthetic data'}>
        <span className="live-dot" />
        {isLive
          ? `Live · ${liveCount} client${liveCount === 1 ? '' : 's'}`
          : 'Synthetic data'}
      </div>

      {showRangePicker && (
        <div className="dpop-wrap" ref={dpopRef}>
          <button
            className="btn btn-outline"
            onClick={() => setDpopOpen((o) => !o)}
            type="button"
          >
            <Icon name="calendar" size={13} />
            {RANGES[range].label}
            <Icon name="chevron" size={12} />
          </button>
          {dpopOpen && (
            <div className="dpop">
              {(Object.entries(RANGES) as [RangeKey, { label: string }][]).map(
                ([k, v]) => (
                  <button
                    key={k}
                    className={'dpop-opt ' + (range === k ? 'active' : '')}
                    onClick={() => {
                      onRangeChange(k);
                      setDpopOpen(false);
                    }}
                    type="button"
                  >
                    <span>{v.label}</span>
                    {range === k && <Icon name="check" size={13} />}
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      )}

      <button
        className="btn btn-outline"
        onClick={onImport}
        type="button"
        disabled={importPending}
      >
        <Icon name="download" size={13} />
        {importPending ? 'Importing…' : 'Import FSP'}
      </button>

      <button
        className="btn btn-icon"
        onClick={onThemeToggle}
        title="Toggle theme"
        type="button"
      >
        <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={14} />
      </button>

      {userEmail && onLogout && (
        <button
          className="btn btn-outline"
          onClick={onLogout}
          title={`Sign out ${userEmail}`}
          type="button"
        >
          Sign out
        </button>
      )}

    </header>
  );
}
