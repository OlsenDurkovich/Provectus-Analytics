import { Icon } from '../Icon';

type DeltaProps = {
  value: number;
  positive: boolean;
};

export function Delta({ value, positive }: DeltaProps) {
  const goingUp = value >= 0;
  return (
    <span className={'delta ' + (positive ? 'up' : 'down')}>
      <Icon name={goingUp ? 'arrowUp' : 'arrowDown'} size={11} strokeWidth={2} />
      <span>{Math.abs(value).toFixed(1)}%</span>
    </span>
  );
}
