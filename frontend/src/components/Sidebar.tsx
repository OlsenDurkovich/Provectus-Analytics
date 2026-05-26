// Sidebar — ported from design_handoff_provectus_analytics/design/panels.jsx
// Active link state is driven by react-router-dom URL (was a `current` prop in the prototype).
import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from './Icon';
import { useMeta } from '../data/queries';

type NavItem = {
  key: 'overview' | 'rating' | 'student' | 'instructor' | 'flights';
  label: string;
  icon: IconName;
  kbd: string;
  path: string;
};

export const NAV: NavItem[] = [
  { key: 'overview', label: 'Overview', icon: 'overview', kbd: 'O', path: '/' },
  { key: 'rating', label: 'Rating detail', icon: 'metrics', kbd: 'R', path: '/ratings' },
  { key: 'student', label: 'Student', icon: 'users', kbd: 'S', path: '/students' },
  { key: 'instructor', label: 'Instructor', icon: 'star', kbd: 'I', path: '/instructors' },
  { key: 'flights', label: 'Flights', icon: 'plane', kbd: 'F', path: '/flights' },
];

type PinnedReport = { name: string; dot: string };
const DEFAULT_PINNED: PinnedReport[] = [
  { name: 'PPL cost trend', dot: '#6E56F8' },
  { name: 'IFR vs cohort', dot: '#3DD68C' },
  { name: 'CFI throughput', dot: '#22D3EE' },
  { name: 'Q2 ops summary', dot: '#F59E0B' },
];

type Props = {
  collapsed: boolean;
  onImport?: () => void;
  onRebuild?: (synthetic: boolean) => void;
  importPending?: boolean;
  rebuildPending?: boolean;
};

export function Sidebar({
  collapsed,
  onImport,
  onRebuild,
  importPending = false,
  rebuildPending = false,
}: Props) {
  const meta = useMeta();
  const ds = meta.data?.dataState ?? {
    flights: 0,
    invoices: 0,
    students: 0,
    surveys: 0,
    overrides: 0,
  };
  const clientCount = meta.data?.liveClientCount ?? 0;

  return (
    <aside className={'sidebar ' + (collapsed ? 'collapsed' : '')}>
      <div className="workspace">
        <div className="workspace-logo">
          <img src="/Provectus.jpg" alt="Provectus Aviation" width={16} height={16} />
        </div>
        <div className="workspace-label">
          <div className="workspace-name">Provectus Aviation</div>
          <div className="workspace-plan">
            Analytics · {clientCount > 0 ? `${clientCount} clients` : 'synthetic'}
          </div>
        </div>
        <span className="workspace-chevron">
          <Icon name="chevronUpDown" size={14} />
        </span>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Analytics</div>
        {NAV.map((n) => (
          <NavLink
            key={n.key}
            to={n.path}
            end={n.path === '/'}
            className={({ isActive }) => 'nav-item ' + (isActive ? 'active' : '')}
          >
            <span className="nav-item-icon">
              <Icon name={n.icon} size={16} />
            </span>
            <span className="nav-item-label">{n.label}</span>
            {!collapsed && <span className="nav-item-kbd">{n.kbd}</span>}
          </NavLink>
        ))}
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Pinned reports</div>
        <div className="pinned-list">
          {DEFAULT_PINNED.map((p) => (
            <button key={p.name} className="pinned-item" type="button">
              <span className="pinned-dot" style={{ background: p.dot }} />
              <span className="nav-item-label">{p.name}</span>
            </button>
          ))}
          {!collapsed && (
            <button
              className="pinned-item"
              style={{ color: 'var(--fg-dim)' }}
              type="button"
            >
              <Icon name="plus" size={12} />
              <span className="nav-item-label">Pin a report</span>
            </button>
          )}
        </div>
      </div>

      <div className="sidebar-spacer" />

      {!collapsed && (onImport || onRebuild) && (
        <div className="sidebar-section">
          <div className="sidebar-section-label">Data actions</div>
          {onImport && (
            <button
              type="button"
              className="nav-item"
              onClick={onImport}
              disabled={importPending}
            >
              <span className="nav-item-icon">
                <Icon name="download" size={14} />
              </span>
              <span className="nav-item-label">
                {importPending ? 'Importing…' : 'Import FSP'}
              </span>
            </button>
          )}
          {onRebuild && (
            <button
              type="button"
              className="nav-item"
              onClick={() => onRebuild(false)}
              disabled={rebuildPending}
            >
              <span className="nav-item-icon">
                <Icon name="sparkles" size={14} />
              </span>
              <span className="nav-item-label">
                {rebuildPending ? 'Rebuilding…' : 'Rebuild DB'}
              </span>
            </button>
          )}
        </div>
      )}

      {!collapsed && (
        <div className="data-state">
          <div className="data-state-label">Data state</div>
          <div className="data-state-row">
            <span>Flights</span>
            <span className="num">{ds.flights.toLocaleString()}</span>
          </div>
          <div className="data-state-row">
            <span>Invoices</span>
            <span className="num">{ds.invoices.toLocaleString()}</span>
          </div>
          <div className="data-state-row">
            <span>Students</span>
            <span className="num">{ds.students}</span>
          </div>
          <div className="data-state-row">
            <span>Surveys</span>
            <span className="num">{ds.surveys}</span>
          </div>
          <div className="data-state-row">
            <span>Overrides</span>
            <span className="num">{ds.overrides}</span>
          </div>
        </div>
      )}

      <div className="user-menu">
        <div className="user-avatar">PA</div>
        {!collapsed && (
          <>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="user-name">Provectus Aviation</div>
              <div className="user-email">Internal analytics</div>
            </div>
            <span style={{ color: 'var(--fg-dim)' }}>
              <Icon name="chevronUpDown" size={14} />
            </span>
          </>
        )}
      </div>
    </aside>
  );
}
