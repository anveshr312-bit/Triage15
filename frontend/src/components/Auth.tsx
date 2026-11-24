import { useState } from 'react';
import { supabase } from '../supabase';

interface AuthProps {
  onAuthSuccess: () => void;
}

export function Auth({ onAuthSuccess }: AuthProps) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setLoading(true);

    try {
      if (isSignUp) {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName.trim() || undefined,
            },
          },
        });

        if (signUpError) throw signUpError;

        if (data.session) {
          onAuthSuccess();
        } else {
          setNotice(
            'Registration successful! Please check your email inbox to confirm your account before signing in.'
          );
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (signInError) throw signInError;
        onAuthSuccess();
      }
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper" style={{ maxWidth: '440px', margin: '48px auto', padding: '0 16px' }}>
      <section className="card" style={{ padding: '32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2 style={{ margin: '0 0 8px 0', fontSize: '1.5rem' }}>
            {isSignUp ? 'Create your Account' : 'Sign in to Triage15'}
          </h2>
          <p style={{ margin: 0, color: 'var(--text-muted, #666)', fontSize: '0.9rem' }}>
            {isSignUp
              ? 'Join peer problem-solving and mentoring sessions'
              : 'Enter your credentials to access your peer workspace'}
          </p>
        </div>

        {error && (
          <div role="alert" className="error" style={{ marginBottom: '16px', padding: '10px 14px' }}>
            {error}
          </div>
        )}

        {notice && (
          <div role="status" className="success" style={{ marginBottom: '16px', padding: '10px 14px' }}>
            {notice}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {isSignUp && (
            <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span>Full Name</span>
              <input
                type="text"
                placeholder="Alex Morgan"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required={isSignUp}
                disabled={loading}
              />
            </label>
          )}

          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span>Email Address</span>
            <input
              type="email"
              placeholder="alex@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              autoComplete="email"
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span>Password</span>
            <input
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              disabled={loading}
              autoComplete={isSignUp ? 'new-password' : 'current-password'}
            />
          </label>

          <button
            type="submit"
            className="primary"
            disabled={loading}
            style={{ width: '100%', marginTop: '8px', padding: '10px' }}
          >
            {loading ? 'Authenticating…' : isSignUp ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '0.875rem' }}>
          {isSignUp ? (
            <span>
              Already registered?{' '}
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setIsSignUp(false);
                  setError(null);
                  setNotice(null);
                }}
                style={{ background: 'none', border: 'none', color: 'var(--primary, #2563eb)', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
              >
                Sign in here
              </button>
            </span>
          ) : (
            <span>
              Don't have an account?{' '}
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setIsSignUp(true);
                  setError(null);
                  setNotice(null);
                }}
                style={{ background: 'none', border: 'none', color: 'var(--primary, #2563eb)', cursor: 'pointer', padding: 0, textDecoration: 'underline' }}
              >
                Create one now
              </button>
            </span>
          )}
        </div>

        <div style={{ marginTop: '24px', borderTop: '1px solid var(--border, #e5e7eb)', paddingTop: '16px', fontSize: '0.78rem', color: 'var(--text-muted, #777)', textAlign: 'center' }}>
          Secured with Supabase Auth & ES256 Asymmetric JWT Verification
        </div>
      </section>
    </div>
  );
}
