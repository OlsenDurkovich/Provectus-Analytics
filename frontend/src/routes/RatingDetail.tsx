import type { RangeKey } from '../data/types';

type Props = { range: RangeKey };

export default function RatingDetail({ range: _range }: Props) {
  return (
    <div className="page-head">
      <div className="eyebrow">Rating detail</div>
      <h1>Rating detail</h1>
      <div className="page-sub">Pick a rating to see its cohort norms.</div>
    </div>
  );
}
