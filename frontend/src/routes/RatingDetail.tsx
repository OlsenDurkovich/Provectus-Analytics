import { useNavigate, useParams } from 'react-router-dom';
import { BigKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { useRating } from '../data/queries';
import type { RangeKey, RatingCode } from '../data/types';

const CODES: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

type Props = { range: RangeKey };

export default function RatingDetail({ range }: Props) {
  const { code } = useParams<{ code?: string }>();
  const navigate = useNavigate();
  const selected = (CODES.includes(code as RatingCode) ? code : 'PPL') as RatingCode;
  const rating = useRating(selected, range);

  return (
    <div className="rating-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">Detail</div>
          <h1 className="page-title">{rating.data?.name ?? selected}</h1>
          <div className="page-sub">
            Cohort distribution with P25–P75 band · compare an individual to the band.
          </div>
        </div>
        <div className="page-head-tools">
          <Select<RatingCode>
            label="Rating"
            value={selected}
            onChange={(v) => v && navigate(`/ratings/${v}`)}
            options={CODES.map((c) => ({ value: c, label: c }))}
            width={130}
          />
        </div>
      </div>

      {rating.isLoading ? (
        <Skel h={200} />
      ) : rating.data ? (
        <div className="kpi-grid">
          <BigKpi
            label="Alumni (n)"
            value={String(rating.data.n)}
            sub={rating.data.lowSample ? 'Low sample — interpret with care' : 'Sufficient sample'}
          />
          <BigKpi
            label="Median hours"
            value={rating.data.medianHrs.toFixed(1)}
            sub={`P25–P75: ${rating.data.p25Hrs.toFixed(1)} – ${rating.data.p75Hrs.toFixed(1)}`}
          />
          <BigKpi
            label="Median cost"
            value={fmtCost(rating.data.medianCost)}
            sub={`P25–P75: ${fmtCost(rating.data.p25Cost)} – ${fmtCost(rating.data.p75Cost)}`}
          />
          <BigKpi
            label="Median days"
            value={Math.round(rating.data.medianDays).toLocaleString()}
            sub={`P25–P75: ${Math.round(rating.data.p25Days)} – ${Math.round(rating.data.p75Days)}`}
          />
        </div>
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No data for {selected}</div>
            <div className="empty-sub">No checkride milestones recorded yet.</div>
          </div>
        </div>
      )}
    </div>
  );
}
