import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { api, ApiError, formatApiError } from '../lib/apiClient';
import { useAuth } from '../context/AuthContext';
import type { InviteDetails, AuthUser } from '../lib/types';

export const AcceptInvitePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setSession } = useAuth();
  const token = searchParams.get('token') || '';

  const [details, setDetails] = useState<InviteDetails | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoadError('No invite token was provided in the link.');
      return;
    }
    api
      .get<InviteDetails>(`/api/auth/invite/${token}`)
      .then(setDetails)
      .catch((e) => setLoadError(e instanceof ApiError ? formatApiError(e.detail) : 'This invite link is not valid.'));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const data = await api.post<{ access_token: string; user: AuthUser }>(`/api/auth/invite/${token}/accept`, {
        full_name: fullName,
        password,
      });
      setSession(data.access_token, data.user);
      navigate('/');
    } catch (e) {
      setSubmitError(e instanceof ApiError ? formatApiError(e.detail) : 'Could not accept this invite.');
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

        {loadError && (
          <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '14px', borderRadius: '12px', fontSize: '13px', fontWeight: 600 }}>
            {loadError}
          </div>
        )}

        {!loadError && !details && <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Loading invite details…</p>}

        {details && (
          <>
            <h2 style={{ fontSize: '22px', fontWeight: 800, marginBottom: '6px' }}>Judge invitation</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              You've been invited to judge <strong>{details.hackathon_title}</strong> as <strong>{details.email}</strong>. Set your name and a password to accept.
            </p>

            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 800, color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Full Name</label>
                <input type="text" required className="search-input" style={{ width: '100%' }} value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 800, color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Password</label>
                <input type="password" required minLength={6} className="search-input" style={{ width: '100%' }} value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>

              {submitError && (
                <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '10px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: 600, marginBottom: '16px' }}>
                  {submitError}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{ width: '100%', background: '#18191C', color: '#FFFFFF', border: 'none', borderRadius: '99px', padding: '14px', fontSize: '15px', fontWeight: 700, cursor: submitting ? 'default' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', opacity: submitting ? 0.7 : 1 }}
              >
                {submitting ? 'Accepting…' : 'Accept Invitation'} <ArrowRight size={18} />
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};
