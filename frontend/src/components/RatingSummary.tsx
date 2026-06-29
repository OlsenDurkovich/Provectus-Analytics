// Overview "Clients" card: a per-rating roll-up with an Average / Best / Worst
// toggle. Best = the most efficient completed student in that rating (lowest
// cost); Worst = the least efficient (highest cost). The detailed individual
// roster now lives on the Flights tab.
import { useState } from 'react';
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
const RATING_ORDER: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];

type Mode = 'avg' | 'best' | 'worst';
const MODES: { key: Mode; label: string }[] = [
  { key: 'avg', label: 'Average' },
  { key: 'best', label: 'Best' },
  { key: 'worst', label: 'Worst' },
];

type SummaryRow = {
  rating: RatingCode;
  basis: string; // "Average · n=4" or a student name
  cost: number;
  hours: number;
  days: number;
  n: number;
};

function fmtCost(v: number): string {
  return v > 0 ? `$${Math.round(v).toLocaleString()}` : '—';
}

function summarize(rows: ClientRow[], mode: Mode): SummaryRow[] {
  // Best/Worst/Average over *completed* students only — partial in-progress
  // figures would distort the comparison.
  const completed = rows.filter((r) => r.status === 'Completed');
  const out: SummaryRow[] = [];
  for (const rating of RATING_ORDER) {
    const group = completed.filter((r) => r.rating === rating);
    if (group.length === 0) continue;
    const n = group.length;
    if (mode === 'avg') {
      const sum = group.reduce(
        (a, r) => ({ c: a.c + r.costToDate, h: a.h + r.hoursToDate, d: a.d + r.daysEnrolled }),
        { c: 0, h: 0, d: 0 },
      );
      out.push({ rating, basis: `Average · n=${n}`, cost: sum.c / n, hours: sum.h / n, days: sum.d / n, n });
    } else {
      // lowest cost = best (most efficient); highest = worst.
      const pick = [...group].sort((a, b) => a.costToDate - b.costToDate)[mode === 'best' ? 0 : group.length - 1];
      out.push({
        rating,
        basis: pick.name,
        cost: pick.costToDate,
        hours: pick.hoursToDate,
        days: pick.daysEnrolled,
        n,
      });
    }
  }
  return out;
}

type Props = {
  rows: ClientRow[];
  filterRating?: RatingCode | null;
  onClearFilter?: () => void;
};

export function RatingSummary({ rows, filterRating, onClearFilter }: Props) {
  const [mode, setMode] = useState<Mode>('avg');
  const all = summarize(rows, mode);
  const summary = filterRating ? all.filter((r) => r.rating === filterRating) : all;

  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Clients · by rating</div>
          <div className="card-sub">
            {mode === 'avg'
              ? 'Average across completed students in each rating'
              : `${mode === 'best' ? 'Most' : 'Least'} efficient completed student per rating (by cost)`}
            {filterRating ? ` — filtered to ${filterRating}` : ''}
          </div>
        </div>
        <div className="row" style={{ gap: 8 }}>
          {filterRating && onClearFilter && (
            <button className="btn btn-outline" type="button" onClick={onClearFilter}>
              Clear filter
            </button>
          )}
          <div className="seg">
            {MODES.map((m) => (
              <button
                key={m.key}
                type="button"
                className={`seg-opt ${mode === m.key ? 'active' : ''}`}
                onClick={() => setMode(m.key)}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th style={{ width: '16%' }}>Rating</th>
              <th>{mode === 'avg' ? 'Basis' : 'Student'}</th>
              <th className="num" style={{ width: '14%' }}>Cost</th>
              <th className="num" style={{ width: '12%' }}>Hours</th>
              <th className="num" style={{ width: '12%' }}>Days</th>
            </tr>
          </thead>
          <tbody>
            {summary.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="empty">
                    <div className="empty-title">No completed students</div>
                    <div className="empty-sub">
                      Averages and best/worst appear once students reach checkride.
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              summary.map((r) => {
                const meta = RATING_META[r.rating];
                return (
                  <tr key={r.rating}>
                    <td>
                      <span className="rating-chip" style={{ background: meta.color }}>{r.rating}</span>
                      <span className="muted tiny" style={{ marginLeft: 8 }}>{meta.name}</span>
                    </td>
                    <td>{r.basis}</td>
                    <td className="num">{fmtCost(r.cost)}</td>
                    <td className="num">{r.hours.toFixed(1)}</td>
                    <td className="num">{Math.round(r.days).toLocaleString()}</td>
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
