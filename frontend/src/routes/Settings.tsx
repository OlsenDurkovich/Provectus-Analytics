// Account settings — self-service for any logged-in user (admin/viewer/student/
// instructor). Edit display name, email, phone, theme, and password.
import { useEffect, useState, type CSSProperties, type FormEvent } from 'react';
import { useAuth } from '../auth/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { useUpdateProfile, useChangePassword } from '../data/queries';
import { ApiError } from '../data/client';

function humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const p = JSON.parse(err.body) as { detail?: string; error?: string };
      return p.detail || p.error || err.body;
    } catch {
      return err.body || `Error ${err.status}`;
    }
  }
  return 'Something went wrong';
}

const input: CSSProperties = {
  padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border, #2a2a2a)',
  background: 'var(--bg-elev, transparent)', color: 'inherit', width: '100%',
};
const label: CSSProperties = { fontSize: 12, color: 'var(--fg-dim)', marginBottom: 4, display: 'block' };
const card: CSSProperties = {
  border: '1px solid var(--border, #2a2a2a)', borderRadius: 8, padding: 18,
  display: 'grid', gap: 14, marginBottom: 18, maxWidth: 460,
};

export default function Settings() {
  const { user, refreshUser } = useAuth();
  const { theme, setTheme } = useTheme();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();

  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [profileMsg, setProfileMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // Hydrate from the current user once it's available.
  useEffect(() => {
    if (!user) return;
    setDisplayName(user.display_name ?? '');
    setEmail(user.email ?? '');
    setPhone(user.phone ?? '');
  }, [user]);

  const saveProfile = (e: FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    updateProfile.mutate(
      { display_name: displayName, email, phone },
      {
        onSuccess: async () => {
          await refreshUser();
          setProfileMsg({ ok: true, text: 'Saved.' });
        },
        onError: (err) => setProfileMsg({ ok: false, text: humanizeError(err) }),
      },
    );
  };

  const pickTheme = (t: 'dark' | 'light') => {
    setTheme(t);
    updateProfile.mutate({ theme: t }, { onSuccess: () => void refreshUser() });
  };

  // password section
  const [curPw, setCurPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const savePassword = (e: FormEvent) => {
    e.preventDefault();
    setPwMsg(null);
    changePassword.mutate(
      { current_password: curPw, new_password: newPw },
      {
        onSuccess: () => {
          setPwMsg({ ok: true, text: 'Password changed.' });
          setCurPw('');
          setNewPw('');
        },
        onError: (err) => setPwMsg({ ok: false, text: humanizeError(err) }),
      },
    );
  };

  const Msg = ({ m }: { m: { ok: boolean; text: string } | null }) =>
    m ? (
      <div style={{ fontSize: 13, color: m.ok ? 'var(--positive, #16A34A)' : 'var(--danger, #e5484d)' }}>
        {m.text}
      </div>
    ) : null;

  return (
    <div style={{ padding: 24, maxWidth: 720 }}>
      <h1 style={{ fontSize: 20, marginBottom: 4 }}>Account settings</h1>
      <p style={{ color: 'var(--fg-dim)', marginTop: 0, fontSize: 13 }}>
        Update your profile, theme, and password. Your display name shows across the app instead of your email.
      </p>

      <form onSubmit={saveProfile} style={card}>
        <strong style={{ fontSize: 14 }}>Profile</strong>
        <div>
          <span style={label}>Display name</span>
          <input style={input} value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="e.g. Olsen Durkovich" />
        </div>
        <div>
          <span style={label}>Email</span>
          <input style={input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <span style={label}>Phone</span>
          <input style={input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="optional" />
        </div>
        <Msg m={profileMsg} />
        <div>
          <button className="btn btn-outline" type="submit" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? 'Saving…' : 'Save profile'}
          </button>
        </div>
      </form>

      <div style={card}>
        <strong style={{ fontSize: 14 }}>Theme</strong>
        <div style={{ display: 'flex', gap: 10 }}>
          {(['dark', 'light'] as const).map((t) => (
            <button
              key={t}
              type="button"
              className={'btn ' + (theme === t ? 'btn-primary' : 'btn-outline')}
              onClick={() => pickTheme(t)}
            >
              {t === 'dark' ? 'Dark' : 'Light'}
            </button>
          ))}
        </div>
        <div style={{ fontSize: 11, color: 'var(--fg-dim)' }}>Saved to your account and applied everywhere you sign in.</div>
      </div>

      <form onSubmit={savePassword} style={card}>
        <strong style={{ fontSize: 14 }}>Password</strong>
        <div>
          <span style={label}>Current password</span>
          <input style={input} type="password" value={curPw} onChange={(e) => setCurPw(e.target.value)} required />
        </div>
        <div>
          <span style={label}>New password (min 8)</span>
          <input style={input} type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8} />
        </div>
        <Msg m={pwMsg} />
        <div>
          <button className="btn btn-outline" type="submit" disabled={changePassword.isPending || newPw.length < 8}>
            {changePassword.isPending ? 'Changing…' : 'Change password'}
          </button>
        </div>
      </form>
    </div>
  );
}
