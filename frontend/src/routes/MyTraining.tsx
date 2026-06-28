// Student-facing page. A `student`-role account sees ONLY this: their own
// training, served by /api/me/training (which is locked to their linked
// record). No cohort comparison, no other students — by design.
import { BigKpi, MiniKpi } from '../components/helpers';
import { Skel } from '../components/primitives';
import { useMyTraining } from '../data/queries';
import { JourneyTimeline } from './Student';
import type { StudentDetail, StudentPerRating } from '../data/types';

function fmtCost(v: number | null | undefined): string {
  if (v == null) return '—';
  return `$${Math.round(v).toLocaleString()}`;
}

export default function MyTraining() {
  const q = useMyTraining();

  return (
    <div className="student-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">My account</div>
          <h1 className="page-title">My training</h1>
          <div className="page-sub">
            Your flight hours, cost, and rating progress to date.
          </div>
        </div>
      </div>

      {q.isLoading ? (
        <Skel h={240} />
      ) : q.data ? (
        <Body detail={q.data} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No training record found</div>
            <div className="empty-sub">
              Your account isn’t linked to a training record yet. Ask an admin to link it.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Body({ detail }: { detail: StudentDetail }) {
  const totals = detail.perRating.reduce(
    (acc, r) => ({
      hours: acc.hours + (r.hours ?? 0),
      cost: acc.cost + (r.cost ?? 0),
      days: acc.days + (r.days ?? 0),
    }),
    { hours: 0, cost: 0, days: 0 },
  );
  const codes = detail.timeline.map((t) => t.rating).join(', ') || '—';

  return (
    <>
      <div className="kpi-grid">
        <BigKpi label="Ratings completed" value={String(detail.timeline.length)} sub={codes} />
        <BigKpi label="Total flight hours" value={totals.hours.toFixed(1)} sub="Sum across ratings" />
        <BigKpi label="Total cost" value={fmtCost(totals.cost)} sub="Sum across ratings" />
        <BigKpi
          label="Training days"
          value={totals.days.toLocaleString()}
          sub="Sum of per-rating durations"
        />
      </div>

      {detail.timeline.length > 0 && <JourneyTimeline timeline={detail.timeline} />}

      {detail.perRating.map((r) => (
        <RatingBlock key={r.rating} r={r} />
      ))}
    </>
  );
}

function RatingBlock({ r }: { r: StudentPerRating }) {
  const hours = r.hours ?? 0;
  const cost = r.cost ?? 0;
  const days = r.days ?? 0;

  return (
    <div className="rating-block">
      <div className="rating-block-head">
        <div className="rating-block-title">
          <span className="rating-chip">{r.rating}</span>
          <span className="rating-block-name">{r.name}</span>
        </div>
      </div>
      <div className="minikpi-grid">
        <MiniKpi label="Hours" value={hours.toFixed(1)} sub="Your flight hours" />
        <MiniKpi label="Cost" value={fmtCost(cost)} sub="Your billed total" />
        <MiniKpi label="Days" value={days.toLocaleString()} sub="Enrolled duration" />
      </div>
    </div>
  );
}
