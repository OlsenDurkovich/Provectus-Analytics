// Self-service password change, available to any logged-in user.
import { useState, type FormEvent, type CSSProperties } from 'react';
import { useChangePassword } from '../data/queries';
import { ApiError } from '../data/client';

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

const backdrop: CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};
const modal: CSSProperties = {
  background: 'var(--bg, #16161a)',
  color: 'inherit',
  border: '1px solid var(--border, #2a2a2a)',
  borderRadius: 10,
  padding: 24,
  width: 360,
  maxWidth: '90vw',
};
const input: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 6,
  border: '1px solid var(--border, #2a2a2a)',
  background: 'var(--bg-elev, transparent)',
  color: 'inherit',
};

export function ChangePasswordDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const mut = useChangePassword();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  if (!open) return null;

  const close = () => {
    setCurrent('');
    setNext('');
    setError(null);
    setDone(false);
    onClose();
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    mut.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setDone(true);
          setCurrent('');
          setNext('');
        },
        onError: (err) => setError(humanizeError(err)),
      },
    );
  };

  return (
    <div style={backdrop} onClick={close}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ marginTop: 0, fontSize: 16 }}>Change password</h2>
        {done ? (
          <>
            <p style={{ fontSize: 13 }}>Your password has been updated.</p>
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-outline" type="button" onClick={close}>
                Close
              </button>
            </div>
          </>
        ) : (
          <form onSubmit={submit} style={{ display: 'grid', gap: 10 }}>
            <input
              style={input}
              type="password"
              placeholder="current password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
            <input
              style={input}
              type="password"
              placeholder="new password (min 8 characters)"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              minLength={8}
            />
            {error && (
              <div style={{ color: 'var(--danger, #e5484d)', fontSize: 13 }}>{error}</div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn btn-outline" type="button" onClick={close}>
                Cancel
              </button>
              <button className="btn btn-outline" type="submit" disabled={mut.isPending}>
                {mut.isPending ? 'Saving…' : 'Update'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
