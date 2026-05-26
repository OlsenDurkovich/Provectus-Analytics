import type { ReactNode } from 'react';

type Overlay = { label: string; value: string };

type Props = {
  label: string;
  value: string;
  sub?: string;
  deltaNode?: ReactNode;
  overlay?: Overlay;
};

export function BigKpi({ label, value, sub, deltaNode, overlay }: Props) {
  return (
    <div className="card bigkpi">
      <div className="bigkpi-label">{label}</div>
      <div className="bigkpi-value-row">
        <div className="bigkpi-value num num-tight">{value}</div>
        {overlay && (
          <div className="bigkpi-overlay">
            <div className="bigkpi-overlay-name">{overlay.label}</div>
            <div className="bigkpi-overlay-value num num-tight">{overlay.value}</div>
          </div>
        )}
      </div>
      {deltaNode && <div className="bigkpi-delta">{deltaNode}</div>}
      {sub && <div className="bigkpi-sub">{sub}</div>}
    </div>
  );
}
