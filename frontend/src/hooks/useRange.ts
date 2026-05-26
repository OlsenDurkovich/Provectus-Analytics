import { useState } from 'react';
import type { RangeKey } from '../data/types';

export function useRange(initial: RangeKey = '12mo') {
  const [range, setRange] = useState<RangeKey>(initial);
  return { range, setRange };
}
