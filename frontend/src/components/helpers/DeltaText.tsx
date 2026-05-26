type Props = {
  value: number | null | undefined;
  betterWhenLower?: boolean;
  fmt?: (v: number) => string;
};

export function DeltaText({ value, betterWhenLower = true, fmt = (v) => String(v) }: Props) {
  if (value === 0 || value === null || value === undefined || Number.isNaN(value)) {
    return <span className="delta-text neutral">{fmt(0)} vs median</span>;
  }
  const positive = betterWhenLower ? value < 0 : value > 0;
  const sign = value > 0 ? '+' : '-';
  return (
    <span className={`delta-text ${positive ? 'good' : 'bad'}`}>
      {sign}
      {fmt(Math.abs(value))} vs median
    </span>
  );
}
