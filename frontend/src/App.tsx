import { useMemo, useState } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar, NAV } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { CmdK } from './components/CmdK';
import { ErrorBoundary } from './components/ErrorBoundary';
import Overview from './routes/Overview';
import RatingDetail from './routes/RatingDetail';
import Student from './routes/Student';
import Instructor from './routes/Instructor';
import Flights from './routes/Flights';
import Users from './routes/Users';
import MyTraining from './routes/MyTraining';
import Login from './routes/Login';
import PublicTransparency from './routes/PublicTransparency';
import { useTheme } from './hooks/useTheme';
import { useShortcuts } from './hooks/useShortcuts';
import { usePersistedTab } from './hooks/usePersistedTab';
import { useRange } from './hooks/useRange';
import { useImportFsp, useRebuild } from './data/queries';
import { useAuth } from './auth/AuthContext';
import { UploadDialog } from './components/UploadDialog';
import { ChangePasswordDialog } from './components/ChangePasswordDialog';

function breadcrumbFor(pathname: string): string {
  for (const n of NAV) {
    if (n.path === '/' && pathname === '/') return n.label;
    if (n.path !== '/' && pathname.startsWith(n.path)) return n.label;
  }
  return 'Overview';
}

export default function App() {
  const { status, user, logout, isAdmin, isStudent, canSee } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const location = useLocation();

  // Public, unauthenticated marketing page — bypasses the auth gate entirely.
  if (location.pathname.startsWith('/transparency')) {
    return <PublicTransparency />;
  }

  // Theme has to be wired even on the login page so the form respects light/dark.
  if (status === 'unauthenticated') {
    return <Login />;
  }

  return (
    <Shell
      user={user}
      isAdmin={isAdmin}
      isStudent={isStudent}
      canSee={canSee}
      logout={logout}
      theme={theme}
      toggleTheme={toggleTheme}
    />
  );
}

function NoAccess() {
  return (
    <div style={{ padding: 24, color: 'var(--fg-dim)', fontSize: 14 }}>
      You don’t have access to any pages yet. Ask an admin to grant you access.
    </div>
  );
}

type ShellProps = {
  user: ReturnType<typeof useAuth>['user'];
  isAdmin: boolean;
  isStudent: boolean;
  canSee: (page: string) => boolean;
  logout: ReturnType<typeof useAuth>['logout'];
  theme: ReturnType<typeof useTheme>['theme'];
  toggleTheme: ReturnType<typeof useTheme>['toggle'];
};

function Shell({ user, isAdmin, isStudent, canSee, logout, theme, toggleTheme }: ShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [pwOpen, setPwOpen] = useState(false);
  const { range, setRange } = useRange();
  const importMut = useImportFsp();
  const rebuildMut = useRebuild();
  usePersistedTab();

  // First dashboard page this user can see — the redirect target when they
  // land on a page they're not allowed to access.
  const DASH_PAGES: [string, string][] = [
    ['overview', '/'],
    ['ratings', '/ratings'],
    ['students', '/students'],
    ['instructors', '/instructors'],
  ];
  // Students have no dashboard pages — their home is the My-training view.
  const firstAllowedPath = isStudent
    ? '/my-training'
    : (DASH_PAGES.find(([p]) => canSee(p))?.[1] ?? null);

  const handlers = useMemo(
    () => ({
      onCmdK: () => setCmdkOpen((v) => !v),
      onCollapseSidebar: () => setCollapsed((v) => !v),
      onToggleTheme: toggleTheme,
      onNavOverview: () => navigate('/'),
      onNavRating: () => navigate('/ratings'),
      onNavStudent: () => navigate('/students'),
      onNavInstructor: () => navigate('/instructors'),
      onNavFlights: () => navigate('/flights'),
    }),
    [navigate, toggleTheme],
  );

  useShortcuts(handlers);

  const breadcrumb = breadcrumbFor(location.pathname);
  const isOverview = location.pathname === '/';

  return (
    <div className={'app ' + (collapsed ? 'sidebar-collapsed' : '')}>
      <Sidebar
        collapsed={collapsed}
        user={user}
        isStudent={isStudent}
        onUpload={isAdmin ? () => setUploadOpen(true) : undefined}
        onImport={isAdmin ? () => importMut.mutate() : undefined}
        onRebuild={isAdmin ? (synthetic) => rebuildMut.mutate({ synthetic }) : undefined}
        importPending={importMut.isPending}
        rebuildPending={rebuildMut.isPending}
      />
      <div className="main-col">
        <Topbar
          breadcrumb={breadcrumb}
          range={range}
          onRangeChange={setRange}
          onToggleSidebar={() => setCollapsed((v) => !v)}
          onOpenCmdK={() => setCmdkOpen(true)}
          theme={theme}
          onThemeToggle={toggleTheme}
          onImport={() => setUploadOpen(true)}
          importPending={importMut.isPending}
          showImport={isAdmin}
          showRangePicker={isOverview}
          userEmail={user?.email ?? null}
          onChangePassword={() => setPwOpen(true)}
          onLogout={logout}
        />
        <div className="canvas">
          <ErrorBoundary>
            <Routes>
              <Route
                path="/"
                element={
                  canSee('overview') ? (
                    <Overview range={range} />
                  ) : firstAllowedPath ? (
                    <Navigate to={firstAllowedPath} replace />
                  ) : (
                    <NoAccess />
                  )
                }
              />
              <Route
                path="/ratings/:code?"
                element={
                  canSee('ratings') ? (
                    <RatingDetail range={range} />
                  ) : (
                    <Navigate to={firstAllowedPath ?? '/'} replace />
                  )
                }
              />
              <Route
                path="/students/:id?"
                element={canSee('students') ? <Student /> : <Navigate to={firstAllowedPath ?? '/'} replace />}
              />
              <Route
                path="/instructors/:id?"
                element={canSee('instructors') ? <Instructor /> : <Navigate to={firstAllowedPath ?? '/'} replace />}
              />
              <Route
                path="/flights"
                element={isAdmin ? <Flights /> : <Navigate to={firstAllowedPath ?? '/'} replace />}
              />
              <Route
                path="/users"
                element={isAdmin ? <Users /> : <Navigate to={firstAllowedPath ?? '/'} replace />}
              />
              <Route
                path="/my-training"
                element={isStudent ? <MyTraining /> : <Navigate to={firstAllowedPath ?? '/'} replace />}
              />
            </Routes>
          </ErrorBoundary>
        </div>
      </div>
      <CmdK
        open={cmdkOpen}
        onClose={() => setCmdkOpen(false)}
        onNavigate={(path) => navigate(path)}
        onSetRange={setRange}
        onToggleTheme={toggleTheme}
        onImport={() => setUploadOpen(true)}
        onRebuild={(synthetic) => rebuildMut.mutate({ synthetic })}
      />
      <UploadDialog open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <ChangePasswordDialog open={pwOpen} onClose={() => setPwOpen(false)} />
    </div>
  );
}
