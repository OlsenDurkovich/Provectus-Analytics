import { useState } from 'react';
import type { RangeKey } from '../data/types';

// Default to all-time: this is a *historical* alumni dataset — most students
// finished training >12 months ago, so a 12-month default hid ~90% of them.
export function useRange(initial: RangeKey = 'all') {
  const [range, setRange] = useState<RangeKey>(initial);
  return { range, setRange };
}
