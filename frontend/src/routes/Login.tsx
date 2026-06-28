// Login page — single form, no register / forgot-password flows.
//
// Intentionally minimal: 2-3 users, all provisioned via INITIAL_ADMIN_EMAIL /
// INITIAL_ADMIN_PASSWORD on first boot. Account management is out of scope for
// the migration.

import { useState } from 'react';
import { useAuth, LoginFailure } from '../auth/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password, remember);
    } catch (err) {
      if (err instanceof LoginFailure) {
        if (err.status === 401) setError('Invalid email or password.');
        else if (err.status === 429) setError('Too many attempts — try again in a minute.');
        else setError(err.message);
      } else {
        setError('Network error — please retry.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={onSubmit} aria-label="Sign in">
        <div className="login-brand">Provectus Analytics</div>
        <div className="login-sub">Sign in to continue</div>

        <label className="login-field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>

        <label className="login-field">
          <span>Password</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        <label className="login-remember">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
          />
          <span>Keep me signed in</span>
        </label>

        {error && <div className="login-error" role="alert">{error}</div>}

        <button
          type="submit"
          className="btn btn-primary login-submit"
          disabled={submitting || !email || !password}
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
