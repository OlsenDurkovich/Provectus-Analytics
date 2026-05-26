import { useNavigate, useParams } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { BigKpi, DeltaText, MiniKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useInstructor, useInstructors, useRatingCohorts } from '../data/queries';
import type {
  InstructorDetail,
  InstructorPerRating,
  RatingCohortMember,
} from '../data/types';

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

function median(vals: number[]): number {
  if (vals.length === 0) return 0;
  const sorted = [...vals].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

export default function Instructor() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const listQ = useInstructors();
  const detailQ = useInstructor(id);

  const opts = (listQ.data ?? []).map((i) => ({ value: i.id, label: i.name }));

  return (
    <div className="instructor-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">People</div>
          <h1 className="page-title">Instructor</h1>
          <div className="page-sub">Efficiency relative to cohort medians, per rating.</div>
        </div>
        <div className="page-head-tools">
          <Select<string>
            label="Instructor"
            value={id ?? ''}
            onChange={(v) => v && navigate(`/instructors/${encodeURIComponent(v)}`)}
            options={opts}
            width={220}
          />
        </div>
      </div>

      {!id ? (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Pick an instructor</div>
            <div className="empty-sub">Use the selector above to drill in.</div>
          </div>
        </div>
      ) : detailQ.isLoading ? (
        <Skel h={240} />
      ) : detailQ.data ? (
        <InstructorBody detail={detailQ.data} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Instructor not found</div>
            <div className="empty-sub">{id}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstructorBody({ detail }: { detail: InstructorDetail }) {
  const totalHours = detail.students.reduce((s, c) => s + c.hoursToDate, 0);
  const studentsAtCheckride = detail.students.filter((s) => s.status === 'Completed').length;
  const cohortCodes = detail.perRating.map((p) => p.rating);
  const cohorts = useRatingCohorts(cohortCodes);

  return (
    <>
      <div className="kpi-grid kpi-grid-2">
        <BigKpi
          label="Ratings taught"
          value={String(detail.perRating.length)}
          sub={detail.perRating.map((p) => p.rating).join(', ') || '—'}
        />
        <BigKpi
          label="Students at checkride"
          value={String(studentsAtCheckride)}
          sub={`Total hours flown: ${totalHours.toFixed(1)}`}
        />
      </div>

      <div className="section-head">
        <h2 className="section-title">Per rating vs cohort</h2>
      </div>
      {detail.perRating.length === 0 && (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No completed ratings yet</div>
            <div className="empty-sub">
              Students under this instructor haven't reached checkride.
            </div>
          </div>
        </div>
      )}
      {detail.perRating.map((r) => (
        <InstructorRatingBlock
          key={r.rating}
          r={r}
          cohortQuery={cohorts.get(r.rating)}
        />
      ))}

      <div className="section-head">
        <h2 className="section-title">Student roster</h2>
      </div>
      <div className="card table-card">
        <div className="table-wrap" style={{ maxHeight: 480 }}>
          <table className="dt">
            <thead>
              <tr>
                <th>Student</th>
                <th>Rating</th>
                <th className="num">Hours</th>
                <th className="num">Days enrolled</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.students.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">
                      <div className="empty-title">No students assigned</div>
                    </div>
                  </td>
                </tr>
              )}
              {detail.students.map((row) => (
                <tr key={`${row.id}-${row.rating}`}>
                  <td>{row.name}</td>
                  <td>
                    <span className="rating-chip">{row.rating}</span>
                  </td>
                  <td className="num">{row.hoursToDate.toFixed(1)}</td>
                  <td className="num">{row.daysEnrolled}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function InstructorRatingBlock({
  r,
  cohortQuery,
}: {
  r: InstructorPerRating;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
}) {
  const cohort = cohortQuery?.data ?? [];
  const cohortMedHrs = median(cohort.map((m) => m.hours));
  const cohortMedCost = median(cohort.map((m) => m.cost));
  const cohortMedDays = median(cohort.map((m) => m.days));

  const highlightNames = cohort
    .filter((m) => r.studentIds.includes(m.studentId))
    .map((m) => m.name);

  return (
    <div className="rating-block">
      <div className="rating-block-head">
        <div className="rating-block-title">
          <span className="rating-chip">{r.rating}</span>
          <span className="rating-block-name">
            {r.n} student{r.n === 1 ? '' : 's'}
          </span>
        </div>
        <div className="rating-block-n">n={r.n}</div>
      </div>

      <div className="minikpi-grid">
        <MiniKpi
          label="Avg hours"
          value={r.avgHrs.toFixed(1)}
          deltaNode={
            <DeltaText
              value={cohortMedHrs ? +(r.avgHrs - cohortMedHrs).toFixed(1) : 0}
              betterWhenLower
              fmt={(v) => v.toFixed(1)}
            />
          }
          sub={cohortMedHrs ? `Cohort median: ${cohortMedHrs.toFixed(1)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Avg cost"
          value={fmtCost(r.avgCost)}
          deltaNode={
            <DeltaText
              value={cohortMedCost ? r.avgCost - cohortMedCost : 0}
              betterWhenLower
              fmt={(v) => fmtCost(v)}
            />
          }
          sub={cohortMedCost ? `Cohort median: ${fmtCost(cohortMedCost)}` : 'No cohort data'}
        />
        <MiniKpi
          label="Avg days"
          value={Math.round(r.avgDays).toLocaleString()}
          deltaNode={
            <DeltaText
              value={cohortMedDays ? r.avgDays - cohortMedDays : 0}
              betterWhenLower
              fmt={(v) => Math.round(v).toLocaleString()}
            />
          }
          sub={cohortMedDays ? `Cohort median: ${Math.round(cohortMedDays)}` : 'No cohort data'}
        />
        <MiniKpi label="Students (n)" value={String(r.n)} />
      </div>

      <InstructorStrips
        r={r}
        cohortQuery={cohortQuery}
        highlightNames={highlightNames}
      />
    </div>
  );
}

function InstructorStrips({
  r,
  cohortQuery,
  highlightNames,
}: {
  r: InstructorPerRating;
  cohortQuery: UseQueryResult<RatingCohortMember[]> | undefined;
  highlightNames: string[];
}) {
  if (cohortQuery?.isLoading) {
    return (
      <div className="rating-block-strips">
        <div className="strip-cell">
          <Skel h={60} />
        </div>
        <div className="strip-cell">
          <Skel h={60} />
        </div>
        <div className="strip-cell">
          <Skel h={60} />
        </div>
      </div>
    );
  }

  if (cohortQuery?.isError || !cohortQuery?.data || cohortQuery.data.length === 0) {
    return null;
  }

  const cohort = cohortQuery.data;

  const stripPoints = (selector: (m: RatingCohortMember) => number) =>
    cohort.map((m) => ({ student: m.name, value: selector(m) }));

  // Derive P25/P75 band client-side from cohort points (consistent with Student Detail).
  const range = (selector: (m: RatingCohortMember) => number) => {
    if (cohort.length === 0) return { low: 0, high: 0 };
    const vals = cohort.map(selector).sort((a, b) => a - b);
    const q = (p: number) => vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
    return { low: q(0.25), high: q(0.75) };
  };

  const medianHrs = median(cohort.map((m) => m.hours));
  const medianCost = median(cohort.map((m) => m.cost));
  const medianDays = median(cohort.map((m) => m.days));
  void r; // r is unused here but kept in the signature for future per-rating tweaks

  return (
    <div className="rating-block-strips">
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.hours)}
          band={range((m) => m.hours)}
          median={medianHrs}
          highlightNames={highlightNames}
          yLabel="Hours"
          fmt={(v) => v.toFixed(1)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.cost)}
          band={range((m) => m.cost)}
          median={medianCost}
          highlightNames={highlightNames}
          yLabel="Cost"
          fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
        />
      </div>
      <div className="strip-cell">
        <ScatterStrip
          size="mini"
          points={stripPoints((m) => m.days)}
          band={range((m) => m.days)}
          median={medianDays}
          highlightNames={highlightNames}
          yLabel="Days"
          fmt={(v) => Math.round(v).toLocaleString()}
        />
      </div>
    </div>
  );
}
