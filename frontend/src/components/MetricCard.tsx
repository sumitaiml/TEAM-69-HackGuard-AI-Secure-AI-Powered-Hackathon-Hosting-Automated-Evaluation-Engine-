import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subText: string;
  icon?: React.ReactNode;
  variant?: 'ice-blue' | 'lavender' | 'mint-green' | 'cream-yellow' | 'coral-red';
  badge?: string;
  badgeColor?: 'green' | 'red' | 'amber' | 'blue';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subText,
  icon,
  variant = 'ice-blue',
  badge,
  badgeColor = 'blue'
}) => {
  return (
    <div className={`metric-card ${variant}`}>
      <div className="metric-card-header">
        <span className="metric-label">{label}</span>
        {icon && <div>{icon}</div>}
      </div>
      <div>
        <div className="metric-value">{value}</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="metric-sub">{subText}</span>
          {badge && <span className={`pill-badge ${badgeColor}`}>{badge}</span>}
        </div>
      </div>
    </div>
  );
};
