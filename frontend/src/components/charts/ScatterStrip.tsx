import { useEffect, useRef, useState } from 'react';

interface Point {
  student: string;
  value: number;
}

interface Props {
  points: Point[];
  band: { low: number; high: number };
  median: number;
  highlightNames: string[];
  yLabel: string;
  fmt: (v: number) => string;
  height?: number;
  size?: 'full' | 'mini';
  highlightInProgress?: boolean;
}

export function ScatterStrip({
  points,
  band,
  median,
  highlightNames,
  yLabel,
  fmt,
  height,
  size = 'full',
  highlightInProgress = false,
}: Props) {
  const mini = size === 'mini';
  const resolvedHeight = height ?? (mini ? 64 : 280);

  const ref = useRef<HTMLDivElement | null>(null);
  const [w, setW] = useState(800);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = mini ? 36 : 56;
  const padR = mini ? 8 : 16;
  const padT = mini ? 8 : 18;
  const padB = mini ? 8 : 16;
  const innerW = Math.max(10, w - padL - padR);
  const innerH = resolvedHeight - padT - padB;
  const n = Math.max(1, points.length);

  const allVals = [...points.map((p) => p.value), band.low, band.high, median];
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const span = Math.max(1, maxV - minV);
  const yMin = minV - span * 0.12;
  const yMax = maxV + span * 0.12;
  const ySpan = Math.max(1, yMax - yMin);

  const yAt = (v: number) => padT + innerH - ((v - yMin) / ySpan) * innerH;
  const xAt = (i: number) => padL + ((i + 1) / (n + 1)) * innerW;

  const tickCount = mini ? 2 : 5;
  const ticks = Array.from(
    { length: tickCount },
    (_, i) => yMin + (ySpan * i) / (tickCount - 1),
  );

  const dotR = mini ? 3 : 5;
  const dotRHighlight = mini ? 4 : 7;
  const tickFont = mini ? 9 : 10.5;

  return (
    <div ref={ref} className="timechart">
      <svg
        width={w}
        height={resolvedHeight}
        onMouseLeave={() => setHovered(null)}
        style={{ cursor: 'default' }}
      >
        {/* Grid lines + y-axis labels */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line
              x1={padL}
              x2={w - padR}
              y1={yAt(t)}
              y2={yAt(t)}
              stroke="var(--grid)"
              strokeWidth="1"
            />
            <text
              x={padL - 6}
              y={yAt(t) + 3}
              textAnchor="end"
              fontSize={tickFont}
              fill="var(--fg-dim)"
              fontFamily="'Geist Mono', monospace"
            >
              {fmt(t)}
            </text>
          </g>
        ))}

        {/* Y-axis label (full only) */}
        {!mini && (
          <text
            x={10}
            y={padT + innerH / 2}
            textAnchor="middle"
            fontSize="10"
            fill="var(--fg-dim)"
            transform={`rotate(-90, 10, ${padT + innerH / 2})`}
          >
            {yLabel}
          </text>
        )}

        {/* P25-P75 band */}
        <rect
          x={padL}
          y={yAt(band.high)}
          width={innerW}
          height={Math.max(0, yAt(band.low) - yAt(band.high))}
          fill="color-mix(in oklab, var(--accent) 14%, transparent)"
        />

        {/* Median dashed line */}
        <line
          x1={padL}
          x2={w - padR}
          y1={yAt(median)}
          y2={yAt(median)}
          stroke="var(--accent)"
          strokeWidth="1.2"
          strokeDasharray="4 3"
          opacity="0.7"
        />

        {/* Dots */}
        {points.map((p, i) => {
          const isHighlighted = highlightNames.includes(p.student);
          const inProgress = isHighlighted && highlightInProgress;
          const cx = xAt(i);
          const cy = yAt(p.value);
          return (
            <g key={i} onMouseEnter={() => setHovered(i)}>
              <circle
                cx={cx}
                cy={cy}
                r={isHighlighted ? dotRHighlight : dotR}
                fill={
                  inProgress
                    ? 'var(--warn)'
                    : isHighlighted
                      ? 'var(--accent)'
                      : 'var(--fg-dim)'
                }
                fillOpacity={isHighlighted ? 1 : 0.5}
                stroke={isHighlighted ? 'var(--bg)' : 'none'}
                strokeWidth="1.5"
              />
            </g>
          );
        })}

        {/* Hover tooltip */}
        {hovered !== null &&
          points[hovered] &&
          (() => {
            const p = points[hovered];
            const cx = xAt(hovered);
            const cy = yAt(p.value);
            const tipW = mini ? 124 : 152;
            const tipH = mini ? 36 : 44;
            const tx = Math.min(Math.max(cx - tipW / 2, padL), w - padR - tipW);
            const ty = Math.max(padT + 4, cy - tipH - 10);
            return (
              <g pointerEvents="none">
                <rect
                  x={tx}
                  y={ty}
                  width={tipW}
                  height={tipH}
                  rx="6"
                  fill="var(--bg-elev-2)"
                  stroke="var(--border-strong)"
                />
                <text
                  x={tx + 10}
                  y={ty + (mini ? 14 : 17)}
                  fontSize={mini ? 10 : 11}
                  fill="var(--fg)"
                  fontWeight="500"
                >
                  {highlightNames.includes(p.student) && highlightInProgress
                    ? `${p.student} (in progress)`
                    : p.student}
                </text>
                <text
                  x={tx + 10}
                  y={ty + (mini ? 27 : 33)}
                  fontSize={mini ? 10 : 11}
                  fill="var(--fg-dim)"
                  fontFamily="'Geist Mono', monospace"
                >
                  {fmt(p.value)}
                </text>
              </g>
            );
          })()}
      </svg>
    </div>
  );
}
