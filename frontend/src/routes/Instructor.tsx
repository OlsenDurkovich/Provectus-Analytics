import { useNavigate, useParams } from 'react-router-dom';
import { BigKpi, Select } from '../components/helpers';
import { Skel } from '../components/primitives';
import { useInstructor, useInstructors } from '../data/queries';
import type { InstructorDetail } from '../data/types';

function fmtCost(v: number): string {
  return `$${Math.round(v).toLocaleString()}`;
}

export default function Instructor() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const listQ = useInstructors();
  const detailQ = useInstructor(id);

  const opts = (listQ.data ?? []).map((i) => ({ value: i.id, label: i.name }));

  return (
    <div className="instructor-detail">
      <div className="page-head">
        <div>
          <div className="eyebrow">People</div>
          <h1 className="page-title">Instructor</h1>
          <div className="page-sub">Efficiency relative to cohort medians, per rating.</div>
        </div>
        <div className="page-head-tools">
          <Select<string>
            label="Instructor"
            value={id ?? ''}
            onChange={(v) => v && navigate(`/instructors/${encodeURIComponent(v)}`)}
            options={opts}
            width={220}
          />
        </div>
      </div>

      {!id ? (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Pick an instructor</div>
            <div className="empty-sub">Use the selector above to drill in.</div>
          </div>
        </div>
      ) : detailQ.isLoading ? (
        <Skel h={240} />
      ) : detailQ.data ? (
        <InstructorBody detail={detailQ.data} />
      ) : (
        <div className="card">
          <div className="empty">
            <div className="empty-title">Instructor not found</div>
            <div className="empty-sub">{id}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function InstructorBody({ detail }: { detail: InstructorDetail }) {
  const totalHours = detail.students.reduce((s, c) => s + c.hoursToDate, 0);
  const studentsAtCheckride = detail.students.filter((s) => s.status === 'Completed').length;

  return (
    <>
      <div className="kpi-grid kpi-grid-2">
        <BigKpi
          label="Ratings taught"
          value={String(detail.perRating.length)}
          sub={detail.perRating.map((p) => p.rating).join(', ') || '—'}
        />
        <BigKpi
          label="Students at checkride"
          value={String(studentsAtCheckride)}
          sub={`Total hours flown: ${totalHours.toFixed(1)}`}
        />
      </div>

      <div className="section-head">
        <h2 className="section-title">Efficiency vs cohort</h2>
      </div>
      <div className="card table-card">
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th>Rating</th>
                <th className="num">Students</th>
                <th className="num">Med hrs</th>
                <th className="num">Med cost</th>
                <th className="num">Med days</th>
              </tr>
            </thead>
            <tbody>
              {detail.perRating.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">
                      <div className="empty-title">No completed ratings yet</div>
                      <div className="empty-sub">
                        Students under this instructor haven't reached checkride.
                      </div>
                    </div>
                  </td>
                </tr>
              )}
              {detail.perRating.map((p) => (
                <tr key={p.rating}>
                  <td>
                    <span className="rating-chip">{p.rating}</span>
                  </td>
                  <td className="num">{p.n}</td>
                  <td className="num">{p.medianHrs.toFixed(1)}</td>
                  <td className="num">{fmtCost(p.medianCost)}</td>
                  <td className="num">{Math.round(p.medianDays).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-head">
        <h2 className="section-title">Student roster</h2>
      </div>
      <div className="card table-card">
        <div className="table-wrap" style={{ maxHeight: 480 }}>
          <table className="dt">
            <thead>
              <tr>
                <th>Student</th>
                <th>Rating</th>
                <th className="num">Hours</th>
                <th className="num">Days enrolled</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {detail.students.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <div className="empty">
                      <div className="empty-title">No students assigned</div>
                    </div>
                  </td>
                </tr>
              )}
              {detail.students.map((row) => (
                <tr key={`${row.id}-${row.rating}`}>
                  <td>{row.name}</td>
                  <td>
                    <span className="rating-chip">{row.rating}</span>
                  </td>
                  <td className="num">{row.hoursToDate.toFixed(1)}</td>
                  <td className="num">{row.daysEnrolled}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
