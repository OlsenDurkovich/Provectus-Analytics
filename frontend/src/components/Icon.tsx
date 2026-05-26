// Ported verbatim from design_handoff_provectus_analytics/design/icons.jsx
// 24x24 viewBox, currentColor strokes. Inline SVGs so color inherits.
import type { SVGProps, ReactNode } from 'react';

export type IconName =
  | 'overview'
  | 'metrics'
  | 'events'
  | 'funnels'
  | 'users'
  | 'settings'
  | 'search'
  | 'bell'
  | 'chevron'
  | 'chevronRight'
  | 'chevronUpDown'
  | 'arrowUp'
  | 'arrowDown'
  | 'arrowUpRight'
  | 'plus'
  | 'calendar'
  | 'sidebar'
  | 'sun'
  | 'moon'
  | 'download'
  | 'columns'
  | 'filter'
  | 'line'
  | 'bar'
  | 'area'
  | 'more'
  | 'pin'
  | 'star'
  | 'check'
  | 'close'
  | 'flash'
  | 'activity'
  | 'folder'
  | 'sparkles'
  | 'plane';

type IconProps = Omit<SVGProps<SVGSVGElement>, 'name'> & {
  name: IconName;
  size?: number;
};

const PATHS: Record<IconName, ReactNode> = {
  overview: (
    <>
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </>
  ),
  metrics: (
    <>
      <path d="M4 20V10" />
      <path d="M10 20V4" />
      <path d="M16 20v-7" />
      <path d="M22 20H2" />
    </>
  ),
  events: <path d="M13 2L4.5 12.5h6L9 22l8.5-10.5h-6L13 2z" />,
  funnels: <path d="M3 5h18l-7 8v6l-4 2v-8L3 5z" />,
  users: (
    <>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20c.5-3.4 3.4-5.5 6.5-5.5s6 2.1 6.5 5.5" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M15 14.7c.6-.4 1.3-.6 2-.6 2.5 0 4.5 1.6 5 4.4" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="2.6" />
      <path d="M19.4 14.6a1.6 1.6 0 0 0 .3 1.7l.1.1a2 2 0 1 1-2.7 2.7l-.1-.1a1.6 1.6 0 0 0-1.7-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.7.3l-.1.1a2 2 0 1 1-2.7-2.7l.1-.1a1.6 1.6 0 0 0 .3-1.7 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.7l-.1-.1a2 2 0 1 1 2.7-2.7l.1.1a1.6 1.6 0 0 0 1.7.3h0a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1c0 .6.4 1.2 1 1.5h0a1.6 1.6 0 0 0 1.7-.3l.1-.1a2 2 0 1 1 2.7 2.7l-.1.1a1.6 1.6 0 0 0-.3 1.7v0a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  bell: (
    <>
      <path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8z" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </>
  ),
  chevron: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  chevronUpDown: (
    <>
      <path d="m7 15 5 5 5-5" />
      <path d="m7 9 5-5 5 5" />
    </>
  ),
  arrowUp: (
    <>
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </>
  ),
  arrowDown: (
    <>
      <path d="M12 5v14" />
      <path d="m19 12-7 7-7-7" />
    </>
  ),
  arrowUpRight: (
    <>
      <path d="M7 17 17 7" />
      <path d="M7 7h10v10" />
    </>
  ),
  plus: (
    <>
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </>
  ),
  calendar: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4" />
      <path d="M8 3v4" />
      <path d="M3 11h18" />
    </>
  ),
  sidebar: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.9 4.9 1.4 1.4" />
      <path d="m17.7 17.7 1.4 1.4" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m4.9 19.1 1.4-1.4" />
      <path d="m17.7 6.3 1.4-1.4" />
    </>
  ),
  moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
  download: (
    <>
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M5 21h14" />
    </>
  ),
  columns: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M9 4v16" />
      <path d="M15 4v16" />
    </>
  ),
  filter: <path d="M3 5h18l-7 8v6l-4 2v-8L3 5z" />,
  line: (
    <>
      <path d="M3 17l5-7 4 3 8-9" />
      <path d="M21 4h-4" />
      <path d="M21 4v4" />
    </>
  ),
  bar: (
    <>
      <path d="M4 20V10" />
      <path d="M10 20V4" />
      <path d="M16 20v-7" />
    </>
  ),
  area: <path d="M3 17 8 9l4 3 8-10v15z" />,
  more: (
    <>
      <circle cx="5" cy="12" r="1" />
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
    </>
  ),
  pin: (
    <>
      <path d="M12 17v5" />
      <path d="M5 9V4h14v5l-3 4v3H8v-3z" />
    </>
  ),
  star: <path d="M12 2.5l3 6.5 7 .8-5.2 4.8L18 22l-6-3.6L6 22l1.2-7.4L2 9.8 9 9z" />,
  check: <path d="m5 12 5 5L20 7" />,
  close: (
    <>
      <path d="M6 6l12 12" />
      <path d="M18 6 6 18" />
    </>
  ),
  flash: <path d="M13 2 4 13h7l-1 9 9-11h-7z" />,
  activity: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
  folder: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
  sparkles: (
    <>
      <path d="M12 3v4" />
      <path d="M12 17v4" />
      <path d="M3 12h4" />
      <path d="M17 12h4" />
      <path d="m5.6 5.6 2.8 2.8" />
      <path d="m15.6 15.6 2.8 2.8" />
      <path d="m5.6 18.4 2.8-2.8" />
      <path d="m15.6 8.4 2.8-2.8" />
    </>
  ),
  plane: (
    <>
      <path
        d="M12 2 9 9H2l5 4-2 9 7-5 7 5-2-9 5-4h-7z"
        transform="rotate(45 12 12)"
        fill="none"
      />
      <path d="M22 12 14 8 13 3l-2 .5-1 5-7 4 1 1 6-1 4 6 1-2 .5-1z" />
    </>
  ),
};

export function Icon({ name, size = 16, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {PATHS[name] ?? null}
    </svg>
  );
}
