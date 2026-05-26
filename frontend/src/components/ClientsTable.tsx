import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from './Icon';
import { Skel } from './primitives';
import type { ClientRow, RatingCode } from '../data/types';

const RATING_META: Record<RatingCode, { name: string; color: string }> = {
  PPL: { name: 'Private Pilot', color: '#6E56F8' },
  IFR: { name: 'Instrument', color: '#3DD68C' },
  COM: { name: 'Commercial SE', color: '#22D3EE' },
  AMEL: { name: 'Multi-Engine', color: '#F59E0B' },
  CFI: { name: 'CFI', color: '#EC4899' },
  CFII: { name: 'CFII', color: '#A78BFA' },
  MEI: { name: 'MEI', color: '#F472B6' },
};

type ColKey = 'name' | 'rating' | 'hours' | 'days' | 'progress' | 'status';

const CLIENT_COLS: Array<{
  key: ColKey;
  label: string;
  align: 'left' | 'right';
  width: string;
  noSort?: boolean;
}> = [
  { key: 'name', label: 'Client', align: 'left', width: '28%' },
  { key: 'rating', label: 'Rating', align: 'left', width: '18%' },
  { key: 'hours', label: 'Hours', align: 'right', width: '12%' },
  { key: 'days', label: 'Days', align: 'right', width: '10%' },
  { key: 'progress', label: 'Progress', align: 'left', width: '20%', noSort: true },
  { key: 'status', label: 'Status', align: 'left', width: '12%' },
];

type SortState = { key: ColKey; dir: 'asc' | 'desc' };

type Props = {
  rows: ClientRow[];
  loading?: boolean;
  filterRating?: RatingCode | null;
  onClearFilter?: () => void;
};

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((s) => s[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

function rowSortValue(row: ClientRow, key: ColKey): string | number {
  switch (key) {
    case 'name': return row.name;
    case 'rating': return row.rating;
    case 'hours': return row.hoursToDate;
    case 'days': return row.daysEnrolled;
    case 'status': return row.status;
    default: return 0;
  }
}

export function ClientsTable({ rows, loading = false, filterRating, onClearFilter }: Props) {
  const [sort, setSort] = useState<SortState>({ key: 'days', dir: 'desc' });
  const [search, setSearch] = useState('');
  const [visibleCols, setVisibleCols] = useState<Record<ColKey, boolean>>(() =>
    Object.fromEntries(CLIENT_COLS.map((c) => [c.key, true])) as Record<ColKey, boolean>
  );
  const [colMenuOpen, setColMenuOpen] = useState(false);
  const colMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (colMenuRef.current && !colMenuRef.current.contains(e.target as Node)) {
        setColMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    let r = rows;
    if (filterRating) r = r.filter((row) => row.rating === filterRating);
    if (s) {
      r = r.filter(
        (row) =>
          row.name.toLowerCase().includes(s) || row.rating.toLowerCase().includes(s)
      );
    }
    const dir = sort.dir === 'asc' ? 1 : -1;
    return [...r].sort((a, b) => {
      const av = rowSortValue(a, sort.key);
      const bv = rowSortValue(b, sort.key);
      if (typeof av === 'string' && typeof bv === 'string') return av.localeCompare(bv) * dir;
      return ((av as number) - (bv as number)) * dir;
    });
  }, [rows, search, sort, filterRating]);

  function toggleSort(key: ColKey) {
    const col = CLIENT_COLS.find((c) => c.key === key);
    if (col?.noSort) return;
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }));
  }

  function exportCsv() {
    const cols = CLIENT_COLS.filter((c) => visibleCols[c.key] && c.key !== 'progress');
    const head = cols.map((c) => c.label).join(',');
    const lines = filtered.map((r) =>
      cols
        .map((c) => {
          let v: string | number = rowSortValue(r, c.key);
          if (c.key === 'hours') v = (r.hoursToDate).toFixed(1);
          if (typeof v === 'string' && (v.includes(',') || v.includes(' '))) v = `"${v}"`;
          return v;
        })
        .join(',')
    );
    const csv = [head, ...lines].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'clients.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  const visibleCount = (Object.values(visibleCols) as boolean[]).filter(Boolean).length;

  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Clients</div>
          <div className="card-sub">
            {filterRating
              ? `Filtered to ${filterRating} — click the ${filterRating} bar again to clear`
              : 'All active and recently completed clients'}
          </div>
        </div>
        <div className="row" style={{ gap: 6 }}>
          <div className="muted tiny">{filtered.length} clients</div>
          {filterRating && onClearFilter && (
            <button className="btn btn-outline" type="button" onClick={onClearFilter}>
              Clear filter
            </button>
          )}
        </div>
      </div>

      <div className="table-toolbar">
        <div className="table-search">
          <Icon name="search" size={12} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter by name or rating…"
            type="text"
          />
        </div>
        <div className="spacer" />
        <div ref={colMenuRef} style={{ position: 'relative' }}>
          <button className="btn" type="button" onClick={() => setColMenuOpen((o) => !o)}>
            <Icon name="columns" size={12} />
            Columns
          </button>
          {colMenuOpen && (
            <div className="dpop" style={{ right: 0, top: 'calc(100% + 6px)', minWidth: 180 }}>
              {CLIENT_COLS.map((c) => (
                <button
                  key={c.key}
                  type="button"
                  className="dpop-opt"
                  onClick={() => setVisibleCols((v) => ({ ...v, [c.key]: !v[c.key] }))}
                >
                  <span>{c.label}</span>
                  {visibleCols[c.key] && <Icon name="check" size={13} />}
                </button>
              ))}
            </div>
          )}
        </div>
        <button className="btn" type="button" onClick={exportCsv}>
          <Icon name="download" size={12} />
          Export CSV
        </button>
      </div>

      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              {CLIENT_COLS.filter((c) => visibleCols[c.key]).map((c) => (
                <th
                  key={c.key}
                  className={`${c.align === 'right' ? 'num ' : ''}${sort.key === c.key ? 'active' : ''}`}
                  style={{ width: c.width }}
                  onClick={() => toggleSort(c.key)}
                >
                  {c.label}
                  {!c.noSort && (
                    <span className="sort-ind">
                      {sort.key === c.key ? (sort.dir === 'asc' ? '↑' : '↓') : '↕'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {CLIENT_COLS.filter((c) => visibleCols[c.key]).map((c) => (
                    <td key={c.key} className={c.align === 'right' ? 'num' : ''}>
                      <Skel w={c.key === 'name' ? '60%' : '40%'} h={10} />
                    </td>
                  ))}
                </tr>
              ))
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={visibleCount}>
                  <div className="empty">
                    <div className="empty-title">No clients match</div>
                    <div className="empty-sub">Try a different search term or clear the filter.</div>
                    <button className="btn btn-outline" type="button" onClick={() => setSearch('')}>
                      Clear search
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((r) => {
                const meta = RATING_META[r.rating];
                return (
                  <tr key={r.id}>
                    {visibleCols.name && (
                      <td>
                        <div className="path-cell">
                          <span className="client-avatar">{initials(r.name)}</span>
                          <span className="path" style={{ color: 'var(--fg)' }}>{r.name}</span>
                        </div>
                      </td>
                    )}
                    {visibleCols.rating && (
                      <td>
                        <span className="rating-chip" style={{ background: meta.color }}>{r.rating}</span>
                        <span className="muted tiny" style={{ marginLeft: 8 }}>{meta.name}</span>
                      </td>
                    )}
                    {visibleCols.hours && (
                      <td className="num">{r.hoursToDate.toFixed(1)}</td>
                    )}
                    {visibleCols.days && (
                      <td className="num">{r.daysEnrolled}</td>
                    )}
                    {visibleCols.progress && (
                      <td>
                        <div className="progress-bar">
                          <div
                            className="progress-fill"
                            style={{
                              width: `${Math.min(100, r.progressPct * 100).toFixed(0)}%`,
                              background: meta.color,
                            }}
                          />
                        </div>
                        <div className="muted tiny" style={{ marginTop: 4 }}>
                          {Math.min(100, Math.round(r.progressPct * 100))}% to median
                        </div>
                      </td>
                    )}
                    {visibleCols.status && (
                      <td>
                        <span className={`status-pill status-${r.status.replace(/\s+/g, '-').toLowerCase()}`}>
                          {r.status}
                        </span>
                      </td>
                    )}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
