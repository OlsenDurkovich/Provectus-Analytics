// Exec one-pager: a single, print-friendly program summary for leadership.
// Half "overview" (all-time cohort) + half "right now" (live operational state).
// "Print" → browser Print → save as PDF.
import { useTrends, useRatingBars, useInsights, useMeta } from '../data/queries';
import { Skel } from '../components/primitives';
import type { MetricKey, RatingCode, RatingBarPoint, PredictionRow, TrendSeries } from '../data/types';

const RATING_ORDER: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];
const RATING_NAME: Record<RatingCode, string> = {
  PPL: 'Private Pilot', IFR: 'Instrument', COM: 'Commercial SE', AMEL: 'Multi-Engine',
  CFI: 'CFI', CFII: 'CFII', MEI: 'MEI',
};
const PRED_META: Record<PredictionRow['status'], { label: string; color: string }> = {
  on_track: { label: 'On track', color: 'var(--positive)' },
  behind_pace: { label: 'Behind pace', color: 'var(--warn, #E0A030)' },
  over_median: { label: 'Over hours', color: 'var(--negative)' },
  stalled: { label: 'Stalled', color: 'var(--fg-dim)' },
};

function byCode(rows: RatingBarPoint[] | undefined): Map<RatingCode, RatingBarPoint> {
  const m = new Map<RatingCode, RatingBarPoint>();
  (rows ?? []).forEach((r) => m.set(r.code, r));
  return m;
}
function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString('en', { month: 'short', year: 'numeric' });
}

const INSTR_HOURS_THRESHOLD = 0.10;   // instructor avg this far over peers → develop

function fmtTrend(v: number, unit: TrendSeries['unit']): string {
  return unit === 'hours' ? Math.round(v).toLocaleString() : String(Math.round(v));
}
// Trend delta: for these metrics more is better, so positive change is good (green).
function TrendDelta({ pct }: { pct: number }) {
  const color = pct > 0.005 ? 'var(--positive)' : pct < -0.005 ? 'var(--negative)' : 'var(--fg-dim)';
  const arrow = pct > 0.005 ? '▲' : pct < -0.005 ? '▼' : '·';
  return <span style={{ color, fontVariantNumeric: 'tabular-nums' }}>{arrow} {pct > 0 ? '+' : ''}{Math.round(pct * 100)}%</span>;
}

export default function Summary() {
  const trends = useTrends();
  const hours = useRatingBars('hours' as MetricKey, 'all');
  const cost = useRatingBars('cost' as MetricKey, 'all');
  const days = useRatingBars('days' as MetricKey, 'all');
  const insights = useInsights(0.25);
  const meta = useMeta();

  const loading = trends.isLoading || hours.isLoading || cost.isLoading || days.isLoading || insights.isLoading;
  const hMap = byCode(hours.data);
  const cMap = byCode(cost.data);
  const dMap = byCode(days.data);
  const ratings = RATING_ORDER.filter((r) => hMap.has(r) || cMap.has(r));

  const synthetic = meta.data?.mode !== 'real';
  const today = new Date().toLocaleDateString('en', { year: 'numeric', month: 'long', day: 'numeric' });

  const ins = insights.data;
  const preds = ins?.predictions ?? [];
  const atRisk = ins?.atRisk ?? [];

  // Pipeline snapshot
  const counts = { on_track: 0, behind_pace: 0, over_median: 0, stalled: 0 } as Record<PredictionRow['status'], number>;
  preds.forEach((p) => { counts[p.status] += 1; });

  // Needs attention: behind-pace / over-hours / stalled + at-risk (deduped by name)
  const attn: { name: string; rating: RatingCode; reason: string; color: string }[] = [];
  const seen = new Set<string>();
  preds.filter((p) => p.status !== 'on_track').forEach((p) => {
    seen.add(p.name);
    const reason =
      p.status === 'behind_pace' ? `Behind pace — proj. ${fmtDate(p.projectedDate)} (${p.weeksRemaining}w)`
        : p.status === 'over_median' ? `Over typical hours — ${p.currentHours.toFixed(0)}h vs ${p.medianHours.toFixed(0)}`
          : `Stalled — last flew ${p.daysSinceLastFlight}d ago`;
    attn.push({ name: p.name, rating: p.rating, reason, color: PRED_META[p.status].color });
  });
  atRisk.forEach((r) => {
    if (seen.has(r.name)) return;
    attn.push({ name: r.name, rating: r.rating, reason: `${Math.round(r.worstPct * 100)}% over cohort median`, color: 'var(--negative)' });
  });

  // Upcoming checkrides: on-track, soonest first
  const upcoming = preds
    .filter((p) => p.status === 'on_track' && p.projectedDate)
    .sort((a, b) => (a.weeksRemaining ?? 1e9) - (b.weeksRemaining ?? 1e9))
    .slice(0, 5);

  // Instructors whose students run materially over their peers in a rating →
  // may need development on that rating. (Hours only — owner doesn't track billing.)
  const instructorAttention = (ins?.strengths ?? [])
    .flatMap((s) => s.instructors)
    .filter((i) => !i.lowSample && i.vsRestHoursPct >= INSTR_HOURS_THRESHOLD)
    .sort((a, b) => b.vsRestHoursPct - a.vsRestHoursPct);

  const bestInstructor = ins?.efficiency?.find((e) => !e.lowSample) ?? ins?.efficiency?.[0];
  const cad = ins?.cadence;
  const slow = cad?.buckets?.[0];
  const fast = cad?.buckets && cad.buckets.length > 1 ? cad.buckets[cad.buckets.length - 1] : undefined;

  return (
    <div className="summary-page">
      <div className="summary-head">
        <div>
          <div className="eyebrow">Program summary</div>
          <h1 className="page-title">Provectus Flight Training — at a glance</h1>
          <div className="page-sub">Generated {today}</div>
        </div>
        <button className="btn btn-primary no-print" type="button" onClick={() => window.print()}>
          Print / Save PDF
        </button>
      </div>

      {synthetic && (
        <div className="summary-banner">
          <strong>Sample data.</strong> Figures are synthetic placeholders shaped like real FSP data; they’ll be replaced as real alumni + flight data load.
        </div>
      )}

      {loading ? (
        <Skel h={500} />
      ) : (
        <>
          {/* ── MOMENTUM (totals + period-over-period) ──────────────────── */}
          <div className="summary-section-title">
            Momentum <span className="muted tiny">· total &amp; period-over-period</span>
            <span className="summary-active-pill">{trends.data?.activeNow ?? 0} active now <span className="muted tiny">(90d)</span></span>
          </div>
          {(trends.data?.series ?? []).map((s) => (
            <div key={s.metric}>
              <div className="summary-trend-label">{s.label}</div>
              <div className="summary-trend-row">
                <div className="summary-kpi">
                  <div className="summary-kpi-value">{fmtTrend(s.allTime, s.unit)}</div>
                  <div className="summary-kpi-label">All time</div>
                </div>
                {s.windows.map((w) => (
                  <div className="summary-kpi" key={w.label}>
                    <div className="summary-kpi-value">{fmtTrend(w.value, s.unit)}</div>
                    <div className="summary-kpi-label">Last {w.label}</div>
                    <div className="summary-kpi-breakdown">
                      <TrendDelta pct={w.pct} /> <span className="muted tiny">vs prior {w.label}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* ── RIGHT NOW (current operational state) ───────────────────── */}
          <div className="summary-section-title">Right now <span className="muted tiny">· current students</span></div>
          <div className="summary-pipeline">
            <div className="summary-pipe-total">{preds.length}<span>in training</span></div>
            {(['on_track', 'behind_pace', 'over_median', 'stalled'] as PredictionRow['status'][]).map((s) => (
              <div className="summary-pipe-stat" key={s}>
                <div className="summary-pipe-n" style={{ color: PRED_META[s].color }}>{counts[s]}</div>
                <div className="summary-pipe-label">{PRED_META[s].label}</div>
              </div>
            ))}
          </div>

          <div className="summary-now-grid">
            <div className="summary-list-card">
              <div className="summary-list-title">Needs attention</div>
              {attn.length === 0 ? (
                <div className="muted tiny">Everyone's on track.</div>
              ) : attn.slice(0, 6).map((a) => (
                <div className="summary-list-row" key={`${a.name}-${a.reason}`}>
                  <div>
                    <span className="summary-dot" style={{ background: a.color }} />
                    <strong>{a.name}</strong> <span className="muted tiny">{a.rating}</span>
                  </div>
                  <div className="summary-list-sub">{a.reason}</div>
                </div>
              ))}
            </div>
            <div className="summary-list-card">
              <div className="summary-list-title">Upcoming checkrides <span className="muted tiny">· schedule these</span></div>
              {upcoming.length === 0 ? (
                <div className="muted tiny">None projected soon.</div>
              ) : upcoming.map((p) => (
                <div className="summary-list-row" key={p.studentId}>
                  <div><strong>{p.name}</strong> <span className="muted tiny">{p.rating}</span></div>
                  <div className="summary-list-sub">~{fmtDate(p.projectedDate)} · {p.weeksRemaining}w · {p.currentHours.toFixed(0)}/{p.medianHours.toFixed(0)}h</div>
                </div>
              ))}
            </div>
            <div className="summary-list-card">
              <div className="summary-list-title">Instructors to develop <span className="muted tiny">· hours vs peers</span></div>
              {instructorAttention.length === 0 ? (
                <div className="muted tiny">All instructors within range of their peers.</div>
              ) : instructorAttention.slice(0, 6).map((i) => (
                <div className="summary-list-row" key={`${i.instructor}-${i.rating}`}>
                  <div>
                    <span className="summary-dot" style={{ background: 'var(--warn, #E0A030)' }} />
                    <strong>{i.instructor}</strong> <span className="muted tiny">{i.rating}</span>
                  </div>
                  <div className="summary-list-sub">
                    +{Math.round(i.vsRestHoursPct * 100)}% hours vs other instructors — may need {i.rating} development
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ── OVERVIEW (all-time cohort) ──────────────────────────────── */}
          <div className="summary-section-title">Cost &amp; time per rating <span className="muted tiny">· all-time cohort median</span></div>
          <table className="dt summary-table">
            <thead>
              <tr>
                <th>Rating</th>
                <th className="num">Alumni</th>
                <th className="num">Flight hours</th>
                <th className="num">Cost</th>
                <th className="num">Calendar days</th>
              </tr>
            </thead>
            <tbody>
              {ratings.map((r) => {
                const n = hMap.get(r)?.n ?? cMap.get(r)?.n ?? 0;
                return (
                  <tr key={r}>
                    <td><strong>{r}</strong> <span className="muted tiny">{RATING_NAME[r]}</span></td>
                    <td className="num">{n}</td>
                    <td className="num">{(hMap.get(r)?.median ?? 0).toFixed(1)}</td>
                    <td className="num">${Math.round(cMap.get(r)?.median ?? 0).toLocaleString()}</td>
                    <td className="num">{Math.round(dMap.get(r)?.median ?? 0).toLocaleString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="summary-highlights">
            {bestInstructor && (
              <div className="summary-highlight">
                <div className="summary-highlight-big">{bestInstructor.instructor}</div>
                <div className="summary-highlight-cap">
                  Most efficient instructor — students average {Math.abs(Math.round(bestInstructor.avgHoursVsRestPct * 100))}% {bestInstructor.avgHoursVsRestPct < 0 ? 'fewer' : 'more'} hours than the rest.
                </div>
              </div>
            )}
            {slow && fast && (
              <div className="summary-highlight">
                <div className="summary-highlight-big">{Math.round(fast.avgDays)} vs {Math.round(slow.avgDays)} days</div>
                <div className="summary-highlight-cap">
                  Students flying {fast.avgCadence.toFixed(0)}×/week reach checkride far sooner than those at ~{slow.avgCadence.toFixed(1)}×/week — and ~{Math.abs(Math.round(fast.costVsMedianPct * 100))}% under their rating's typical cost.
                </div>
              </div>
            )}
          </div>

          <div className="summary-foot muted tiny">
            Provectus Analytics · all-time cohort medians + live pipeline · full detail in the dashboards.
          </div>
        </>
      )}
    </div>
  );
}
