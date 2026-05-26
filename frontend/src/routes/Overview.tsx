import type { RangeKey } from '../data/types';

type Props = { range: RangeKey };

export default function Overview({ range: _range }: Props) {
  return (
    <div className="page-head">
      <div className="eyebrow">Cohort overview</div>
      <h1>All ratings</h1>
      <div className="page-sub">Overview tab — wiring in progress.</div>
    </div>
  );
}
