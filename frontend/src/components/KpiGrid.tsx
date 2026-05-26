import { Delta, Sparkline } from './primitives';
import { Icon } from './Icon';
import type { Kpi } from '../data/types';

type Props = {
  kpis: Kpi[];
  focusedKey: string | null;
  onFocus: (key: string | null) => void;
};

export function KpiGrid({ kpis, focusedKey, onFocus }: Props) {
  return (
    <div className="kpi-grid">
      {kpis.map((k) => {
        const isSelected = focusedKey === k.key;
        return (
          <button
            key={k.key}
            type="button"
            className={`card kpi ${isSelected ? 'selected' : ''}`}
            onClick={() => onFocus(isSelected ? null : k.key)}
          >
            <div className="kpi-label">
              {k.label}
              {isSelected && (
                <span style={{ color: 'var(--accent-strong)' }}>
                  <Icon name="filter" size={10} />
                </span>
              )}
            </div>
            <div className="kpi-value num num-tight">{k.value}</div>
            <div className="kpi-meta">
              <Delta value={k.delta} positive={k.positive} />
            </div>
            <div className="kpi-sub">{k.sub}</div>
            <div className="kpi-spark" style={{ color: k.color }}>
              <Sparkline data={k.spark} height={36} />
            </div>
          </button>
        );
      })}
    </div>
  );
}
