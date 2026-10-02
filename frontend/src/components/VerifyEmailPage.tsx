import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api, ApiError, formatApiError } from '../lib/apiClient';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token was provided in the link.');
      return;
    }
    api
      .get<{ message: string }>(`/api/auth/verify/${token}`)
      .then((res) => {
        setStatus('success');
        setMessage(res.message);
      })
      .catch((e) => {
        setStatus('error');
        setMessage(e instanceof ApiError ? formatApiError(e.detail) : 'Could not verify this email address.');
      });
  }, [token]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--canvas-bg)', padding: '24px' }}>
      <div style={{ background: '#FFFFFF', borderRadius: '32px', boxShadow: '0 20px 60px rgba(0,0,0,0.06)', border: '1px solid rgba(229, 231, 235, 0.8)', padding: '40px', width: '440px', maxWidth: '100%', textAlign: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', marginBottom: '24px' }}>
          <div style={{ background: '#18191C', color: '#FDF8E2', width: '38px', height: '38px', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: '18px' }}>⚡</div>
          <span style={{ fontSize: '18px', fontWeight: 800 }}>HackGuard AI</span>
        </div>

        {status === 'loading' && <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Verifying your email…</p>}

        {status !== 'loading' && (
          <div style={{
            background: status === 'success' ? '#E6F7F0' : '#FEE2E2',
            color: status === 'success' ? '#10B981' : '#991B1B',
            padding: '14px', borderRadius: '12px', fontSize: '13px', fontWeight: 600, marginBottom: '20px',
          }}>
            {message}
          </div>
        )}

        <Link to="/" style={{ fontSize: '13px', fontWeight: 700, color: '#2B7FFF' }}>Go to Dashboard →</Link>
      </div>
    </div>
  );
};
