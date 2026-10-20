import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Lock, Mail, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError, formatApiError, API_BASE_URL, setToken } from '../lib/apiClient';
import type { AuthUser } from '../lib/types';

// Crisp official brand icons
const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path
      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
      fill="#4285F4"
    />
    <path
      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
      fill="#34A853"
    />
    <path
      d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.04 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      fill="#FBBC05"
    />
    <path
      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      fill="#EA4335"
    />
  </svg>
);

const GitHubIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="#24292F" xmlns="http://www.w3.org/2000/svg">
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"
    />
  </svg>
);

// Judges don't self-register - they accept an invite from an organizer
// (see AcceptInvitePage) - so signup only ever offers these two roles.
const SELF_REGISTERABLE_ROLES = ['participant', 'organizer'] as const;

export const LoginPage: React.FC = () => {
  const { login, register, setSession } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [selectedRole, setSelectedRole] = useState<'participant' | 'organizer'>('participant');
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

  useEffect(() => {
    const oauthError = searchParams.get('oauth_error');
    const token = searchParams.get('token');

    if (oauthError) {
      setError(oauthError);
    } else if (token) {
      setIsSubmitting(true);
      setToken(token);
      api
        .get<AuthUser>('/api/auth/me')
        .then((user) => {
          setSession(token, user);
          navigate('/', { replace: true });
        })
        .catch(() => {
          setToken(null);
          setError('Failed to retrieve account details after social login.');
        })
        .finally(() => {
          setIsSubmitting(false);
        });
    }
  }, [searchParams, setSession, navigate]);

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/auth/oauth/google`;
  };

  const handleGitHubLogin = () => {
    window.location.href = `${API_BASE_URL}/api/auth/oauth/github`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      if (mode === 'forgot') {
        await api.post('/api/auth/forgot-password', { email });
        setForgotSubmitted(true);
      } else if (mode === 'signin') {
        await login(email, password);
        navigate('/');
      } else {
        await register(email, password, fullName, selectedRole);
        navigate('/');
      }
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err.detail, 'Incorrect email or password') : 'Could not connect to the server.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const switchMode = (next: 'signin' | 'signup' | 'forgot') => {
    setMode(next);
    setError(null);
    setForgotSubmitted(false);
  };

  return (
    <div style={{
      minHeight: '100vh',
      width: '100%',
      backgroundColor: '#FFFFFF',
      display: 'grid',
      gridTemplateColumns: '480px 1fr',
    }}>
      {/* Left Dark Panel */}
        <div style={{
          backgroundColor: '#18191C',
          color: '#FFFFFF',
          padding: '40px 36px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative'
        }}>
          <div>
            {/* Top Brand Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '40px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                  background: '#FDF8E2',
                  color: '#18191C',
                  width: '38px',
                  height: '38px',
                  borderRadius: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: '800',
                  fontSize: '18px'
                }}>
                  ⚡
                </div>
                <span style={{ fontSize: '18px', fontWeight: '800' }}>HackEval</span>
              </div>
              <span className="pill-badge" style={{ background: 'rgba(255,255,255,0.1)', color: '#9CA3AF' }}>v1.0 Live</span>
            </div>

            {/* Main Headline */}
            <h2 style={{ fontSize: '32px', fontWeight: '800', lineHeight: '1.25', marginBottom: '16px' }}>
              Automated AI Hackathon Engine
            </h2>
            <p style={{ fontSize: '14px', color: '#9CA3AF', lineHeight: '1.6', marginBottom: '36px' }}>
              Secure code execution, AST plagiarism detection, static security analysis, and dynamic leaderboards in one unified hub.
            </p>

            {/* Two Mini Preview Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ background: '#F0EBF9', padding: '16px', borderRadius: '16px', color: '#18191C' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: '#8B5CF6', textTransform: 'uppercase' }}>AI Score</div>
                <div style={{ fontSize: '20px', fontWeight: '800', margin: '4px 0' }}>88.5 / 100</div>
                <div style={{ fontSize: '11px', color: '#10B981', fontWeight: '700' }}>+2.4% Yield</div>
              </div>

              <div style={{ background: '#E6F7F0', padding: '16px', borderRadius: '16px', color: '#18191C' }}>
                <div style={{ fontSize: '11px', fontWeight: '700', color: '#10B981', textTransform: 'uppercase' }}>Plagiarism</div>
                <div style={{ fontSize: '20px', fontWeight: '800', margin: '4px 0' }}>0.2% Low</div>
                <div style={{ fontSize: '11px', color: '#10B981', fontWeight: '700' }}>Passed AST</div>
              </div>
            </div>
          </div>

          {/* Left Footer Badges */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px', color: '#9CA3AF', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ color: '#10B981' }}>●</span> Docker Sandbox Isolated
            </span>
            <span>SOC2 Type II</span>
          </div>
        </div>

        {/* Right Light Form Panel */}
        <div style={{ padding: '40px 48px', display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%', maxWidth: '560px', width: '100%', margin: '0 auto' }}>
          <div style={{ width: '100%' }}>
            {/* Header Controls */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
              {mode !== 'forgot' && (
                <div style={{ background: '#F3F4F6', borderRadius: '99px', padding: '4px', display: 'flex' }}>
                  <button
                    type="button"
                    onClick={() => switchMode('signin')}
                    style={{
                      border: 'none',
                      background: mode === 'signin' ? '#FFFFFF' : 'transparent',
                      color: mode === 'signin' ? '#111827' : '#6B7280',
                      padding: '8px 20px',
                      borderRadius: '99px',
                      fontSize: '14px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      boxShadow: mode === 'signin' ? '0 2px 6px rgba(0,0,0,0.05)' : 'none',
                      transition: 'all 0.2s'
                    }}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={() => switchMode('signup')}
                    style={{
                      border: 'none',
                      background: mode === 'signup' ? '#FFFFFF' : 'transparent',
                      color: mode === 'signup' ? '#111827' : '#6B7280',
                      padding: '8px 20px',
                      borderRadius: '99px',
                      fontSize: '14px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      boxShadow: mode === 'signup' ? '0 2px 6px rgba(0,0,0,0.05)' : 'none',
                      transition: 'all 0.2s'
                    }}
                  >
                    Create Account
                  </button>
                </div>
              )}

              <span style={{ fontSize: '13px', color: '#6B7280', cursor: 'pointer', fontWeight: '600' }}>
                Help & Support &gt;
              </span>
            </div>

            {/* Welcome Heading */}
            <h2 style={{ fontSize: '26px', fontWeight: '800', marginBottom: '6px' }}>
              {mode === 'signin' ? 'Welcome back' : mode === 'signup' ? 'Create your account' : 'Reset your password'}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              {mode === 'signin'
                ? 'Access your real-time hackathon evaluation reports, dashboards, and leaderboards.'
                : mode === 'signup'
                ? 'Judges are invited by an organizer, not registered here - pick participant or organizer.'
                : "Enter your account's email and we'll send you a link to reset your password."}
            </p>

            {/* Form */}
            {mode === 'forgot' && forgotSubmitted ? (
              <div>
                <div style={{ background: '#E6F7F0', color: '#10B981', padding: '14px', borderRadius: '12px', fontSize: '13px', fontWeight: 600, marginBottom: '20px' }}>
                  If an account with that email exists, a password reset link has been sent.
                </div>
                <button type="button" onClick={() => switchMode('signin')} style={{ background: 'none', border: 'none', color: '#2B7FFF', fontSize: '13px', fontWeight: 700, cursor: 'pointer' }}>
                  ← Back to Sign In
                </button>
              </div>
            ) : (
            <form onSubmit={handleSubmit}>
              {mode === 'signup' && (
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Full Name</label>
                  <input
                    type="text"
                    required
                    className="search-input"
                    style={{ width: '100%' }}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
              )}

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Email Address</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="email"
                    required
                    className="search-input"
                    style={{ width: '100%', paddingRight: '36px' }}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Mail size={16} style={{ position: 'absolute', right: '14px', top: '12px', color: '#9CA3AF' }} />
                </div>
              </div>

              {mode !== 'forgot' && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <label style={{ fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase' }}>Password</label>
                    {mode === 'signin' && (
                      <button type="button" onClick={() => switchMode('forgot')} style={{ background: 'none', border: 'none', color: '#2B7FFF', fontSize: '12px', fontWeight: 700, cursor: 'pointer', padding: 0 }}>
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="password"
                      required
                      minLength={6}
                      className="search-input"
                      style={{ width: '100%', paddingRight: '36px' }}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <Lock size={16} style={{ position: 'absolute', right: '14px', top: '12px', color: '#9CA3AF' }} />
                  </div>
                </div>
              )}

              {/* Role Selection - signup only, and judges are excluded (invite-only) */}
              {mode === 'signup' && (
                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '8px' }}>Select Account Role</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {SELF_REGISTERABLE_ROLES.map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setSelectedRole(r)}
                        style={{
                          border: selectedRole === r ? '2px solid #2B7FFF' : '1px solid #E5E7EB',
                          background: selectedRole === r ? '#E8F2FF' : '#FFFFFF',
                          color: selectedRole === r ? '#2B7FFF' : '#374151',
                          borderRadius: '10px',
                          padding: '8px',
                          fontSize: '12px',
                          fontWeight: '700',
                          cursor: 'pointer',
                          textTransform: 'capitalize'
                        }}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Remember Me */}
              {mode === 'signin' && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer', color: '#374151' }}>
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      style={{ accentColor: '#18191C' }}
                    />
                    Remember this device
                  </label>
                </div>
              )}

              {error && (
                <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '10px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: 600, marginBottom: '16px' }}>
                  {error}
                </div>
              )}

              {/* Main Submit Pill Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  width: '100%',
                  background: '#18191C',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '99px',
                  padding: '14px',
                  fontSize: '15px',
                  fontWeight: '700',
                  cursor: isSubmitting ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'background 0.2s',
                  opacity: isSubmitting ? 0.7 : 1,
                }}
              >
                {isSubmitting
                  ? 'Please wait…'
                  : mode === 'signin'
                  ? 'Sign In to Dashboard'
                  : mode === 'signup'
                  ? 'Create Account'
                  : 'Send Reset Link'} <ArrowRight size={18} />
              </button>

              {/* Divider and OAuth Social Login Options */}
              {mode !== 'forgot' && (
                <>
                  <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0 16px', gap: '12px' }}>
                    <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
                    <span style={{ fontSize: '11px', fontWeight: '700', color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      OR
                    </span>
                    <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <button
                      type="button"
                      onClick={handleGoogleLogin}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        background: '#FFFFFF',
                        color: '#374151',
                        border: '1px solid #E5E7EB',
                        borderRadius: '99px',
                        padding: '12px',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: isSubmitting ? 'default' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '10px',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                        transition: 'all 0.2s',
                        opacity: isSubmitting ? 0.7 : 1,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#F9FAFB';
                        e.currentTarget.style.borderColor = '#D1D5DB';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#FFFFFF';
                        e.currentTarget.style.borderColor = '#E5E7EB';
                      }}
                    >
                      <GoogleIcon />
                      Continue with Google
                    </button>

                    <button
                      type="button"
                      onClick={handleGitHubLogin}
                      disabled={isSubmitting}
                      style={{
                        width: '100%',
                        background: '#FFFFFF',
                        color: '#374151',
                        border: '1px solid #E5E7EB',
                        borderRadius: '99px',
                        padding: '12px',
                        fontSize: '14px',
                        fontWeight: '600',
                        cursor: isSubmitting ? 'default' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '10px',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                        transition: 'all 0.2s',
                        opacity: isSubmitting ? 0.7 : 1,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = '#F9FAFB';
                        e.currentTarget.style.borderColor = '#D1D5DB';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#FFFFFF';
                        e.currentTarget.style.borderColor = '#E5E7EB';
                      }}
                    >
                      <GitHubIcon />
                      Continue with GitHub
                    </button>
                  </div>
                </>
              )}
            </form>
            )}
          </div>

          {/* Footer Links */}
          <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#9CA3AF', justifyContent: 'center', marginTop: '20px' }}>
            <span>© 2026 HackEval</span>
          </div>
        </div>
    </div>
  );
};

