// Confirmation gate for "Rebuild DB" — a heavy, irreversible action that
// regenerates the whole analytics database. Requires typing REBUILD so it can't
// be triggered by an accidental click (this once took prod down).
import { useEffect, useState, type CSSProperties } from 'react';

const CONFIRM_WORD = 'REBUILD';

const backdrop: CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
  display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
};
const modal: CSSProperties = {
  background: 'var(--bg-elev, #16161a)', color: 'inherit',
  border: '1px solid var(--border, #2a2a2a)', borderRadius: 10,
  padding: 22, width: 420, maxWidth: '92vw', display: 'grid', gap: 14,
};
const input: CSSProperties = {
  padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border, #2a2a2a)',
  background: 'var(--bg, transparent)', color: 'inherit', width: '100%',
};

type Props = {
  open: boolean;
  pending?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function RebuildConfirmDialog({ open, pending = false, onCancel, onConfirm }: Props) {
  const [typed, setTyped] = useState('');

  useEffect(() => {
    if (!open) setTyped('');
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pending) onCancel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, pending, onCancel]);

  if (!open) return null;
  const armed = typed.trim().toUpperCase() === CONFIRM_WORD;

  return (
    <div style={backdrop} onMouseDown={() => !pending && onCancel()}>
      <div style={modal} onMouseDown={(e) => e.stopPropagation()}>
        <strong style={{ fontSize: 15 }}>Rebuild the analytics database?</strong>
        <div style={{ fontSize: 13, color: 'var(--fg-muted)', lineHeight: 1.5 }}>
          This regenerates the entire analytics dataset from source. It can take up to
          a minute and <strong>discards any manual flight overrides</strong>. On synthetic
          data it resets the dashboard to the sample dataset. Your accounts and settings
          are <strong>not</strong> affected (separate database). This can't be undone.
        </div>
        <div>
          <label style={{ fontSize: 12, color: 'var(--fg-dim)', display: 'block', marginBottom: 4 }}>
            Type <strong>{CONFIRM_WORD}</strong> to confirm
          </label>
          <input
            style={input}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder={CONFIRM_WORD}
            autoFocus
            disabled={pending}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="btn btn-outline" type="button" onClick={onCancel} disabled={pending}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={onConfirm}
            disabled={!armed || pending}
          >
            {pending ? 'Rebuilding…' : 'Rebuild database'}
          </button>
        </div>
      </div>
    </div>
  );
}
