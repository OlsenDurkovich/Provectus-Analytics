import { useState } from 'react';
import { useInsights } from '../data/queries';
import { Skel } from '../components/primitives';
import type {
  AtRiskRow,
  CadenceInsight,
  InstructorEfficiency,
  PredictionRow,
  RatingCode,
  RatingStrength,
} from '../data/types';

const RATING_META: Record<RatingCode, { name: string; color: string }> = {
  PPL: { name: 'Private Pilot', color: '#6E56F8' },
  IFR: { name: 'Instrument', color: '#3DD68C' },
  COM: { name: 'Commercial SE', color: '#22D3EE' },
  AMEL: { name: 'Multi-Engine', color: '#F59E0B' },
  CFI: { name: 'CFI', color: '#EC4899' },
  CFII: { name: 'CFII', color: '#A78BFA' },
  MEI: { name: 'MEI', color: '#F472B6' },
};

const THRESHOLDS: { v: number; label: string }[] = [
  { v: 0.1, label: '10%' },
  { v: 0.25, label: '25%' },
  { v: 0.5, label: '50%' },
];

function pct(v: number, digits = 0): string {
  const s = (v * 100).toFixed(digits);
  return `${v > 0 ? '+' : ''}${s}%`;
}

function chip(code: RatingCode) {
  const m = RATING_META[code];
  return <span className="rating-chip" style={{ background: m.color }}>{code}</span>;
}

// vs-rest %: lower is better, so negative is good (green), positive is bad (red).
// `comparable === false` means the instructor taught everyone in the rating, so
// there's no "rest" to compare against.
function VsRest({ value, comparable = true }: { value: number; comparable?: boolean }) {
  if (!comparable) return <span className="muted">—</span>;
  const color = value < -0.005 ? 'var(--positive)' : value > 0.005 ? 'var(--negative)' : 'var(--fg-dim)';
  return <span style={{ color, fontVariantNumeric: 'tabular-nums' }}>{pct(value)}</span>;
}

export default function Insights() {
  const [threshold, setThreshold] = useState(0.25);
  const q = useInsights(threshold);

  return (
    <div className="insights-tab">
      <div className="page-head">
        <div>
          <div className="eyebrow">Analytics</div>
          <h1 className="page-title">Insights</h1>
          <div className="page-sub">
            At-risk students, instructor strengths by rating, and overall efficiency — all vs cohort medians.
          </div>
        </div>
      </div>

      {q.isLoading ? (
        <Skel h={400} />
      ) : q.data ? (
        <>
          <AtRisk
            rows={q.data.atRisk}
            threshold={threshold}
            onThreshold={setThreshold}
          />
          <Predictions rows={q.data.predictions} />
          {q.data.cadence && <Cadence data={q.data.cadence} />}
          <Strengths strengths={q.data.strengths} />
          <Efficiency rows={q.data.efficiency} />
        </>
      ) : (
        <div className="card"><div className="empty"><div className="empty-title">No insights available</div></div></div>
      )}
    </div>
  );
}

function AtRisk({
  rows,
  threshold,
  onThreshold,
}: {
  rows: AtRiskRow[];
  threshold: number;
  onThreshold: (v: number) => void;
}) {
  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">At-risk students</div>
          <div className="card-sub">
            Running over the cohort median by the selected margin — may need extra help.
          </div>
        </div>
        <div className="seg">
          {THRESHOLDS.map((t) => (
            <button
              key={t.v}
              type="button"
              className={`seg-opt ${threshold === t.v ? 'active' : ''}`}
              onClick={() => onThreshold(t.v)}
            >
              ≥{t.label}
            </button>
          ))}
        </div>
      </div>
      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th style={{ width: '22%' }}>Student</th>
              <th style={{ width: '14%' }}>Rating</th>
              <th className="num">Hours</th>
              <th className="num">vs median</th>
              <th className="num">Cost</th>
              <th className="num">vs median</th>
              <th className="num">Over by</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty">
                    <div className="empty-title">No one over {Math.round(threshold * 100)}%</div>
                    <div className="empty-sub">Lower the threshold to widen the net.</div>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={`${r.studentId}-${r.rating}`}>
                  <td>{r.name}</td>
                  <td>{chip(r.rating)}<span className="muted tiny" style={{ marginLeft: 8 }}>{RATING_META[r.rating].name}</span></td>
                  <td className="num">{r.hours.toFixed(1)}</td>
                  <td className="num"><VsRest value={r.pctOverHours} /></td>
                  <td className="num">${Math.round(r.cost).toLocaleString()}</td>
                  <td className="num"><VsRest value={r.pctOverCost} /></td>
                  <td className="num">
                    <span className="status-pill status-active" style={{ background: 'var(--negative-faint, rgba(220,80,80,0.15))', color: 'var(--negative)' }}>
                      {pct(r.worstPct)}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const PRED_STATUS: Record<PredictionRow['status'], { label: string; color: string }> = {
  on_track: { label: 'On track', color: 'var(--positive)' },
  behind_pace: { label: 'Behind pace', color: 'var(--warn, #E0A030)' },
  over_median: { label: 'Over median', color: 'var(--negative)' },
  stalled: { label: 'Stalled', color: 'var(--fg-dim)' },
};

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en', { month: 'short', year: 'numeric' });
}

function Predictions({ rows }: { rows: PredictionRow[] }) {
  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Completion forecast · in-progress students</div>
          <div className="card-sub">
            Projected checkride-readiness from each student's recent flight pace vs the cohort median.
            Use it to time the checkride — or to spot who's stalled or running long.
          </div>
        </div>
      </div>
      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th style={{ width: '20%' }}>Student</th>
              <th>Rating</th>
              <th className="num">Hours</th>
              <th className="num">Pace/wk</th>
              <th className="num">Last flew</th>
              <th className="num">Projected</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={7}><div className="empty"><div className="empty-title">No students in progress</div></div></td></tr>
            ) : (
              rows.map((p) => {
                const st = PRED_STATUS[p.status];
                return (
                  <tr key={`${p.studentId}-${p.rating}`}>
                    <td>{p.name}</td>
                    <td>{chip(p.rating)}</td>
                    <td className="num">{p.currentHours.toFixed(1)} / {p.medianHours.toFixed(0)}</td>
                    <td className="num">{p.pacePerWeek.toFixed(1)}h</td>
                    <td className="num">{p.daysSinceLastFlight}d ago</td>
                    <td className="num">
                      {p.projectedDate
                        ? <span>{fmtDate(p.projectedDate)}{p.weeksRemaining != null ? <span className="muted tiny"> ({p.weeksRemaining}w)</span> : null}</span>
                        : <span className="muted">—</span>}
                    </td>
                    <td><span style={{ color: st.color }}>{st.label}</span></td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Cadence({ data }: { data: CadenceInsight }) {
  const maxDays = Math.max(...data.buckets.map((b) => b.avgDays), 1);
  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Training cadence vs outcomes · all students</div>
          <div className="card-sub">
            Every completed student ({data.n}) grouped by how often they flew. Flying more frequently
            finishes far sooner. Cost &amp; hours are shown vs each student's <em>own rating median</em>,
            so ratings are comparable (a CFI and a PPL aren't mixed by raw dollars).
          </div>
        </div>
      </div>
      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th>Training frequency</th>
              <th className="num">Students</th>
              <th className="num">Avg flights/wk</th>
              <th className="num">Days to checkride</th>
              <th style={{ width: '22%' }}>Time</th>
              <th className="num">Cost vs typical</th>
              <th className="num">Hours vs typical</th>
            </tr>
          </thead>
          <tbody>
            {data.buckets.map((b) => (
              <tr key={b.label}>
                <td>{b.label}</td>
                <td className="num">{b.n}</td>
                <td className="num">{b.avgCadence.toFixed(1)}</td>
                <td className="num">{Math.round(b.avgDays)}</td>
                <td>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${(b.avgDays / maxDays) * 100}%`, background: 'var(--accent)' }} />
                  </div>
                </td>
                <td className="num"><VsRest value={b.costVsMedianPct} /></td>
                <td className="num"><VsRest value={b.hoursVsMedianPct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Strengths({ strengths }: { strengths: RatingStrength[] }) {
  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Instructor strengths · by rating</div>
          <div className="card-sub">
            Ranked by avg hours-to-checkride (#1 = best). "vs rest" compares each instructor's
            students against <em>every other</em> instructor's students in that rating — not a
            cohort baseline they're part of — so a negative % means their students were faster
            than everyone else's.
          </div>
        </div>
      </div>
      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th style={{ width: '8%' }}>Rating</th>
              <th>Instructor</th>
              <th className="num">Students</th>
              <th className="num">Avg hours</th>
              <th className="num">vs rest</th>
              <th className="num">Avg cost</th>
              <th className="num">vs rest</th>
            </tr>
          </thead>
          <tbody>
            {strengths.flatMap((s) =>
              s.instructors.map((i, idx) => (
                <tr key={`${s.rating}-${i.instructor}`}>
                  {idx === 0 ? (
                    <td rowSpan={s.instructors.length} style={{ verticalAlign: 'top', paddingTop: 12 }}>
                      {chip(s.rating)}
                    </td>
                  ) : null}
                  <td>
                    {i.rank === 1 && <span title="Best in this rating" style={{ marginRight: 6 }}>★</span>}
                    {i.instructor}
                    {i.lowSample && <span className="muted tiny" style={{ marginLeft: 6 }}>(low n)</span>}
                  </td>
                  <td className="num">{i.n}</td>
                  <td className="num">{i.avgHours.toFixed(1)}</td>
                  <td className="num"><VsRest value={i.vsRestHoursPct} comparable={i.comparable} /></td>
                  <td className="num">${Math.round(i.avgCost).toLocaleString()}</td>
                  <td className="num"><VsRest value={i.vsRestCostPct} comparable={i.comparable} /></td>
                </tr>
              )),
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Efficiency({ rows }: { rows: InstructorEfficiency[] }) {
  return (
    <div className="card table-card">
      <div className="card-head">
        <div>
          <div className="card-title">Instructor efficiency ranking</div>
          <div className="card-sub">
            Each instructor's students vs every <em>other</em> instructor's students, averaged
            across the ratings they teach (leave-one-out, weighted by student count). Lower = more
            efficient.
          </div>
        </div>
      </div>
      <div className="table-wrap">
        <table className="dt">
          <thead>
            <tr>
              <th style={{ width: '8%' }}>Rank</th>
              <th>Instructor</th>
              <th className="num">Students</th>
              <th className="num">Ratings</th>
              <th className="num">Hours vs rest</th>
              <th className="num">Cost vs rest</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <tr key={e.instructor}>
                <td className="num">{e.rank}</td>
                <td>
                  {e.rank === 1 && <span style={{ marginRight: 6 }}>★</span>}
                  {e.instructor}
                  {e.lowSample && <span className="muted tiny" style={{ marginLeft: 6 }}>(low n)</span>}
                </td>
                <td className="num">{e.students}</td>
                <td className="num">{e.ratings}</td>
                <td className="num"><VsRest value={e.avgHoursVsRestPct} /></td>
                <td className="num"><VsRest value={e.avgCostVsRestPct} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
