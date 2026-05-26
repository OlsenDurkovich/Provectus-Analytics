import { useMemo, useState } from 'react';
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { Sidebar, NAV } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import Overview from './routes/Overview';
import RatingDetail from './routes/RatingDetail';
import Student from './routes/Student';
import Instructor from './routes/Instructor';
import Flights from './routes/Flights';
import { useTheme } from './hooks/useTheme';
import { useShortcuts } from './hooks/useShortcuts';
import { usePersistedTab } from './hooks/usePersistedTab';
import { useRange } from './hooks/useRange';

function breadcrumbFor(pathname: string): string {
  for (const n of NAV) {
    if (n.path === '/' && pathname === '/') return n.label;
    if (n.path !== '/' && pathname.startsWith(n.path)) return n.label;
  }
  return 'Overview';
}

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggle: toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [, setCmdkOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const { range, setRange } = useRange();
  usePersistedTab();

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
      <Sidebar collapsed={collapsed} />
      <div className="main">
        <Topbar
          breadcrumb={breadcrumb}
          range={range}
          onRangeChange={setRange}
          onToggleSidebar={() => setCollapsed((v) => !v)}
          onOpenCmdK={() => setCmdkOpen(true)}
          theme={theme}
          onThemeToggle={toggleTheme}
          onImport={() => {
            /* wired in Phase 9 */
          }}
          notifOpen={notifOpen}
          setNotifOpen={setNotifOpen}
          showRangePicker={isOverview}
        />
        <div className="canvas">
          <Routes>
            <Route path="/" element={<Overview range={range} />} />
            <Route path="/ratings/:code?" element={<RatingDetail range={range} />} />
            <Route path="/students/:id?" element={<Student />} />
            <Route path="/instructors/:id?" element={<Instructor />} />
            <Route path="/flights" element={<Flights />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
