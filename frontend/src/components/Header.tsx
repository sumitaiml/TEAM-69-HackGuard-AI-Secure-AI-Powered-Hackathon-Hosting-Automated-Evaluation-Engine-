import React from 'react';
import { Search, Bell } from 'lucide-react';

interface HeaderProps {
  title: string;
}

export const Header: React.FC<HeaderProps> = ({ title }) => {
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
        </button>
      </div>
    </header>
  );
};
