import { useState } from 'react';
import { RatingSummary } from '../components/RatingSummary';
import { KpiGrid } from '../components/KpiGrid';
import { RatingBars } from '../components/charts/RatingBars';
import { RatingsList } from '../components/charts/RatingsList';
import { Skel } from '../components/primitives';
import {
  useClients,
  useKpis,
  useRatingBars,
  useRatingsCompleted,
} from '../data/queries';
import type { MetricKey, RangeKey, RatingCode } from '../data/types';

const RANGE_LABEL: Record<RangeKey, string> = {
  '30d': 'last 30 days',
  '90d': 'last 90 days',
  '6mo': 'last 6 months',
  '12mo': 'last 12 months',
  ytd: 'year to date',
  all: 'all time',
};

const METRICS: MetricKey[] = ['hours', 'cost', 'days'];

type Props = { range: RangeKey };

export default function Overview({ range }: Props) {
  const [metric, setMetric] = useState<MetricKey>('hours');
  const [focusedKpi, setFocusedKpi] = useState<string | null>(null);
  const [focusedRating, setFocusedRating] = useState<RatingCode | null>(null);

  const kpis = useKpis(range);
  const bars = useRatingBars(metric, range);
  const completed = useRatingsCompleted(range);
  const clients = useClients(range, focusedRating ?? undefined);

  return (
    <div className="overview">
      <div className="page-head">
        <div className="eyebrow">Cohort overview</div>
        <h1>All ratings</h1>
        <div className="page-sub">
          Median + P25–P75 to checkride · {RANGE_LABEL[range]} · all ratings
        </div>
      </div>

      {kpis.isLoading ? (
        <Skel h={120} />
      ) : kpis.data ? (
        <KpiGrid kpis={kpis.data} focusedKey={focusedKpi} onFocus={setFocusedKpi} />
      ) : null}

      <div className="card">
        <div className="card-head">
          <div>
            <div className="card-title">Median {metric} to checkride · by rating</div>
            <div className="card-sub">Click a bar to filter clients</div>
          </div>
          <div className="seg metric-switcher">
            {METRICS.map((m) => (
              <button
                key={m}
                type="button"
                className={`seg-opt ${metric === m ? 'active' : ''}`}
                onClick={() => setMetric(m)}
              >
                {m[0].toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>
        {bars.isLoading ? (
          <Skel h={280} />
        ) : bars.data ? (
          <RatingBars
            data={bars.data}
            metric={metric}
            focusedCode={focusedRating}
            onFocus={setFocusedRating}
          />
        ) : null}
      </div>

      <div className="card">
        <div className="card-title">Ratings completed</div>
        {completed.isLoading ? (
          <Skel h={180} />
        ) : completed.data ? (
          <RatingsList data={completed.data} />
        ) : null}
      </div>

      {clients.isLoading ? (
        <Skel h={300} />
      ) : clients.data ? (
        <RatingSummary
          rows={clients.data}
          filterRating={focusedRating}
          onClearFilter={() => setFocusedRating(null)}
        />
      ) : null}
    </div>
  );
}
