import React from 'react';
import { Search, Bell } from 'lucide-react';

interface HeaderProps {
  currentRole: 'participant' | 'organizer' | 'judge';
  setCurrentRole: (role: 'participant' | 'organizer' | 'judge') => void;
  title: string;
}

export const Header: React.FC<HeaderProps> = ({ currentRole, setCurrentRole, title }) => {
  return (
    <header className="top-header">
      <h1 className="header-title">{title}</h1>

      <div className="header-actions">
        {/* Search */}
        <div className="search-input-container">
          <Search size={16} style={{ position: 'absolute', left: '14px', top: '12px', color: '#9CA3AF' }} />
          <input type="text" placeholder="Search submissions, teams..." className="search-input" />
        </div>

        {/* Notification Bell */}
        <button className="icon-btn">
          <Bell size={18} style={{ color: '#374151' }} />
          <span className="badge-dot">3</span>
        </button>

        {/* Role Switcher */}
        <div className="role-switcher">
          <button
            className={`role-btn ${currentRole === 'participant' ? 'active' : ''}`}
            onClick={() => setCurrentRole('participant')}
          >
            Participant
          </button>
          <button
            className={`role-btn ${currentRole === 'organizer' ? 'active' : ''}`}
            onClick={() => setCurrentRole('organizer')}
          >
            Organizer
          </button>
          <button
            className={`role-btn ${currentRole === 'judge' ? 'active' : ''}`}
            onClick={() => setCurrentRole('judge')}
          >
            Judge
          </button>
        </div>
      </div>
    </header>
  );
};
