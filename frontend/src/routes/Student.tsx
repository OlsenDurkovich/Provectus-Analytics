import { useNavigate, useParams } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { BigKpi, DeltaText, MiniKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useClients, useRatingCohorts, useStudent } from '../data/queries';
import type {
  RatingCohortMember,
  StudentDetail,
  StudentPerRating,
  StudentTimelinePoint,
} from '../data/types';

function fmtCost(v: number | null | undefined): string {
  if (v == null) return '—';
  return `$${Math.round(v).toLocaleString()}`;
}

function fmtMonthYear(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('en', { month: 'short', year: 'numeric' });
}

function spanMs(start: string, end: string | null): { startMs: number; endMs: number } {
  const startMs = new Date(start).getTime();
  const endMs = end ? new Date(end).getTime() : startMs + 86400000;
  return { startMs, endMs: Math.max(endMs, startMs + 86400000) };
}

export default function Student() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const clientsQ = useClients('all');
  const detailQ = useStudent(id);

  const studentOpts = (clientsQ.data ?? [])
    .filter((c, idx, arr) => arr.findIndex((x) => x.id === c.id) === idx)
    .map((s) => ({ value: s.id, label: s.name }));

  const detail = detailQ.data;

  return (
    <div className="student-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">Drill-down</div>
          <h1 className="page-title">Student</h1>
          <div className="page-sub">
            Per-student journey across all ratings, with cohort-comparison deltas.
          </div>
        </div>
        <div className="page-head-tools">
          <Select<string>
            label="Student"
            value={id ?? ''}
            onChange={(v) => v && navigate(`/students/${v}`)}
            options={studentOpts}
            width={240}
          />
        </div>
      </div>

      {!id ? (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Pick a student</div>
            <div className="empty-sub">Use the selector above to drill into one student.</div>
          </div>
        </div>
      ) : detailQ.isLoading ? (
        <Skel h={240} />
      ) : detail ? (
        <StudentBody detail={detail} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Student not found</div>
            <div className="empty-sub">{id}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function StudentBody({ detail }: { detail: StudentDetail }) {
  const totals = detail.perRating.reduce(
    (acc, r) => ({
      hours: acc.hours + (r.hours ?? 0),
      cost: acc.cost + (r.cost ?? 0),
      days: acc.days + (r.days ?? 0),
    }),
    { hours: 0, cost: 0, days: 0 },
  );
  const codes = detail.timeline.map((t) => t.rating).join(', ') || '—';
  const cohortCodes = detail.perRating.map((r) => r.rating);
  const cohorts = useRatingCohorts(cohortCodes);

  return (
    <>
      <h2 className="visually-hidden">{detail.name}</h2>
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
        <RatingBlock
          key={r.rating}
          r={r}
          studentId={detail.id}
          studentName={detail.name}
          cohortQuery={cohorts.get(r.rating)}
        />
      ))}
    </>
  );
}

function JourneyTimeline({ timeline }: { timeline: StudentTimelinePoint[] }) {
  const spans = timeline.map((t) => spanMs(t.start, t.end));
  const startMs = Math.min(...spans.map((s) => s.startMs));
  const endMs = Math.max(...spans.map((s) => s.endMs));
  const total = Math.max(1, endMs - startMs);

  const pct = (ms: number) => ((ms - startMs) / total) * 100;

  return (
    <>
      <div className="section-head">
        <h2 className="section-title">Training journey</h2>
        <div className="muted tiny">Each row is a rating. Dots = milestones.</div>
      </div>
      <div className="card">
        <div className="card-body" style={{ padding: '18px 18px 14px' }}>
          <div className="timeline">
            {timeline.map((t, i) => {
              const { startMs: s, endMs: e } = spans[i];
              const left = pct(s);
              const width = Math.max(0.6, pct(e) - pct(s));
              return (
                <div className="timeline-row" key={t.rating}>
                  <div className="timeline-label">
                    <div className="timeline-label-code">{t.rating}</div>
                  </div>
                  <div className="timeline-track">
                    <div
                      className="timeline-bar"
                      style={{
                        left: `${left}%`,
                        width: `${width}%`,
                        background: 'var(--accent)',
                      }}
                    >
                      {t.milestones.map((m) => {
                        const ms = new Date(m.date).getTime();
                        const dotLeft = ((ms - s) / Math.max(1, e - s)) * 100;
                        return (
                          <span
                            key={`${m.name}-${m.date}`}
                            className="timeline-dot"
                            style={{ left: `${dotLeft}%` }}
                            title={`${m.name} · ${m.date}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="timeline-axis">
            <span>{fmtMonthYear(new Date(startMs).toISOString())}</span>
            <span>{fmtMonthYear(new Date(endMs).toISOString())}</span>
          </div>
        </div>
      </div>
    </>
  );
}

function RatingBlock({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const hours = r.hours ?? 0;
  const cost = r.cost ?? 0;
  const days = r.days ?? 0;
  const cohortHours = r.medianHrs ?? 0;
  const cohortCost = r.medianCost ?? 0;
  const cohortDays = r.medianDays ?? 0;

  return (
    <div className="rating-block">
      <div className="rating-block-head">
        <div className="rating-block-title">
          <span className="rating-chip">{r.rating}</span>
          <span className="rating-block-name">{r.name}</span>
        </div>
        <div className={`rating-block-n${r.lowSample ? ' low' : ''}`}>
          {r.lowSample ? `n=${r.n} · low sample` : `n=${r.n}`}
        </div>
      </div>
      <div className="minikpi-grid">
        <MiniKpi
          label="Hours"
          value={hours.toFixed(1)}
          deltaNode={
            <DeltaText
              value={cohortHours ? +(hours - cohortHours).toFixed(1) : 0}
              betterWhenLower
              fmt={(v) => v.toFixed(1)}
            />
          }
          sub={cohortHours ? `Cohort median: ${cohortHours.toFixed(1)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Cost"
          value={fmtCost(cost)}
          deltaNode={
            <DeltaText
              value={cohortCost ? cost - cohortCost : 0}
              betterWhenLower
              fmt={(v) => fmtCost(v)}
            />
          }
          sub={cohortCost ? `Cohort median: ${fmtCost(cohortCost)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Days"
          value={days.toLocaleString()}
          deltaNode={
            <DeltaText
              value={cohortDays ? days - cohortDays : 0}
              betterWhenLower
              fmt={(v) => Math.round(v).toLocaleString()}
            />
          }
          sub={cohortDays ? `Cohort median: ${Math.round(cohortDays)}` : 'No cohort data'}
        />
        <MiniKpi label="Alumni (n)" value={String(r.n)} />
      </div>
      <RatingBlockStrips
        r={r}
        studentId={studentId}
        studentName={studentName}
        cohortQuery={cohortQuery}
      />
    </div>
  );
}

function RatingBlockStrips({
  r,
  studentId,
  studentName,
  cohortQuery,
}: {
  r: StudentPerRating;
  studentId: string;
  studentName: string;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const rawCohort = cohortQuery?.data ?? [];
  const inCohort = rawCohort.some((m) => m.studentId === studentId);
  const hasStudentData = r.hours != null || r.cost != null || r.days != null;

  // Inject the student as a synthetic point if they aren't in the cohort.
  const cohort: RatingCohortMember[] = inCohort || !hasStudentData
    ? rawCohort
    : [
        ...rawCohort,
        {
          studentId,
          name: studentName,
          hours: r.hours ?? 0,
          cost: r.cost ?? 0,
          days: r.days ?? 0,
        },
      ];

  const highlightInProgress = !inCohort && hasStudentData;

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    cohort.map((m) => ({ student: m.name, value: selector(m) }));

  const range = (selector: (m: RatingCohortMember) => number) => {
    if (cohort.length === 0) return { low: 0, high: 0 };
    const vals = cohort.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={r.medianHrs ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={r.medianCost ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={r.medianDays ?? 0}
          highlightName={studentName}
          highlightInProgress={highlightInProgress}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
