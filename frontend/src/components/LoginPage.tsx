import { useState } from 'react';
import { Lock, Mail, ArrowRight } from 'lucide-react';

interface LoginPageProps {
  onLoginSuccess: (role: 'participant' | 'organizer' | 'judge', userEmail: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('participant@hackguard.ai');
  const [password, setPassword] = useState('password123');
  const [fullName, setFullName] = useState('Alice Dev');
  const [selectedRole, setSelectedRole] = useState<'participant' | 'organizer' | 'judge'>('participant');
  const [rememberMe, setRememberMe] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLoginSuccess(selectedRole, email);
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--canvas-bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px'
    }}>
      {/* Outer Card Container */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: '32px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.06)',
        border: '1px solid rgba(229, 231, 235, 0.8)',
        display: 'grid',
        gridTemplateColumns: '440px 520px',
        width: '960px',
        maxWidth: '100%',
        overflow: 'hidden'
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
                <span style={{ fontSize: '18px', fontWeight: '800' }}>HackGuard AI</span>
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
        <div style={{ padding: '40px 48px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            {/* Header Controls */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '32px' }}>
              <div style={{ background: '#F3F4F6', borderRadius: '99px', padding: '4px', display: 'flex' }}>
                <button
                  type="button"
                  onClick={() => setMode('signin')}
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
                  onClick={() => setMode('signup')}
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

              <span style={{ fontSize: '13px', color: '#6B7280', cursor: 'pointer', fontWeight: '600' }}>
                Help & Support &gt;
              </span>
            </div>

            {/* Welcome Heading */}
            <h2 style={{ fontSize: '26px', fontWeight: '800', marginBottom: '6px' }}>
              {mode === 'signin' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Access your real-time hackathon evaluation reports, dashboards, and leaderboards.
            </p>

            {/* Social Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
              <button type="button" style={{
                border: '1px solid #E5E7EB',
                background: '#FFFFFF',
                borderRadius: '12px',
                padding: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '13px',
                fontWeight: '700',
                cursor: 'pointer'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg> Google
              </button>
              <button type="button" style={{
                border: '1px solid #E5E7EB',
                background: '#FFFFFF',
                borderRadius: '12px',
                padding: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontSize: '13px',
                fontWeight: '700',
                cursor: 'pointer'
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg> GitHub
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
              <span style={{ fontSize: '11px', fontWeight: '700', color: '#9CA3AF', letterSpacing: '0.5px' }}>OR WITH EMAIL</span>
              <div style={{ flex: 1, height: '1px', background: '#E5E7EB' }} />
            </div>

            {/* Form */}
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

              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase' }}>Password</label>
                  {mode === 'signin' && (
                    <a href="#" style={{ fontSize: '12px', color: '#2B7FFF', textDecoration: 'none', fontWeight: '600' }}>Forgot password?</a>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type="password"
                    required
                    className="search-input"
                    style={{ width: '100%', paddingRight: '36px' }}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <Lock size={16} style={{ position: 'absolute', right: '14px', top: '12px', color: '#9CA3AF' }} />
                </div>
              </div>

              {/* Role Selection */}
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '8px' }}>Select Account Role</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                  {(['participant', 'organizer', 'judge'] as const).map((r) => (
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

              {/* Remember Me */}
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
                <span style={{ fontSize: '12px', color: '#2B7FFF', fontWeight: '700' }}>● Active Session</span>
              </div>

              {/* Main Submit Pill Button */}
              <button
                type="submit"
                style={{
                  width: '100%',
                  background: '#18191C',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '99px',
                  padding: '14px',
                  fontSize: '15px',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                  transition: 'background 0.2s'
                }}
              >
                {mode === 'signin' ? 'Sign In to Dashboard' : 'Create Account'} <ArrowRight size={18} />
              </button>
            </form>
          </div>

          {/* Footer Links */}
          <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#9CA3AF', justifyContent: 'center', marginTop: '20px' }}>
            <span>© 2026 HackGuard AI</span>
            <span>•</span>
            <a href="#" style={{ color: 'inherit' }}>Privacy Policy</a>
            <a href="#" style={{ color: 'inherit' }}>Terms of Service</a>
            <a href="#" style={{ color: 'inherit' }}>Security Audit</a>
          </div>
        </div>
      </div>
    </div>
  );
};
