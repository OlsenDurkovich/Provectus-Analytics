import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BigKpi, DeltaText, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { ScatterStrip } from '../components/charts/ScatterStrip';
import { useRating, useRatingCohort } from '../data/queries';
import type { RangeKey, RatingCode, RatingCohortMember } from '../data/types';

const CODES: RatingCode[] = ['PPL', 'IFR', 'COM', 'AMEL', 'CFI', 'CFII', 'MEI'];

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

type Props = { range: RangeKey };

export default function RatingDetail({ range }: Props) {
  const { code } = useParams<{ code?: string }>();
  const navigate = useNavigate();
  const selected = (CODES.includes(code as RatingCode) ? code : 'PPL') as RatingCode;
  const [overlayId, setOverlayId] = useState<string | null>(null);

  const rating = useRating(selected, range);
  const cohort = useRatingCohort(selected);

  const cohortData = cohort.data ?? [];
  const overlayPt = overlayId
    ? (cohortData.find((m) => m.studentId === overlayId) ?? null)
    : null;

  const studentOpts = cohortData.map((m) => ({ value: m.studentId, label: m.name }));

  return (
    <div className="rating-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">Detail</div>
          <h1 className="page-title">Rating detail</h1>
          <div className="page-sub">
            Cohort distribution with P25–P75 band. Compare an individual to the band.
          </div>
        </div>
        <div className="page-head-tools">
          <Select<RatingCode>
            label="Rating"
            value={selected}
            onChange={(v) => {
              if (v) {
                setOverlayId(null);
                navigate(`/ratings/${v}`);
              }
            }}
            options={CODES.map((c) => ({ value: c, label: c }))}
            width={130}
          />
          <Select<string>
            label="Overlay student"
            value={overlayId}
            onChange={setOverlayId}
            options={studentOpts}
            width={220}
            allowClear
          />
        </div>
      </div>

      {rating.isLoading ? (
        <Skel h={200} />
      ) : rating.data ? (
        <>
          <div className="kpi-grid">
            <BigKpi
              label="Alumni (n)"
              value={String(rating.data.n)}
              sub={
                rating.data.lowSample
                  ? 'Low sample — interpret with care'
                  : 'Sufficient sample'
              }
            />
            <BigKpi
              label="Median hours"
              value={rating.data.medianHrs.toFixed(1)}
              overlay={
                overlayPt
                  ? { label: overlayPt.name, value: overlayPt.hours.toFixed(1) }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={+(overlayPt.hours - rating.data.medianHrs).toFixed(1)}
                    betterWhenLower
                    fmt={(v) => v.toFixed(1)}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${rating.data.p25Hrs.toFixed(1)} – ${rating.data.p75Hrs.toFixed(1)}`}
            />
            <BigKpi
              label="Median cost"
              value={fmtCost(rating.data.medianCost)}
              overlay={
                overlayPt
                  ? { label: overlayPt.name, value: fmtCost(overlayPt.cost) }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={Math.round(overlayPt.cost - rating.data.medianCost)}
                    betterWhenLower
                    fmt={(v) => `$${Math.round(v).toLocaleString()}`}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${fmtCost(rating.data.p25Cost)} – ${fmtCost(rating.data.p75Cost)}`}
            />
            <BigKpi
              label="Median days"
              value={Math.round(rating.data.medianDays).toLocaleString()}
              overlay={
                overlayPt
                  ? {
                      label: overlayPt.name,
                      value: overlayPt.days.toLocaleString(),
                    }
                  : undefined
              }
              deltaNode={
                overlayPt ? (
                  <DeltaText
                    value={overlayPt.days - Math.round(rating.data.medianDays)}
                    betterWhenLower
                    fmt={(v) => Math.round(Math.abs(v)).toLocaleString()}
                  />
                ) : undefined
              }
              sub={`P25–P75: ${Math.round(rating.data.p25Days)} – ${Math.round(rating.data.p75Days)}`}
            />
          </div>

          {!cohort.isLoading && cohortData.length > 0 && (
            <DistributionSection
              ratingName={rating.data.name}
              cohort={cohortData}
              band={{
                hrs: [rating.data.p25Hrs, rating.data.p75Hrs],
                cost: [rating.data.p25Cost, rating.data.p75Cost],
                days: [rating.data.p25Days, rating.data.p75Days],
              }}
              median={{
                hrs: rating.data.medianHrs,
                cost: rating.data.medianCost,
                days: rating.data.medianDays,
              }}
              overlayName={overlayPt?.name ?? null}
            />
          )}
        </>
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

function DistributionSection({
  ratingName,
  cohort,
  band,
  median,
  overlayName,
}: {
  ratingName: string;
  cohort: RatingCohortMember[];
  band: { hrs: [number, number]; cost: [number, number]; days: [number, number] };
  median: { hrs: number; cost: number; days: number };
  overlayName: string | null;
}) {
  return (
    <>
      <div className="section-head">
        <h2 className="section-title">
          Distribution
          {overlayName && (
            <>
              {' '}
              vs{' '}
              <span style={{ color: 'var(--accent-strong)' }}>{overlayName}</span>
            </>
          )}
        </h2>
        <div className="muted tiny">
          <span className="legend-swatch band" />
          band = P25–P75
          <span className="legend-swatch med" />
          dotted = median
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">{ratingName} — flight hours</div>
            <div className="card-sub">{cohort.length} cohort members</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.hours }))}
            band={{ low: band.hrs[0], high: band.hrs[1] }}
            median={median.hrs}
            highlightName={overlayName}
            yLabel="Hours"
            fmt={(v) => v.toFixed(1)}
          />
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">Total cost</div>
            <div className="card-sub">Per-rating spend, USD</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.cost }))}
            band={{ low: band.cost[0], high: band.cost[1] }}
            median={median.cost}
            highlightName={overlayName}
            yLabel="USD"
            fmt={(v) => (v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${Math.round(v)}`)}
          />
        </div>
      </div>

      <div className="card chart-card">
        <div className="card-head">
          <div>
            <div className="card-title">Calendar days</div>
            <div className="card-sub">Days from start to checkride</div>
          </div>
        </div>
        <div className="card-body">
          <ScatterStrip
            points={cohort.map((p) => ({ student: p.name, value: p.days }))}
            band={{ low: band.days[0], high: band.days[1] }}
            median={median.days}
            highlightName={overlayName}
            yLabel="Days"
            fmt={(v) => Math.round(v).toLocaleString()}
          />
        </div>
      </div>

      <CohortTable cohort={cohort} median={median} overlayName={overlayName} />
    </>
  );
}

function CohortTable({
  cohort,
  median,
  overlayName,
}: {
  cohort: RatingCohortMember[];
  median: { hrs: number; cost: number; days: number };
  overlayName: string | null;
}) {
  const sorted = [...cohort].sort((a, b) => {
    if (a.name === overlayName) return -1;
    if (b.name === overlayName) return 1;
    return a.hours - b.hours;
  });

  return (
    <>
      <div className="section-head">
        <h2 className="section-title">Cohort</h2>
      </div>
      <div className="card table-card">
        <div className="table-wrap" style={{ maxHeight: 360 }}>
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: '32%' }}>Student</th>
                <th className="num" style={{ width: '20%' }}>
                  Hours
                </th>
                <th className="num" style={{ width: '24%' }}>
                  Cost
                </th>
                <th className="num" style={{ width: '24%' }}>
                  Days
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => {
                const isOverlay = p.name === overlayName;
                const hrsDelta = +(p.hours - median.hrs).toFixed(1);
                return (
                  <tr key={p.studentId} className={isOverlay ? 'row-highlight' : ''}>
                    <td>
                      <div className="path-cell">
                        <span className="client-avatar">
                          {p.name
                            .split(' ')
                            .map((s) => s[0])
                            .slice(0, 2)
                            .join('')}
                        </span>
                        <span>{p.name}</span>
                        {isOverlay && (
                          <span className="overlay-pin">overlay</span>
                        )}
                      </div>
                    </td>
                    <td className="num">
                      {p.hours.toFixed(1)}
                      <span className="muted tiny" style={{ marginLeft: 6 }}>
                        {hrsDelta > 0 ? '+' : ''}
                        {hrsDelta}
                      </span>
                    </td>
                    <td className="num">{fmtCost(p.cost)}</td>
                    <td className="num">{p.days}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
