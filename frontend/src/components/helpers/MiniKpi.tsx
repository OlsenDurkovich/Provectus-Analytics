import type { ReactNode } from 'react';

type Props = {
  label: string;
  value: string;
  sub?: string;
  deltaNode?: ReactNode;
};

export function MiniKpi({ label, value, sub, deltaNode }: Props) {
  return (
    <div className="card minikpi">
      <div className="minikpi-label">{label}</div>
      <div className="minikpi-value num num-tight">{value}</div>
      {deltaNode && <div className="minikpi-delta">{deltaNode}</div>}
      {sub && <div className="minikpi-sub">{sub}</div>}
    </div>
  );
}
