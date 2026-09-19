import React from 'react';
import { LayoutDashboard, Users, UploadCloud, FileText, Trophy, ShieldAlert, Sliders, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import type { Role } from '../lib/types';

interface SidebarProps {
  currentRole: Role;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  if (parts.length === 0 || !parts[0]) return '?';
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase();
}

export const Sidebar: React.FC<SidebarProps> = ({ currentRole, activeTab, setActiveTab }) => {
  const { user, logout } = useAuth();

  return (
    <aside style={{
      width: '260px',
      backgroundColor: 'var(--sidebar-bg)',
      color: '#FFFFFF',
      padding: '32px 24px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      minHeight: '100vh'
    }}>
      <div>
        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '40px' }}>
          <div style={{
            background: '#FDF8E2',
            color: '#18191C',
            width: '44px',
            height: '44px',
            borderRadius: '14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: '800',
            fontSize: '20px'
          }}>
            ⚡
          </div>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '800', lineHeight: '1.2' }}>HackGuard AI</h2>
            <span style={{ fontSize: '11px', color: '#9CA3AF', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {currentRole} Portal
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {currentRole === 'participant' && (
            <>
              <NavItem icon={<LayoutDashboard size={18} />} label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
              <NavItem icon={<Users size={18} />} label="Team Management" active={activeTab === 'team'} onClick={() => setActiveTab('team')} />
              <NavItem icon={<UploadCloud size={18} />} label="Submit Project" active={activeTab === 'submit'} onClick={() => setActiveTab('submit')} />
              <NavItem icon={<FileText size={18} />} label="AI Evaluation" active={activeTab === 'report'} onClick={() => setActiveTab('report')} />
              <NavItem icon={<Trophy size={18} />} label="Live Leaderboard" active={activeTab === 'leaderboard'} onClick={() => setActiveTab('leaderboard')} />
            </>
          )}

          {currentRole === 'organizer' && (
            <>
              <NavItem icon={<LayoutDashboard size={18} />} label="Command Center" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
              <NavItem icon={<Sliders size={18} />} label="Rubric Configurator" active={activeTab === 'rubric'} onClick={() => setActiveTab('rubric')} />
              <NavItem icon={<ShieldAlert size={18} />} label="Fraud & Plagiarism" active={activeTab === 'fraud'} onClick={() => setActiveTab('fraud')} />
              <NavItem icon={<Trophy size={18} />} label="Results & Leaderboard" active={activeTab === 'leaderboard'} onClick={() => setActiveTab('leaderboard')} />
            </>
          )}

          {currentRole === 'judge' && (
            <>
              <NavItem icon={<LayoutDashboard size={18} />} label="Judge Queue" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
              <NavItem icon={<FileText size={18} />} label="AI Report Audit" active={activeTab === 'report'} onClick={() => setActiveTab('report')} />
              <NavItem icon={<Sliders size={18} />} label="Score Override" active={activeTab === 'override'} onClick={() => setActiveTab('override')} />
            </>
          )}
        </nav>
      </div>

      {/* User Footer */}
      <div style={{
        paddingTop: '20px',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '99px',
            background: '#374151',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            fontWeight: '700'
          }}>
            {user ? initials(user.full_name) : '?'}
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '700' }}>
              {user?.full_name || 'Unknown user'}
            </div>
            <div style={{ fontSize: '11px', color: '#9CA3AF' }}>{user?.email}</div>
          </div>
        </div>
        <button
          onClick={logout}
          title="Sign out"
          style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'flex' }}
        >
          <LogOut size={16} style={{ color: '#9CA3AF' }} />
        </button>
      </div>
    </aside>
  );
};

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, active, onClick }) => {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        borderRadius: '12px',
        border: 'none',
        background: active ? '#2B7FFF' : 'transparent',
        color: active ? '#FFFFFF' : '#9CA3AF',
        fontWeight: active ? '700' : '500',
        fontSize: '14px',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        transition: 'all 0.2s'
      }}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
};
