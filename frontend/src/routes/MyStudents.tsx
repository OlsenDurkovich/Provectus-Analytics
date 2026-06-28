// Instructor-facing page. An `instructor`-role account sees ONLY this: their
// own roster, served by /api/me/students (locked to their linked instructor
// name). No cost/billing — progress only — by design.
import { BigKpi } from '../components/helpers';
import { Skel } from '../components/primitives';
import { useMyStudents } from '../data/queries';
import type { MyStudentRow, MyStudentsView } from '../data/types';

const STATUS_STYLE: Record<string, { color: string }> = {
  Completed: { color: 'var(--positive)' },
  'On checkride': { color: 'var(--accent-strong, var(--accent))' },
  Active: { color: 'var(--fg-muted)' },
};

export default function MyStudents() {
  const q = useMyStudents();

  return (
    <div className="student-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">My account</div>
          <h1 className="page-title">My students</h1>
          <div className="page-sub">
            Your students' flight hours and rating progress.
          </div>
        </div>
      </div>

      {q.isLoading ? (
        <Skel h={240} />
      ) : q.data ? (
        <Body view={q.data} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">No students found</div>
            <div className="empty-sub">
              Your account isn’t linked to an instructor record yet, or that
              instructor has no students. Ask an admin to check.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Body({ view }: { view: MyStudentsView }) {
  const totalHours = view.students.reduce((a, s) => a + (s.hoursToDate ?? 0), 0);
  const uniqueStudents = new Set(view.students.map((s) => s.id)).size;
  const completed = view.students.filter((s) => s.status === 'Completed').length;

  return (
    <>
      <div className="kpi-grid">
        <BigKpi label="Students" value={String(uniqueStudents)} sub="Across all ratings you've taught" />
        <BigKpi label="Enrollments" value={String(view.students.length)} sub="Student × rating" />
        <BigKpi label="Total flight hours" value={totalHours.toFixed(1)} sub="Hours you've instructed" />
        <BigKpi label="Checkrides passed" value={String(completed)} sub="Completed ratings" />
      </div>

      <div className="section-head">
        <h2 className="section-title">Roster</h2>
        <div className="muted tiny">One row per student / rating. Progress vs cohort median hours.</div>
      </div>
      <div className="card">
        <div className="card-body" style={{ padding: 0 }}>
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>Student</th>
                <th style={{ textAlign: 'left' }}>Rating</th>
                <th style={{ textAlign: 'right' }}>Hours</th>
                <th style={{ textAlign: 'right' }}>Days</th>
                <th style={{ textAlign: 'left' }}>Progress</th>
                <th style={{ textAlign: 'left' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {view.students.map((s, i) => (
                <Row key={`${s.id}-${s.rating}-${i}`} s={s} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Row({ s }: { s: MyStudentRow }) {
  const pct = Math.round(Math.min(s.progressPct, 1) * 100);
  return (
    <tr>
      <td>{s.name}</td>
      <td><span className="rating-chip">{s.rating}</span></td>
      <td style={{ textAlign: 'right' }} className="num">{s.hoursToDate.toFixed(1)}</td>
      <td style={{ textAlign: 'right' }} className="num">{s.daysEnrolled.toLocaleString()}</td>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 6, background: 'var(--bg-elev-2, var(--bg-elev))', borderRadius: 3, minWidth: 80 }}>
            <div style={{ width: `${pct}%`, height: '100%', background: 'var(--accent)', borderRadius: 3 }} />
          </div>
          <span className="tiny muted num">{pct}%</span>
        </div>
      </td>
      <td style={STATUS_STYLE[s.status] ?? {}}>{s.status}</td>
    </tr>
  );
}
