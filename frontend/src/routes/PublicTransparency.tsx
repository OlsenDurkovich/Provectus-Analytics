// Public, unauthenticated marketing page: "what does training cost at Provectus".
// Shows consent-filtered, anonymized per-rating medians + P25–P75 ranges.
import type { CSSProperties } from 'react';
import { usePublicTransparency } from '../data/queries';
import type { PublicRatingNorm } from '../data/types';

const fmtUSD = (n: number) => '$' + Math.round(n).toLocaleString('en-US');
const fmtHrs = (n: number) => n.toFixed(1);

const page: CSSProperties = {
  minHeight: '100vh',
  background: 'var(--bg)',
  color: 'var(--fg)',
  padding: '48px 20px',
  overflowY: 'auto',
};
const wrap: CSSProperties = { maxWidth: 880, margin: '0 auto' };
const card: CSSProperties = {
  background: 'var(--bg-elev)',
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
};
const badge: CSSProperties = {
  fontSize: 11,
  padding: '2px 8px',
  borderRadius: 999,
  border: '1px solid var(--border-strong)',
  color: 'var(--fg-dim)',
  whiteSpace: 'nowrap',
};
const notice: CSSProperties = {
  background: 'var(--accent-faint)',
  border: '1px solid var(--accent)',
  color: 'var(--fg)',
  borderRadius: 10,
  padding: '12px 16px',
  fontSize: 13,
  marginBottom: 24,
};

function Metric({ label, big, range }: { label: string; big: string; range?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
      <span style={{ fontSize: 13, color: 'var(--fg-muted)' }}>{label}</span>
      <span style={{ textAlign: 'right' }}>
        <span className="num" style={{ fontSize: 18, fontWeight: 600 }}>{big}</span>
        {range && (
          <span style={{ display: 'block', fontSize: 12, color: 'var(--fg-dim)' }}>
            typical range {range}
          </span>
        )}
      </span>
    </div>
  );
}

function RatingCard({ r }: { r: PublicRatingNorm }) {
  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: 16 }}>
          {r.label}{' '}
          <span style={{ color: 'var(--fg-dim)', fontWeight: 400 }}>({r.code})</span>
        </h3>
        {r.low_sample && (
          <span style={badge} title="Fewer than 10 responses — indicative only">
            low sample
          </span>
        )}
      </div>
      <div style={{ marginTop: 14, display: 'grid', gap: 12 }}>
        <Metric label="Typical cost" big={fmtUSD(r.median_cost)} range={`${fmtUSD(r.p25_cost)} – ${fmtUSD(r.p75_cost)}`} />
        <Metric label="Flight hours" big={fmtHrs(r.median_hours)} range={`${fmtHrs(r.p25_hours)} – ${fmtHrs(r.p75_hours)}`} />
        <Metric label="Calendar time" big={`${r.median_days} days`} />
      </div>
      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--fg-dim)' }}>
        Based on {r.n} alum{r.n === 1 ? '' : 'ni'} who opted in
      </div>
    </div>
  );
}

export default function PublicTransparency() {
  const q = usePublicTransparency();

  return (
    <div style={page}>
      <div style={wrap}>
        <header style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 8 }}>
          <img src="/Provectus.jpg" alt="Provectus Aviation" height={40} />
          <div>
            <h1 style={{ margin: 0, fontSize: 24 }}>What flight training costs at Provectus</h1>
            <p style={{ margin: '4px 0 0', color: 'var(--fg-muted)', fontSize: 14 }}>
              Real numbers from our alumni — median cost, hours, and time per rating.
            </p>
          </div>
        </header>

        {q.data?.data_mode === 'synthetic' && (
          <div style={notice}>
            <strong>Sample data.</strong> These figures are placeholders for layout
            and will be replaced with real alumni responses as they come in.
          </div>
        )}

        {q.isLoading && <p style={{ color: 'var(--fg-dim)' }}>Loading…</p>}
        {q.isError && <p style={{ color: 'var(--negative)' }}>Couldn’t load the figures right now.</p>}
        {q.data && q.data.ratings.length === 0 && (
          <p style={{ color: 'var(--fg-dim)' }}>
            No opted-in responses yet — check back soon.
          </p>
        )}

        {q.data && q.data.ratings.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginTop: 8 }}>
            {q.data.ratings.map((r) => (
              <RatingCard key={r.code} r={r} />
            ))}
          </div>
        )}

        <footer style={{ marginTop: 32, fontSize: 12, color: 'var(--fg-dim)', lineHeight: 1.6 }}>
          <p style={{ margin: 0 }}>
            Figures show the <strong>median</strong> (typical) value; the "typical range"
            is the middle 50% of alumni (25th–75th percentile). Only data from alumni who
            explicitly opted in is included, and no individual is identifiable. Ratings with
            fewer than 10 responses are marked “low sample.”
          </p>
        </footer>
      </div>
    </div>
  );
}
