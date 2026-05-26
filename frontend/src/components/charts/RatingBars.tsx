import { useEffect, useMemo, useRef, useState } from 'react';
import type { MetricKey, RatingBarPoint, RatingCode } from '../../data/types';

type Props = {
  data: RatingBarPoint[];
  metric: MetricKey;
  focusedCode?: RatingCode | null;
  onFocus?: (code: RatingCode | null) => void;
};

const METRIC_META: Record<MetricKey, { label: string; color: string; yFormat: (v: number) => string }> = {
  hours: { label: 'Hours', color: '#6E56F8', yFormat: (v) => v.toFixed(0) },
  cost: {
    label: 'Cost',
    color: '#3DD68C',
    yFormat: (v) => (v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${Math.round(v)}`),
  },
  days: { label: 'Days', color: '#F59E0B', yFormat: (v) => Math.round(v).toLocaleString() },
};

function formatMetric(v: number, metric: MetricKey): string {
  if (metric === 'cost') {
    if (v >= 1000) return `$${(v / 1000).toFixed(1)}k`;
    return `$${Math.round(v).toLocaleString()}`;
  }
  if (metric === 'hours') return v.toFixed(1);
  return Math.round(v).toLocaleString();
}

export function RatingBars({ data, metric, focusedCode, onFocus }: Props) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 800, h: 280 });
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: 280 });
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const meta = METRIC_META[metric];
  const padL = 56, padR = 16, padT = 18, padB = 36;
  const innerW = Math.max(10, size.w - padL - padR);
  const innerH = size.h - padT - padB;
  const n = Math.max(1, data.length);
  const slot = innerW / n;
  const barW = Math.min(64, slot * 0.55);

  const maxY = useMemo(() => {
    let m = 0;
    data.forEach((d) => { if (d.p75 > m) m = d.p75; });
    return m * 1.12 || 1;
  }, [data]);

  const yTicks = useMemo(() => {
    const steps = 4;
    return Array.from({ length: steps + 1 }, (_, i) => (maxY / steps) * i);
  }, [maxY]);

  const xAt = (i: number) => padL + slot * (i + 0.5);
  const yAt = (v: number) => padT + innerH - (v / maxY) * innerH;

  return (
    <div className="timechart" ref={ref}>
      <svg width={size.w} height={size.h} onMouseLeave={() => setHover(null)} style={{ cursor: 'default' }}>
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={size.w - padR} y1={yAt(t)} y2={yAt(t)} stroke="var(--grid)" strokeWidth="1" />
            <text x={padL - 8} y={yAt(t) + 3} textAnchor="end" fontSize="10.5" fill="var(--fg-dim)" fontFamily="'Geist Mono', monospace">
              {meta.yFormat(t)}
            </text>
          </g>
        ))}
        <line x1={padL} x2={size.w - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--border-strong)" strokeWidth="1" />

        {data.map((d, i) => {
          const cx = xAt(i);
          const x = cx - barW / 2;
          const y = yAt(d.median);
          const h = Math.max(2, padT + innerH - y);
          const isFocused = focusedCode === d.code;
          const dim = focusedCode && !isFocused;
          const isHover = hover === i;
          return (
            <g
              key={d.code}
              opacity={dim ? 0.32 : 1}
              onMouseEnter={() => setHover(i)}
              onClick={() => onFocus?.(isFocused ? null : (d.code as RatingCode))}
              style={{ cursor: 'pointer' }}
            >
              <rect x={x} y={y} width={barW} height={h} rx="3" fill={meta.color} fillOpacity={isHover || isFocused ? 1 : 0.85} />
              <line x1={cx} x2={cx} y1={yAt(d.p25)} y2={yAt(d.p75)} stroke="var(--fg)" strokeOpacity="0.45" strokeWidth="1.2" />
              <line x1={cx - 8} x2={cx + 8} y1={yAt(d.p25)} y2={yAt(d.p25)} stroke="var(--fg)" strokeOpacity="0.5" strokeWidth="1.2" />
              <line x1={cx - 8} x2={cx + 8} y1={yAt(d.p75)} y2={yAt(d.p75)} stroke="var(--fg)" strokeOpacity="0.5" strokeWidth="1.2" />
              <rect x={cx - slot / 2} y={padT} width={slot} height={innerH} fill="transparent" />
              <text x={cx} y={size.h - 18} textAnchor="middle" fontSize="11" fill={isFocused ? 'var(--fg)' : 'var(--fg-muted)'} fontWeight={isFocused ? 600 : 500}>
                {d.code}
              </text>
              <text x={cx} y={size.h - 5} textAnchor="middle" fontSize="9.5" fill="var(--fg-dim)" fontFamily="'Geist Mono', monospace">
                n={d.n}
              </text>
            </g>
          );
        })}

        {hover != null && data[hover] && (() => {
          const d = data[hover];
          const cx = xAt(hover);
          const tipW = 178, tipH = 88;
          const tx = Math.min(Math.max(cx - tipW / 2, padL), size.w - padR - tipW);
          const ty = Math.max(padT + 4, yAt(d.p75) - tipH - 10);
          return (
            <g pointerEvents="none">
              <rect x={tx} y={ty} width={tipW} height={tipH} rx="8" fill="var(--bg-elev-2)" stroke="var(--border-strong)" />
              <text x={tx + 12} y={ty + 18} fontSize="11.5" fill="var(--fg)" fontWeight="600">
                {d.code} · {d.name}
              </text>
              <text x={tx + 12} y={ty + 36} fontSize="10.5" fill="var(--fg-dim)">
                Median {meta.label.toLowerCase()}
              </text>
              <text x={tx + tipW - 12} y={ty + 36} textAnchor="end" fontSize="12" fill="var(--fg)" fontFamily="'Geist Mono', monospace" fontWeight="500">
                {formatMetric(d.median, metric)}
              </text>
              <text x={tx + 12} y={ty + 54} fontSize="10.5" fill="var(--fg-dim)">P25 – P75</text>
              <text x={tx + tipW - 12} y={ty + 54} textAnchor="end" fontSize="11.5" fill="var(--fg-muted)" fontFamily="'Geist Mono', monospace">
                {formatMetric(d.p25, metric)} – {formatMetric(d.p75, metric)}
              </text>
              <text x={tx + 12} y={ty + 72} fontSize="10.5" fill="var(--fg-dim)">Sample size</text>
              <text x={tx + tipW - 12} y={ty + 72} textAnchor="end" fontSize="11.5" fill="var(--fg-muted)" fontFamily="'Geist Mono', monospace">
                n = {d.n}
              </text>
            </g>
          );
        })()}
      </svg>
    </div>
  );
}
