import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon, type IconName } from './Icon';
import type { RangeKey } from '../data/types';

type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
  onSetRange: (r: RangeKey) => void;
  onToggleTheme: () => void;
  onImport: () => void;
  onRebuild: (synthetic: boolean) => void;
};

type Item = {
  id: string;
  label: string;
  icon: IconName;
  meta?: string;
  group: string;
  run: () => void;
};

const RANGES: { value: RangeKey; label: string }[] = [
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: '6mo', label: 'Last 6 months' },
  { value: '12mo', label: 'Last 12 months' },
  { value: 'ytd', label: 'Year to date' },
  { value: 'all', label: 'All time' },
];

const NAV: { path: string; label: string; icon: IconName; kbd: string }[] = [
  { path: '/', label: 'Overview', icon: 'overview', kbd: 'O' },
  { path: '/ratings', label: 'Rating detail', icon: 'metrics', kbd: 'R' },
  { path: '/students', label: 'Student', icon: 'users', kbd: 'S' },
  { path: '/instructors', label: 'Instructor', icon: 'users', kbd: 'I' },
  { path: '/insights', label: 'Insights', icon: 'metrics', kbd: 'N' },
  { path: '/summary', label: 'Summary (print / PDF)', icon: 'overview', kbd: 'Y' },
  { path: '/flights', label: 'Flights', icon: 'plane', kbd: 'F' },
];

export function CmdK({
  open,
  onClose,
  onNavigate,
  onSetRange,
  onToggleTheme,
  onImport,
  onRebuild,
}: Props) {
  const [q, setQ] = useState('');
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  const items: Item[] = useMemo(
    () => [
      ...NAV.map<Item>((n) => ({
        id: `nav-${n.path}`,
        label: `Go to ${n.label}`,
        icon: n.icon,
        meta: n.kbd,
        group: 'Navigate',
        run: () => onNavigate(n.path),
      })),
      ...RANGES.map<Item>((r) => ({
        id: `r-${r.value}`,
        label: `Range: ${r.label}`,
        icon: 'calendar',
        group: 'Time range',
        run: () => onSetRange(r.value),
      })),
      {
        id: 'theme',
        label: 'Toggle theme',
        icon: 'moon',
        meta: '⇧⌘T',
        group: 'Actions',
        run: onToggleTheme,
      },
      {
        id: 'import',
        label: 'Import latest FSP exports',
        icon: 'download',
        group: 'Actions',
        run: onImport,
      },
      {
        id: 'rebuild',
        label: 'Rebuild database',
        icon: 'sparkles',
        group: 'Actions',
        run: () => onRebuild(false),
      },
      {
        id: 'rebuild-synth',
        label: 'Rebuild database (synthetic)',
        icon: 'sparkles',
        group: 'Actions',
        run: () => onRebuild(true),
      },
    ],
    [onNavigate, onSetRange, onToggleTheme, onImport, onRebuild],
  );

  const flat = useMemo(() => {
    const qq = q.trim().toLowerCase();
    return qq ? items.filter((it) => it.label.toLowerCase().includes(qq)) : items;
  }, [items, q]);

  useEffect(() => {
    setActive(0);
  }, [q]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(flat.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      flat[active]?.run();
      onClose();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }

  const grouped = useMemo(() => {
    const m = new Map<string, (Item & { idx: number })[]>();
    flat.forEach((it, idx) => {
      const arr = m.get(it.group) ?? [];
      arr.push({ ...it, idx });
      m.set(it.group, arr);
    });
    return [...m.entries()];
  }, [flat]);

  if (!open) return null;

  return (
    <div className="cmdk-backdrop on" onClick={onClose}>
      <div
        className="cmdk"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        role="dialog"
        aria-label="Command palette"
      >
        <div className="cmdk-input-row">
          <Icon name="search" size={16} />
          <input
            ref={inputRef}
            className="cmdk-input"
            placeholder="Type a command or search…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <span className="kbd">ESC</span>
        </div>
        <div className="cmdk-list">
          {grouped.length === 0 && (
            <div className="empty">
              <div className="empty-title">No results</div>
              <div className="empty-sub">Try a different command.</div>
            </div>
          )}
          {grouped.map(([label, list]) => (
            <div key={label}>
              <div className="cmdk-section-label">{label}</div>
              {list.map((it) => (
                <button
                  type="button"
                  key={it.id}
                  className={'cmdk-item ' + (active === it.idx ? 'active' : '')}
                  onMouseEnter={() => setActive(it.idx)}
                  onClick={() => {
                    it.run();
                    onClose();
                  }}
                >
                  <span className="cmdk-item-icon">
                    <Icon name={it.icon} size={15} />
                  </span>
                  <span className="cmdk-item-label">{it.label}</span>
                  {it.meta && <span className="cmdk-item-meta">{it.meta}</span>}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="cmdk-footer">
          <span>
            <span className="kbd">↑</span> <span className="kbd">↓</span> Navigate
          </span>
          <span>
            <span className="kbd">↵</span> Select
          </span>
          <span>
            <span className="kbd">ESC</span> Close
          </span>
        </div>
      </div>
    </div>
  );
}
