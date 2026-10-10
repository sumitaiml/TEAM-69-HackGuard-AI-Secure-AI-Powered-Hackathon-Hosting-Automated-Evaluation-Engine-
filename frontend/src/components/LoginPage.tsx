import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api, ApiError, formatApiError } from '../lib/apiClient';

// Judges don't self-register - they accept an invite from an organizer
// (see AcceptInvitePage) - so signup only ever offers these two roles.
const SELF_REGISTERABLE_ROLES = ['participant', 'organizer'] as const;

export const LoginPage: React.FC = () => {
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [selectedRole, setSelectedRole] = useState<'participant' | 'organizer'>('participant');
  const [rememberMe, setRememberMe] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotSubmitted, setForgotSubmitted] = useState(false);

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

