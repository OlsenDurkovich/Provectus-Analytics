// Exec one-pager: a single, print-friendly program summary for leadership.
// Pulls live data (all-time), and "Print" → browser Print → save as PDF.
import { useKpis, useRatingBars, useInsights } from '../data/queries';
import { Skel } from '../components/primitives';
import { useMeta } from '../data/queries';
import type { MetricKey, RatingCode, RatingBarPoint } from '../data/types';

const RATING_ORDER: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];
const RATING_NAME: Record<RatingCode, string> = {
  PPL: 'Private Pilot', IFR: 'Instrument', COM: 'Commercial SE', AMEL: 'Multi-Engine',
  CFI: 'CFI', CFII: 'CFII', MEI: 'MEI',
};

function byCode(rows: RatingBarPoint[] | undefined): Map<RatingCode, RatingBarPoint> {
  const m = new Map<RatingCode, RatingBarPoint>();
  (rows ?? []).forEach((r) => m.set(r.code, r));
  return m;
}

export default function Summary() {
  const kpis = useKpis('all');
  const hours = useRatingBars('hours' as MetricKey, 'all');
  const cost = useRatingBars('cost' as MetricKey, 'all');
  const days = useRatingBars('days' as MetricKey, 'all');
  const insights = useInsights(0.25);
  const meta = useMeta();

  const loading = kpis.isLoading || hours.isLoading || cost.isLoading || days.isLoading || insights.isLoading;
  const hMap = byCode(hours.data);
  const cMap = byCode(cost.data);
  const dMap = byCode(days.data);
  const ratings = RATING_ORDER.filter((r) => hMap.has(r) || cMap.has(r));

  const synthetic = meta.data?.mode !== 'real';
  const today = new Date().toLocaleDateString('en', { year: 'numeric', month: 'long', day: 'numeric' });

  // Insight highlights
  const ins = insights.data;
  const bestInstructor = ins?.efficiency?.find((e) => !e.lowSample) ?? ins?.efficiency?.[0];
  const cad = ins?.cadence;
  const slow = cad?.buckets?.[0];
  const fast = cad?.buckets && cad.buckets.length > 1 ? cad.buckets[cad.buckets.length - 1] : undefined;
  const atRiskN = ins?.atRisk?.length ?? 0;
  const inProgressN = ins?.predictions?.length ?? 0;

  return (
    <div className="summary-page">
      <div className="summary-head">
        <div>
          <div className="eyebrow">Program summary</div>
          <h1 className="page-title">Provectus Flight Training — at a glance</h1>
          <div className="page-sub">All-time cohort · generated {today}</div>
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
          <div className="summary-kpis">
            {(kpis.data ?? []).map((k) => (
              <div className="summary-kpi" key={k.key}>
                <div className="summary-kpi-value">{k.value}</div>
                <div className="summary-kpi-label">{k.label}</div>
              </div>
            ))}
          </div>

          <div className="summary-section-title">Cost &amp; time per rating <span className="muted tiny">(cohort median)</span></div>
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

          <div className="summary-section-title">Highlights</div>
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
                  PPL students flying {fast.label.replace('×+/week', '×+/wk')} finish far sooner than {slow.label.replace('×/week', '×/wk')} — and ~${Math.round((slow.avgCost - fast.avgCost)).toLocaleString()} cheaper.
                </div>
              </div>
            )}
            <div className="summary-highlight">
              <div className="summary-highlight-big">{inProgressN} in progress · {atRiskN} at-risk</div>
              <div className="summary-highlight-cap">
                Students currently training, with {atRiskN} running ≥25% over the cohort median (may need extra help).
              </div>
            </div>
          </div>

          <div className="summary-foot muted tiny">
            Provectus Analytics · cohort medians shown · full detail in the dashboards.
          </div>
        </>
      )}
    </div>
  );
}
