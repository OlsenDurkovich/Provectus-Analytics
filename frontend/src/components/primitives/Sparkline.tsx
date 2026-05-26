// Ported from design_handoff_provectus_analytics/design/primitives.jsx
type SparklineProps = {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fill?: boolean;
  strokeWidth?: number;
};

export function Sparkline({
  data,
  width = 120,
  height = 36,
  color = 'currentColor',
  fill = true,
  strokeWidth = 1.5,
}: SparklineProps) {
  if (!data || data.length === 0) return null;
  const w = width;
  const h = height;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const stepX = w / (data.length - 1 || 1);
  const points: [number, number][] = data.map((v, i) => [
    i * stepX,
    h - ((v - min) / range) * (h - 4) - 2,
  ]);
  const path = points
    .map((p, i) => (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ' ' + p[1].toFixed(1))
    .join(' ');
  const areaPath = `${path} L ${w} ${h} L 0 ${h} Z`;
  const gradId = 'spg-' + Math.random().toString(36).slice(2, 8);
  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      style={{ width: '100%', height: '100%', display: 'block', color }}
    >
      {fill && (
        <>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
              <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradId})`} stroke="none" />
        </>
      )}
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
