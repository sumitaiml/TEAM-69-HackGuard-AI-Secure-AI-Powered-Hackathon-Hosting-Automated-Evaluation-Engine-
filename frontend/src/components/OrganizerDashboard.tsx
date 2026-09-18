import React, { useState } from 'react';
import { MetricCard } from './MetricCard';
import { Users, ShieldAlert, Sliders, Trophy, Download, Send, Plus, Calendar } from 'lucide-react';
import type { HackathonItem } from '../App';

interface OrganizerDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
  onCreateHackathon: (title: string, description: string, startDate: string, endDate: string) => void;
}

export const OrganizerDashboard: React.FC<OrganizerDashboardProps> = ({
  activeTab,
  setActiveTab,
  hackathons,
  selectedHackathonId,
  setSelectedHackathonId,
  onCreateHackathon,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New Hackathon Form State
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newStartDate, setNewStartDate] = useState('2026-09-25');
  const [newEndDate, setNewEndDate] = useState('2026-09-27');

  // Dynamic Rubric State
  const [weights, setWeights] = useState({
    technical: 30,
    innovation: 20,
    ui_ux: 15,
    business_impact: 15,
    documentation: 10,
    presentation: 10,
  });

  // Dynamic Fraud Feed State
  const [fraudFeed, setFraudFeed] = useState([
    { id: 'f1', team: 'Team Alpha', repo: 'github.com/alpha/app', astMatch: '84%', risk: 'CRITICAL', status: 'Flagged', baseScore: 78 },
    { id: 'f2', team: 'ByteStorm', repo: 'github.com/bytestorm/app', astMatch: '72%', risk: 'CRITICAL', status: 'Flagged', baseScore: 81 },
    { id: 'f3', team: 'CodeCraft', repo: 'github.com/codecraft/app', astMatch: '61%', risk: 'MEDIUM', status: 'Under Review', baseScore: 85 },
    { id: 'f4', team: 'AlphaCoders', repo: 'github.com/alphacoders/ai', astMatch: '0.2%', risk: 'LOW', status: 'Passed', baseScore: 92 },
  ]);

  const activeHackathon = hackathons.find((h) => h.id === selectedHackathonId) || hackathons[0];
  const totalSum = Object.values(weights).reduce((a, b) => a + b, 0);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    onCreateHackathon(newTitle, newDesc, newStartDate, newEndDate);
    setShowCreateModal(false);
    setNewTitle('');
    setNewDesc('');
  };

  const handleSliderChange = (param: keyof typeof weights, value: number) => {
    setWeights((prev) => ({ ...prev, [param]: value }));
  };

  const handleDismissAlert = (id: string) => {
    setFraudFeed(fraudFeed.map((item) => (item.id === id ? { ...item, risk: 'LOW', status: 'Dismissed' } : item)));
  };

  // 1. Rubric Configurator View
  if (activeTab === 'rubric') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Evaluation Rubric Configurator</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Dynamically adjust weighted criteria for event: <strong>{activeHackathon.title}</strong>
            </p>
          </div>
          <span className={`pill-badge ${Math.abs(totalSum - 100) < 0.1 ? 'green' : 'red'}`}>
            Total Sum: {totalSum}%
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <SliderGroup label="Technical Complexity" value={weights.technical} onChange={(v) => handleSliderChange('technical', v)} />
            <SliderGroup label="Innovation" value={weights.innovation} onChange={(v) => handleSliderChange('innovation', v)} />
            <SliderGroup label="UI/UX Design" value={weights.ui_ux} onChange={(v) => handleSliderChange('ui_ux', v)} />
            <SliderGroup label="Business Impact" value={weights.business_impact} onChange={(v) => handleSliderChange('business_impact', v)} />
            <SliderGroup label="Documentation" value={weights.documentation} onChange={(v) => handleSliderChange('documentation', v)} />
            <SliderGroup label="Presentation & Video" value={weights.presentation} onChange={(v) => handleSliderChange('presentation', v)} />
          </div>

          <div style={{ background: '#F9FAFB', padding: '24px', borderRadius: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>Rubric Weight Validation</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '16px' }}>
                All criteria weights must sum to exactly 100%. Changing weights recalculates overall scores for all registered teams.
              </p>
              {Math.abs(totalSum - 100) > 0.1 && (
                <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '12px', borderRadius: '12px', fontSize: '13px', fontWeight: '600' }}>
                  ⚠️ Weight total must equal 100%. Current total: {totalSum}%
                </div>
              )}
            </div>

            <button
              className="btn-primary"
              disabled={Math.abs(totalSum - 100) > 0.1}
              onClick={() => alert(`Rubric weights updated for "${activeHackathon.title}"!`)}
            >
              <Sliders size={16} /> Save Rubric Settings
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Fraud & Plagiarism View
  if (activeTab === 'fraud') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Plagiarism & Fraud Detection Monitor</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              AST structural code matching & cross-submission plagiarism flags for {activeHackathon.title}
            </p>
          </div>
          <span className="pill-badge red">{fraudFeed.filter((f) => f.risk === 'CRITICAL').length} High Risk Alerts</span>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Team Name</th>
                <th>Repository</th>
                <th>AST Similarity Match</th>
                <th>Risk Level</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {fraudFeed.map((item) => (
                <tr key={item.id}>
                  <td style={{ fontWeight: '700' }}>{item.team}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.repo}</td>
                  <td>
                    <span style={{ fontWeight: '800', color: item.risk === 'CRITICAL' ? '#EF4444' : '#10B981' }}>
                      {item.astMatch}
                    </span>
                  </td>
                  <td>
                    <span className={`pill-badge ${item.risk === 'CRITICAL' ? 'red' : item.risk === 'MEDIUM' ? 'amber' : 'green'}`}>
                      {item.risk}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="role-btn" style={{ fontSize: '12px' }} onClick={() => alert(`Auditing AST code snippet for ${item.team}...`)}>
                        Audit
                      </button>
                      {item.risk !== 'LOW' && (
                        <button className="role-btn" style={{ fontSize: '12px', background: '#E5E7EB' }} onClick={() => handleDismissAlert(item.id)}>
                          Dismiss
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // 3. Leaderboard View
  if (activeTab === 'leaderboard') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Results & Winner Publisher</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Official results for: <strong>{activeHackathon.title}</strong>
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="role-btn" onClick={() => alert('Exporting CSV/PDF Score Sheet...')}>
              <Download size={14} /> Export CSV
            </button>
            <button className="btn-primary" onClick={() => alert(`Winners published for "${activeHackathon.title}"!`)}>
              <Send size={14} /> Publish Winner Ranks
            </button>
          </div>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Team Name</th>
                <th>Final AI Score</th>
                <th>Plagiarism Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {fraudFeed.map((item, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '800' }}>#{idx + 1}</td>
                  <td style={{ fontWeight: '700' }}>{item.team}</td>
                  <td style={{ fontWeight: '800', fontSize: '15px' }}>{item.baseScore}</td>
                  <td>
                    <span className={`pill-badge ${item.risk === 'CRITICAL' ? 'red' : 'green'}`}>{item.risk}</span>
                  </td>
                  <td>
                    <span className="pill-badge blue">Verified</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // 4. Default Command Center Overview
  return (
    <div className="animate-fade-in">
      {/* Top Banner Bar with Hackathon Selector & Create Button */}
      <div
        style={{
          background: '#FFFFFF',
          borderRadius: '24px',
          padding: '20px 28px',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          border: '1px solid var(--border-color)',
          boxShadow: '0 4px 14px rgba(0,0,0,0.03)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: '#E8F2FF', padding: '12px', borderRadius: '14px', color: '#2B7FFF' }}>
            <Calendar size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Selected Hackathon Event ({hackathons.length} Total)
            </div>
            <select
              className="hackathon-select"
              value={selectedHackathonId}
              onChange={(e) => setSelectedHackathonId(e.target.value)}
            >
              {hackathons.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} /> Create New Hackathon
        </button>
      </div>

      {/* Top Hero Row */}
      <div className="metrics-row">
        <MetricCard
          label="Registered Teams"
          value={`${activeHackathon.teamsCount || 142} Teams`}
          subText="Event Active"
          variant="ice-blue"
          badge="Registration Live"
          badgeColor="blue"
          icon={<Users size={22} style={{ color: '#2B7FFF' }} />}
        />

        <MetricCard
          label="Evaluation Progress"
          value="85%"
          subText="Automated AI Pipeline"
          variant="lavender"
          badge="In Progress"
          badgeColor="blue"
          icon={<Sliders size={22} style={{ color: '#8B5CF6' }} />}
        />

        <MetricCard
          label="Plagiarism & Fraud Alerts"
          value={`${fraudFeed.filter((f) => f.risk === 'CRITICAL').length} Flagged`}
          subText="Action Required"
          variant="coral-red"
          badge="High Risk"
          badgeColor="red"
          icon={<ShieldAlert size={22} style={{ color: '#EF4444' }} />}
        />

        <MetricCard
          label="Leaderboard State"
          value="LIVE"
          subText="Auto-Updating Ranks"
          variant="mint-green"
          badge="Public Sync"
          badgeColor="green"
          icon={<Trophy size={22} style={{ color: '#10B981' }} />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Evaluation Rubric Configurator</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Adjust weighted criteria for AI score calculation</p>
            </div>
            <button className="role-btn" onClick={() => setActiveTab('rubric')}>
              Full Configurator →
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <SliderGroup label="Technical Complexity" value={weights.technical} onChange={(v) => handleSliderChange('technical', v)} />
            <SliderGroup label="Innovation" value={weights.innovation} onChange={(v) => handleSliderChange('innovation', v)} />
            <SliderGroup label="UI/UX Design" value={weights.ui_ux} onChange={(v) => handleSliderChange('ui_ux', v)} />
            <SliderGroup label="Business Impact" value={weights.business_impact} onChange={(v) => handleSliderChange('business_impact', v)} />
            <SliderGroup label="Documentation" value={weights.documentation} onChange={(v) => handleSliderChange('documentation', v)} />
            <SliderGroup label="Presentation & Video" value={weights.presentation} onChange={(v) => handleSliderChange('presentation', v)} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: '800' }}>Plagiarism Monitor Feed</h4>
              <button className="role-btn" style={{ fontSize: '12px' }} onClick={() => setActiveTab('fraud')}>
                View All →
              </button>
            </div>

            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Team</th>
                    <th>AST Match</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {fraudFeed.slice(0, 3).map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div style={{ fontWeight: '700' }}>{item.team}</div>
                      </td>
                      <td>
                        <span style={{ fontWeight: '800', color: item.risk === 'CRITICAL' ? '#EF4444' : '#10B981' }}>
                          {item.astMatch}
                        </span>
                      </td>
                      <td>
                        <span className={`pill-badge ${item.risk === 'CRITICAL' ? 'red' : 'green'}`}>{item.risk}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ background: '#18191C', color: '#FFFFFF' }}>
            <h4 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '12px' }}>Event Control Panel</h4>
            <p style={{ fontSize: '13px', color: '#9CA3AF', marginBottom: '20px' }}>
              Export full score sheets or publish official winners.
            </p>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="role-btn" style={{ background: '#374151', color: '#FFFFFF', flex: 1 }} onClick={() => alert('Exporting CSV...')}>
                <Download size={14} /> Export CSV
              </button>
              <button className="btn-primary" style={{ flex: 1 }} onClick={() => alert(`Winners published for "${activeHackathon.title}"!`)}>
                <Send size={14} /> Publish Winners
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Create Hackathon Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '6px' }}>Create New Hackathon Event</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Configure a new hackathon event with custom dates and evaluation rubrics.
            </p>

            <form onSubmit={handleFormSubmit}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Hackathon Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AI World Championship 2026"
                  className="search-input"
                  style={{ width: '100%' }}
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Description
                </label>
                <textarea
                  placeholder="Event guidelines, rules, and track descriptions..."
                  className="search-input"
                  style={{ width: '100%', height: '70px', borderRadius: '12px' }}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>
                    Start Date
                  </label>
                  <input
                    type="date"
                    required
                    className="search-input"
                    style={{ width: '100%' }}
                    value={newStartDate}
                    onChange={(e) => setNewStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>
                    End Date
                  </label>
                  <input
                    type="date"
                    required
                    className="search-input"
                    style={{ width: '100%' }}
                    value={newEndDate}
                    onChange={(e) => setNewEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button type="button" className="role-btn" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Create Event
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const SliderGroup: React.FC<{ label: string; value: number; onChange: (v: number) => void }> = ({ label, value, onChange }) => (
  <div className="slider-group">
    <div className="slider-label">
      <span>{label}</span>
      <span style={{ fontWeight: '800', color: '#2B7FFF' }}>{value}%</span>
    </div>
    <input type="range" min="0" max="50" value={value} onChange={(e) => onChange(Number(e.target.value))} className="range-input" />
  </div>
);
