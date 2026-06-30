// Sidebar — ported from design_handoff_provectus_analytics/design/panels.jsx
// Active link state is driven by react-router-dom URL (was a `current` prop in the prototype).
import { NavLink } from 'react-router-dom';
import { Icon, type IconName } from './Icon';
import { useMeta } from '../data/queries';
import type { StoredUser } from '../auth/storage';

function initialsFromEmail(email: string): string {
  const local = (email.split('@')[0] || email).trim();
  const parts = local.split(/[.\-_+]/).filter(Boolean);
  const raw = parts.length >= 2 ? parts[0][0] + parts[1][0] : local.slice(0, 2);
  return raw.toUpperCase() || 'U';
}

type NavItem = {
  key: 'overview' | 'rating' | 'student' | 'instructor' | 'insights' | 'flights' | 'users' | 'mytraining' | 'mystudents';
  label: string;
  icon: IconName;
  kbd: string;
  path: string;
  adminOnly?: boolean;
  studentOnly?: boolean;
  instructorOnly?: boolean;
  // For dashboard pages: the page-access key that controls visibility.
  page?: 'overview' | 'ratings' | 'students' | 'instructors' | 'insights';
};

export const NAV: NavItem[] = [
  { key: 'overview', label: 'Overview', icon: 'overview', kbd: 'O', path: '/', page: 'overview' },
  { key: 'rating', label: 'Rating detail', icon: 'metrics', kbd: 'R', path: '/ratings', page: 'ratings' },
  { key: 'student', label: 'Student', icon: 'users', kbd: 'S', path: '/students', page: 'students' },
  { key: 'instructor', label: 'Instructor', icon: 'star', kbd: 'I', path: '/instructors', page: 'instructors' },
  { key: 'insights', label: 'Insights', icon: 'metrics', kbd: 'N', path: '/insights', page: 'insights' },
  { key: 'flights', label: 'Flights', icon: 'plane', kbd: 'F', path: '/flights', adminOnly: true },
  { key: 'users', label: 'Users', icon: 'users', kbd: 'U', path: '/users', adminOnly: true },
  { key: 'mytraining', label: 'My training', icon: 'overview', kbd: 'T', path: '/my-training', studentOnly: true },
  { key: 'mystudents', label: 'My students', icon: 'users', kbd: 'M', path: '/my-students', instructorOnly: true },
];

type Props = {
  collapsed: boolean;
  user?: StoredUser | null;
  isStudent?: boolean;
  isInstructor?: boolean;
  onUpload?: () => void;
  onImport?: () => void;
  onRebuild?: (synthetic: boolean) => void;
  importPending?: boolean;
  rebuildPending?: boolean;
};

export function Sidebar({
  collapsed,
  user = null,
  isStudent = false,
  isInstructor = false,
  onUpload,
  onImport,
  onRebuild,
  importPending = false,
  rebuildPending = false,
}: Props) {
  const scoped = isStudent || isInstructor;
  const meta = useMeta();
  const isAdmin = user?.is_admin ?? false;
  const canSee = (page: string) => isAdmin || (user?.pages?.includes(page) ?? false);
  const userEmail = user?.email ?? '';
  const displayName = user?.display_name || userEmail;
  const userInitials = (user?.display_name
    ? user.display_name.trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join('')
    : userEmail ? initialsFromEmail(userEmail) : 'PA').toUpperCase() || 'PA';
  const roleLabel = user?.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1)
    : 'Internal analytics';
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
            {isStudent
              ? 'Student portal'
              : isInstructor
                ? 'Instructor portal'
                : `Analytics · ${clientCount > 0 ? `${clientCount} clients` : 'synthetic'}`}
          </div>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Analytics</div>
        {NAV.filter((n) =>
          n.adminOnly
            ? isAdmin
            : n.studentOnly
              ? isStudent
              : n.instructorOnly
                ? isInstructor
                : !scoped && (!n.page || canSee(n.page)),
        ).map((n) => (
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

      <div className="sidebar-spacer" />

      {!collapsed && (onUpload || onImport || onRebuild) && (
        <div className="sidebar-section">
          <div className="sidebar-section-label">Data actions</div>
          {onUpload && (
            <button
              type="button"
              className="nav-item"
              onClick={onUpload}
            >
              <span className="nav-item-icon">
                <Icon name="download" size={14} />
              </span>
              <span className="nav-item-label">Upload FSP</span>
            </button>
          )}
          {onImport && (
            <button
              type="button"
              className="nav-item"
              onClick={onImport}
              disabled={importPending}
              title="Pick up FSP exports from ~/Downloads (local dev only)"
            >
              <span className="nav-item-icon">
                <Icon name="download" size={14} />
              </span>
              <span className="nav-item-label">
                {importPending ? 'Importing…' : 'Import from Downloads'}
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

      {!collapsed && !scoped && (
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
        <div className="user-avatar">{userInitials}</div>
        {!collapsed && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="user-name">{displayName || 'Not signed in'}</div>
            <div className="user-email">{roleLabel}</div>
          </div>
        )}
      </div>
    </aside>
  );
}
