// Admin-only user management screen. The API enforces admin access too;
// App.tsx also guards the route so non-admins are redirected away.
import { useState, type FormEvent, type CSSProperties } from 'react';
import { useUsers, useCreateUser, useUpdateUser } from '../data/queries';
import { ApiError } from '../data/client';
import type { UserRole } from '../data/types';

const ROLES: UserRole[] = ['admin', 'instructor', 'viewer'];

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

const cell: CSSProperties = {
  textAlign: 'left',
  padding: '8px 10px',
  borderBottom: '1px solid var(--border, #2a2a2a)',
  fontSize: 13,
};
const input: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid var(--border, #2a2a2a)',
  background: 'var(--bg-elev, transparent)',
  color: 'inherit',
};

export default function Users() {
  const users = useUsers();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('viewer');
  const [createError, setCreateError] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setCreateError(null);
    createUser.mutate(
      { email, password, role },
      {
        onSuccess: () => {
          setEmail('');
          setPassword('');
          setRole('viewer');
        },
        onError: (err) => setCreateError(humanizeError(err)),
      },
    );
  };

  const patch = (id: number, body: { role?: string; is_active?: boolean }) => {
    setRowError(null);
    updateUser.mutate({ id, patch: body }, { onError: (err) => setRowError(humanizeError(err)) });
  };

  return (
    <div style={{ maxWidth: 760 }}>
      <h1 style={{ fontSize: 20, marginBottom: 4 }}>Users</h1>
      <p style={{ color: 'var(--fg-dim, #888)', marginTop: 0, fontSize: 13 }}>
        Manage who can sign in and what they can do. Admins manage everything;
        instructors and viewers are read-only.
      </p>

      <form
        onSubmit={submit}
        style={{ display: 'grid', gap: 10, maxWidth: 380, margin: '20px 0 28px' }}
      >
        <strong style={{ fontSize: 14 }}>Add a user</strong>
        <input
          style={input}
          type="email"
          placeholder="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          style={input}
          type="password"
          placeholder="password (min 8 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
        <select
          style={input}
          value={role}
          onChange={(e) => setRole(e.target.value as UserRole)}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {createError && (
          <div style={{ color: 'var(--danger, #e5484d)', fontSize: 13 }}>{createError}</div>
        )}
        <button className="btn btn-outline" type="submit" disabled={createUser.isPending}>
          {createUser.isPending ? 'Adding…' : 'Add user'}
        </button>
      </form>

      {users.isLoading && <div>Loading…</div>}
      {users.isError && <div>Couldn’t load users.</div>}
      {users.data && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={cell}>Email</th>
              <th style={cell}>Role</th>
              <th style={cell}>Status</th>
              <th style={cell}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.data.map((u) => (
              <tr key={u.user_id}>
                <td style={cell}>{u.email}</td>
                <td style={cell}>
                  <select
                    style={input}
                    value={u.role}
                    onChange={(e) => patch(u.user_id, { role: e.target.value })}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td style={cell}>{u.is_active ? 'Active' : 'Inactive'}</td>
                <td style={cell}>
                  <button
                    className="btn btn-outline"
                    type="button"
                    onClick={() => patch(u.user_id, { is_active: !u.is_active })}
                  >
                    {u.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {rowError && (
        <div style={{ color: 'var(--danger, #e5484d)', marginTop: 10, fontSize: 13 }}>
          {rowError}
        </div>
      )}
    </div>
  );
}
