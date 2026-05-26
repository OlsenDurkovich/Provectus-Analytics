import type { RatingCode, RatingsCompletedRow } from '../../data/types';

const RATING_META: Record<RatingCode, { name: string; color: string }> = {
  PPL: { name: 'Private Pilot', color: '#6E56F8' },
  IFR: { name: 'Instrument', color: '#3DD68C' },
  COM: { name: 'Commercial SE', color: '#22D3EE' },
  AMEL: { name: 'Multi-Engine', color: '#F59E0B' },
  CFI: { name: 'CFI', color: '#EC4899' },
  CFII: { name: 'CFII', color: '#A78BFA' },
  MEI: { name: 'MEI', color: '#F472B6' },
};

type Props = { data: RatingsCompletedRow[] };

export function RatingsList({ data }: Props) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="hbar-list">
      {data.map((row) => {
        const meta = RATING_META[row.rating];
        return (
          <div key={row.rating}>
            <div className="hbar-row">
              <div className="hbar-label">
                <span className="rating-chip" style={{ background: meta.color }}>{row.rating}</span>
                <span className="hbar-label-text muted-name">{meta.name}</span>
              </div>
              <div className="hbar-val num">{row.count}</div>
            </div>
            <div className="hbar-track">
              <div
                className="hbar-fill"
                style={{ width: `${((row.count / max) * 100).toFixed(1)}%`, background: meta.color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
