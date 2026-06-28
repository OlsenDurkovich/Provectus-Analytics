// Admin-only user management. The API enforces admin access + page access too;
// App.tsx guards the route so non-admins are redirected away.
import { useState, type FormEvent, type CSSProperties } from 'react';
import {
  useUsers, useCreateUser, useUpdateUser, useStudentRecords, useInstructorRecords,
} from '../data/queries';
import { ApiError } from '../data/client';
import {
  ALL_PAGES, type InstructorRecord, type StudentRecord, type UserRole, type UserRow,
} from '../data/types';

const ROLES: UserRole[] = ['admin', 'instructor', 'viewer', 'student'];

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.body) as { detail?: string; error?: string };
      return parsed.detail || parsed.error || err.body;
    } catch {
      return err.body || `Error ${err.status}`;
    }
  }
  return 'Something went wrong';
}

const input: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid var(--border, #2a2a2a)',
  background: 'var(--bg-elev, transparent)',
  color: 'inherit',
};
const card: CSSProperties = {
  border: '1px solid var(--border, #2a2a2a)',
  borderRadius: 8,
  padding: 14,
  display: 'grid',
  gap: 12,
};

type UpdateBody = {
  role?: string;
  is_active?: boolean;
  pages?: string[];
  new_password?: string;
  student_id?: number | null;
  instructor_name?: string | null;
};

function UserCard({
  u,
  onPatch,
  busy,
  records,
  instructors,
}: {
  u: UserRow;
  onPatch: (id: number, body: UpdateBody) => void;
  busy: boolean;
  records: StudentRecord[];
  instructors: InstructorRecord[];
}) {
  const [pw, setPw] = useState('');

  const togglePage = (key: string) => {
    const next = u.pages.includes(key)
      ? u.pages.filter((p) => p !== key)
      : [...u.pages, key];
    onPatch(u.user_id, { pages: next });
  };

  return (
    <div style={{ ...card, opacity: u.is_active ? 1 : 0.6 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 14 }}>
          {u.email}
          {!u.is_active && (
            <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--fg-dim)' }}>(inactive)</span>
          )}
        </strong>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select style={input} value={u.role} onChange={(e) => onPatch(u.user_id, { role: e.target.value })}>
            {ROLES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
          <button className="btn btn-outline" type="button" onClick={() => onPatch(u.user_id, { is_active: !u.is_active })}>
            {u.is_active ? 'Deactivate' : 'Reactivate'}
          </button>
        </div>
      </div>

      {u.role === 'student' ? (
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-dim)', marginBottom: 6 }}>
            Linked training record
          </div>
          <select
            style={{ ...input, maxWidth: 280 }}
            value={u.student_id ?? ''}
            disabled={busy}
            onChange={(e) =>
              e.target.value && onPatch(u.user_id, { student_id: Number(e.target.value) })
            }
          >
            <option value="" disabled>
              {u.student_id == null ? 'Pick a student…' : 'Change linked student…'}
            </option>
            {records.map((r) => (
              <option key={r.student_id} value={r.student_id}>
                {r.name}
                {r.email ? ` · ${r.email}` : ''}
              </option>
            ))}
          </select>
          <div style={{ fontSize: 11, color: 'var(--fg-dim)', marginTop: 4 }}>
            Student accounts see only their own training — no other pages or people.
          </div>
        </div>
      ) : u.role === 'instructor' ? (
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-dim)', marginBottom: 6 }}>
            Linked instructor
          </div>
          <select
            style={{ ...input, maxWidth: 280 }}
            value={u.instructor_name ?? ''}
            disabled={busy}
            onChange={(e) =>
              e.target.value && onPatch(u.user_id, { instructor_name: e.target.value })
            }
          >
            <option value="" disabled>
              {u.instructor_name == null ? 'Pick an instructor…' : 'Change linked instructor…'}
            </option>
            {instructors.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name} · {r.students} students
              </option>
            ))}
          </select>
          <div style={{ fontSize: 11, color: 'var(--fg-dim)', marginTop: 4 }}>
            Instructors see only their own students' progress — no cost, no other people.
          </div>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 12, color: 'var(--fg-dim)', marginBottom: 6 }}>Pages this user can see</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {ALL_PAGES.map((p) => (
              <label
                key={p.key}
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, opacity: u.is_admin ? 0.6 : 1 }}
              >
                <input
                  type="checkbox"
                  checked={u.is_admin || u.pages.includes(p.key)}
                  disabled={u.is_admin || busy}
                  onChange={() => togglePage(p.key)}
                />
                {p.label}
              </label>
            ))}
          </div>
          {u.is_admin && (
            <div style={{ fontSize: 11, color: 'var(--fg-dim)', marginTop: 4 }}>
              Admins can see every page and manage users.
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          style={{ ...input, flex: 1, maxWidth: 240 }}
          type="password"
          placeholder="set a new password (min 8)"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          minLength={8}
        />
        <button
          className="btn btn-outline"
          type="button"
          disabled={pw.length < 8 || busy}
          onClick={() => {
            onPatch(u.user_id, { new_password: pw });
            setPw('');
          }}
        >
          Reset password
        </button>
      </div>
    </div>
  );
}

export default function Users() {
  const users = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const studentRecords = useStudentRecords();
  const records = studentRecords.data ?? [];
  const instructorRecords = useInstructorRecords();
  const instructors = instructorRecords.data ?? [];

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('viewer');
  const [studentId, setStudentId] = useState<string>('');
  const [instructorName, setInstructorName] = useState<string>('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    if (role === 'student' && !studentId) {
      setCreateError('Pick which student record this account belongs to.');
      return;
    }
    if (role === 'instructor' && !instructorName) {
      setCreateError('Pick which instructor this account belongs to.');
      return;
    }
    createUser.mutate(
      {
        email,
        password,
        role,
        student_id: role === 'student' ? Number(studentId) : undefined,
        instructor_name: role === 'instructor' ? instructorName : undefined,
      },
      {
        onSuccess: () => {
          setEmail('');
          setPassword('');
          setRole('viewer');
          setStudentId('');
          setInstructorName('');
        },
        onError: (err) => setCreateError(humanizeError(err)),
      },
    );
  };

  const patch = (id: number, body: UpdateBody) => {
    setRowError(null);
    updateUser.mutate({ id, patch: body }, { onError: (err) => setRowError(humanizeError(err)) });
  };

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 20, marginBottom: 4 }}>Users</h1>
      <p style={{ color: 'var(--fg-dim, #888)', marginTop: 0, fontSize: 13 }}>
        Manage accounts, roles, and exactly which pages each person can see. The
        role sets a starting point; tick or untick pages to fine-tune. Admins
        always have full access. A <strong>student</strong> account is linked to
        one training record; an <strong>instructor</strong> account is linked to
        one instructor and sees only their own students' progress (no cost).
      </p>

      <form onSubmit={submit} style={{ display: 'grid', gap: 10, maxWidth: 380, margin: '20px 0 28px' }}>
        <strong style={{ fontSize: 14 }}>Add a user</strong>
        <input style={input} type="email" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input
          style={input}
          type="password"
          placeholder="password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        <select style={input} value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          {ROLES.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        {role === 'student' && (
          <select
            style={input}
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            required
          >
            <option value="" disabled>
              {studentRecords.isLoading ? 'Loading students…' : 'Link to student record…'}
            </option>
            {records.map((r) => (
              <option key={r.student_id} value={r.student_id}>
                {r.name}
                {r.email ? ` · ${r.email}` : ''}
              </option>
            ))}
          </select>
        )}
        {role === 'instructor' && (
          <select
            style={input}
            value={instructorName}
            onChange={(e) => setInstructorName(e.target.value)}
            required
          >
            <option value="" disabled>
              {instructorRecords.isLoading ? 'Loading instructors…' : 'Link to instructor…'}
            </option>
            {instructors.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name} · {r.students} students
              </option>
            ))}
          </select>
        )}
        {createError && <div style={{ color: 'var(--danger, #e5484d)', fontSize: 13 }}>{createError}</div>}
        <button className="btn btn-outline" type="submit" disabled={createUser.isPending}>
          {createUser.isPending ? 'Adding…' : 'Add user'}
        </button>
      </form>

      {rowError && (
        <div style={{ color: 'var(--danger, #e5484d)', marginBottom: 12, fontSize: 13 }}>{rowError}</div>
      )}
      {users.isLoading && <div>Loading…</div>}
      {users.isError && <div>Couldn’t load users.</div>}
      {users.data && (
        <div style={{ display: 'grid', gap: 12 }}>
          {users.data.map((u: UserRow) => (
            <UserCard key={u.user_id} u={u} onPatch={patch} busy={updateUser.isPending} records={records} instructors={instructors} />
          ))}
        </div>
      )}
    </div>
  );
}
