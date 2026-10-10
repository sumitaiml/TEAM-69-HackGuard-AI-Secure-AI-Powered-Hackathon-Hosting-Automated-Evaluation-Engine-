import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { api, ApiError, formatApiError } from '../lib/apiClient';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/auth/reset-password/${token}`, { new_password: newPassword });
      setDone(true);
    } catch (e) {
      setError(e instanceof ApiError ? formatApiError(e.detail) : 'Could not reset your password.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#FFFFFF' }}>
      <div style={{ padding: '40px', width: '100%', maxWidth: '440px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
          <div style={{ background: '#18191C', color: '#FDF8E2', width: '38px', height: '38px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '18px' }}>⚡</div>
          <span style={{ fontSize: '18px', fontWeight: 800 }}>HackEval</span>
        </div>

        {!token && (
          <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '14px', borderRadius: '12px', fontSize: '13px', fontWeight: 600 }}>
            No reset token was provided in the link.
          </div>
        )}

        {token && done && (
          <>
            <h2 style={{ fontSize: '22px', fontWeight: 800, marginBottom: '6px' }}>Password reset</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Your password has been updated. You can sign in with it now.
            </p>
            <Link to="/login" style={{ fontSize: '13px', fontWeight: 700, color: '#2B7FFF' }}>Back to Sign In →</Link>
          </>
        )}

        {token && !done && (
          <>
            <h2 style={{ fontSize: '22px', fontWeight: 800, marginBottom: '6px' }}>Set a new password</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Choose a new password for your account.
            </p>

            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 800, color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>New Password</label>
                <input type="password" required minLength={6} className="search-input" style={{ width: '100%' }} value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </div>

              {error && (
                <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '10px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: 600, marginBottom: '16px' }}>
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{ width: '100%', background: '#18191C', color: '#FFFFFF', border: 'none', borderRadius: '99px', padding: '14px', fontSize: '15px', fontWeight: 700, cursor: submitting ? 'default' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', opacity: submitting ? 0.7 : 1 }}
              >
                {submitting ? 'Saving…' : 'Reset Password'} <ArrowRight size={18} />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};
