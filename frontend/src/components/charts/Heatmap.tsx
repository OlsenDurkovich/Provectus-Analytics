import { Fragment } from 'react';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

type Props = { rows: number[][]; buckets: string[] };

function cellBg(v: number, max: number): string {
  if (max <= 0) return 'var(--bg-elev-2)';
  const norm = v / max;
  if (norm < 0.06) return 'var(--bg-elev-2)';
  return `rgba(110, 86, 248, ${0.12 + norm * 0.72})`;
}

export function Heatmap({ rows, buckets }: Props) {
  const max = Math.max(0, ...rows.flat());
  return (
    <div>
      <div className="heatmap" style={{ gridTemplateColumns: `56px repeat(${buckets.length}, 1fr)` }}>
        <div />
        <div
          className="heatmap-col-labels"
          style={{ gridColumn: '2 / -1', gridTemplateColumns: `repeat(${buckets.length}, 1fr)` }}
        >
          {buckets.map((b, i) => <div key={i}>{b}</div>)}
        </div>
        {rows.map((cells, ri) => (
          <Fragment key={ri}>
            <div className="heatmap-label">{DAY_LABELS[ri] ?? `Row ${ri + 1}`}</div>
            {cells.map((v, ci) => (
              <div
                key={ci}
                className="heatmap-cell"
                style={{ background: cellBg(v, max) }}
                title={`${DAY_LABELS[ri]} · ${buckets[ci]} · ${max ? Math.round((v / max) * 100) : 0}% intensity`}
              />
            ))}
          </Fragment>
        ))}
      </div>
      <div className="heatmap-legend">
        <span>Quieter</span>
        <div className="heatmap-legend-scale">
          {[0.05, 0.25, 0.45, 0.65, 0.85].map((v, i) => (
            <div
              key={i}
              style={{
                background:
                  i === 0 ? 'var(--bg-elev-2)' : `rgba(110, 86, 248, ${0.12 + v * 0.72})`,
              }}
            />
          ))}
        </div>
        <span>Busier</span>
      </div>
    </div>
  );
}
