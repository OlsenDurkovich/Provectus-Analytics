import type { CSSProperties } from 'react';

type SkelProps = {
  w?: number | string;
  h?: number | string;
  style?: CSSProperties;
};

export function Skel({ w = '100%', h = 12, style }: SkelProps) {
  return <div className="skel" style={{ width: w, height: h, ...style }} />;
}
