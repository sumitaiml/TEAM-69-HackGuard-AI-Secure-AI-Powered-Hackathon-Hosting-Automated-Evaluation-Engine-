import React, { useState, useEffect, useCallback } from 'react';
import { MetricCard } from './MetricCard';
import { Users, ShieldAlert, Sliders, Trophy, Download, Send, Plus, Calendar, UserPlus } from 'lucide-react';
import type { HackathonItem, LeaderboardEntry, RubricWeights } from '../lib/types';
import { api } from '../lib/apiClient';
import { useAsyncAction } from '../hooks/useAsyncAction';

interface OrganizerDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
  onCreateHackathon: (title: string, description: string, startDate: string, endDate: string) => Promise<void>;
}

const RUBRIC_KEYS = ['technical_complexity', 'innovation', 'ui_ux', 'business_impact', 'documentation', 'presentation'] as const;
const RUBRIC_LABELS: Record<(typeof RUBRIC_KEYS)[number], string> = {
  technical_complexity: 'Technical Complexity',
  innovation: 'Innovation',
  ui_ux: 'UI/UX Design',
  business_impact: 'Business Impact',
  documentation: 'Documentation',
  presentation: 'Presentation & Video',
};

export const OrganizerDashboard: React.FC<OrganizerDashboardProps> = ({
  activeTab,
  setActiveTab,
  hackathons,
  selectedHackathonId,
  setSelectedHackathonId,
  onCreateHackathon,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newStartDate, setNewStartDate] = useState('');
  const [newEndDate, setNewEndDate] = useState('');

  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [weights, setWeights] = useState<RubricWeights | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [devInviteLink, setDevInviteLink] = useState<string | null>(null);

  const activeHackathon = hackathons.find((h) => h.id === selectedHackathonId) || null;

  const loadLeaderboard = useCallback(() => {
    if (!selectedHackathonId) { setLeaderboard([]); return; }
    api.get<LeaderboardEntry[]>(`/api/evaluation/leaderboard/${selectedHackathonId}`).then(setLeaderboard).catch(() => setLeaderboard([]));
  }, [selectedHackathonId]);
  useEffect(() => { loadLeaderboard(); }, [loadLeaderboard]);

  useEffect(() => {
    if (activeHackathon?.rubric_weights_json) {
      setWeights(activeHackathon.rubric_weights_json);
    }
  }, [activeHackathon]);

  const totalSum = weights ? Math.round(Object.values(weights).reduce((a, b) => a + b, 0)) : 0;

  const saveRubric = useAsyncAction(async () => {
    if (!weights || !activeHackathon) return;
    await api.put(`/api/hackathons/${activeHackathon.id}/rubric`, weights);
  });

  const inviteJudge = useAsyncAction(async () => {
    if (!inviteEmail.trim() || !activeHackathon) return;
    const res = await api.post<{ dev_invite_link?: string }>(`/api/hackathons/${activeHackathon.id}/invite-judge`, { email: inviteEmail });
    setDevInviteLink(res.dev_invite_link || null);
    setInviteEmail('');
  });

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    await onCreateHackathon(newTitle, newDesc, newStartDate, newEndDate);
    setShowCreateModal(false);
    setNewTitle('');
    setNewDesc('');
  };

  const handleSliderChange = (param: (typeof RUBRIC_KEYS)[number], value: number) => {
    setWeights((prev) => (prev ? { ...prev, [param]: value } : prev));
  };

  const exportCsv = () => {
    const header = 'Rank,Team,TechStack,Score,Technical,Innovation,UIUX,Impact,PlagiarismRisk,PlagiarismPercent,Status\n';
    const rows = leaderboard.map((e) => `${e.rank},"${e.team_name}","${e.tech_stack}",${e.score},${e.parameter_scores?.technical_complexity ?? ''},${e.parameter_scores?.innovation ?? ''},${e.parameter_scores?.ui_ux ?? ''},${e.parameter_scores?.business_impact ?? ''},${e.plagiarism_risk},${e.plagiarism_percentage},${e.status}`).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeHackathon?.title || 'leaderboard'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const criticalCount = leaderboard.filter((e) => e.plagiarism_risk === 'CRITICAL').length;
  const evaluatedCount = leaderboard.filter((e) => e.status === 'completed').length;
  const registeredTeams = new Set(leaderboard.map((e) => e.team_id)).size;

  // ---- 1. Rubric Configurator View ----
  if (activeTab === 'rubric') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Evaluation Rubric Configurator</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Dynamically adjust weighted criteria for event: <strong>{activeHackathon?.title || '—'}</strong>
            </p>
          </div>
          <span className={`pill-badge ${Math.abs(totalSum - 100) < 0.1 ? 'green' : 'red'}`}>Total Sum: {totalSum}%</span>
        </div>

        {!weights ? (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Select a hackathon to configure its rubric.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {RUBRIC_KEYS.map((key) => (
                <SliderGroup key={key} label={RUBRIC_LABELS[key]} value={weights[key]} onChange={(v) => handleSliderChange(key, v)} />
              ))}
            </div>

            <div style={{ background: '#F9FAFB', padding: '24px', borderRadius: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>Rubric Weight Validation</h4>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '16px' }}>
                  All criteria weights must sum to exactly 100%. Saving recalculates future evaluations against these weights.
                </p>
                {Math.abs(totalSum - 100) > 0.1 && (
                  <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '12px', borderRadius: '12px', fontSize: '13px', fontWeight: '600' }}>
                    ⚠️ Weight total must equal 100%. Current total: {totalSum}%
                  </div>
                )}
                {saveRubric.error && <p style={{ color: '#EF4444', fontSize: '13px', marginTop: '12px' }}>{saveRubric.error}</p>}
              </div>

              <button className="btn-primary" disabled={Math.abs(totalSum - 100) > 0.1 || saveRubric.isLoading} onClick={() => saveRubric.run()}>
                <Sliders size={16} /> {saveRubric.isLoading ? 'Saving…' : 'Save Rubric Settings'}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ---- 2. Fraud & Plagiarism View ----
  if (activeTab === 'fraud') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Plagiarism & Fraud Detection Monitor</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              AST/MinHash cross-submission plagiarism flags for {activeHackathon?.title || '—'}. AI explanations are flagged for organizer review, not a finding of fact.
            </p>
          </div>
          <span className="pill-badge red">{criticalCount} High Risk Alerts</span>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Team Name</th><th>Repository</th><th>Similarity</th><th>Risk Level</th><th>AI Explanation</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={6} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.github_url || '—'}</td>
                  <td><span style={{ fontWeight: '800', color: item.plagiarism_risk === 'CRITICAL' ? '#EF4444' : '#10B981' }}>{item.plagiarism_percentage}%</span></td>
                  <td><span className={`pill-badge ${item.plagiarism_risk === 'CRITICAL' ? 'red' : item.plagiarism_risk === 'MEDIUM' ? 'amber' : 'green'}`}>{item.plagiarism_risk}</span></td>
                  <td style={{ maxWidth: '280px' }}>
                    {item.plagiarism_explanation ? (
                      <>
                        <span className={`pill-badge ${item.plagiarism_explanation.verdict === 'probable_copying' ? 'red' : item.plagiarism_explanation.verdict === 'likely_shared_boilerplate' ? 'green' : 'blue'}`} style={{ marginBottom: '4px', display: 'inline-block' }}>
                          {item.plagiarism_explanation.verdict.replace(/_/g, ' ')}
                        </span>
                        <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{item.plagiarism_explanation.explanation}</div>
                      </>
                    ) : '—'}
                  </td>
                  <td>
                    {item.github_url && (
                      <a className="role-btn" style={{ fontSize: '12px', textDecoration: 'none', display: 'inline-block' }} href={item.github_url} target="_blank" rel="noreferrer">
                        View Repo
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '28px 0 12px' }}>
          <div>
            <h4 style={{ fontSize: '16px', fontWeight: '800' }}>AI-Generated Code Detection</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Heuristic estimate only (comment density, naming patterns, boilerplate phrasing) - not proof of AI authorship. For organizer review, not an automatic penalty.
            </p>
          </div>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Team Name</th><th>Estimated AI Usage</th><th>Risk Level</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={3} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.ai_code_usage_percentage != null ? `${item.ai_code_usage_percentage}%` : '—'}</td>
                  <td><span className={`pill-badge ${item.ai_code_risk === 'HIGH' ? 'red' : item.ai_code_risk === 'MEDIUM' ? 'amber' : item.ai_code_risk === 'LOW' ? 'green' : 'blue'}`}>{item.ai_code_risk}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '28px 0 12px' }}>
          <div>
            <h4 style={{ fontSize: '16px', fontWeight: '800' }}>Submission Timeline Check</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Flags repos whose commit history predates the hackathon start (or an unusually large first commit) - catches a pre-built project submitted as new, which plagiarism matching alone can't. For organizer review, not an automatic penalty.
            </p>
          </div>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Team Name</th><th>Risk Level</th><th>Reasoning</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={3} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td><span className={`pill-badge ${item.timeline_risk_level === 'HIGH' ? 'red' : item.timeline_risk_level === 'MEDIUM' ? 'amber' : 'green'}`}>{item.timeline_risk_level}</span></td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{item.timeline_reasoning || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ---- 3. Leaderboard View ----
  if (activeTab === 'leaderboard') {
    return (
      <div className="card animate-fade-in">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Results & Winner Publisher</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Official results for: <strong>{activeHackathon?.title || '—'}</strong></p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="role-btn" onClick={exportCsv} disabled={leaderboard.length === 0}>
              <Download size={14} /> Export CSV
            </button>
            <button className="btn-primary" title="Result publishing/locking isn't backed by the API yet" disabled>
              <Send size={14} /> Publish Winner Ranks
            </button>
          </div>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Rank</th><th>Team Name</th><th>Final AI Score</th><th>Technical</th><th>Innovation</th><th>UI/UX</th><th>Impact</th><th>Plagiarism Risk</th><th>Status</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={9} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '800' }}>#{item.rank}</td>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td style={{ fontWeight: '800', fontSize: '15px' }}>{item.score}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.parameter_scores?.technical_complexity ?? '—'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.parameter_scores?.innovation ?? '—'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.parameter_scores?.ui_ux ?? '—'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.parameter_scores?.business_impact ?? '—'}</td>
                  <td><span className={`pill-badge ${item.plagiarism_risk === 'CRITICAL' ? 'red' : 'green'}`}>{item.plagiarism_risk}</span></td>
                  <td><span className="pill-badge blue">{item.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // ---- 4. Default Command Center Overview ----
  return (
    <div className="animate-fade-in">
      <div style={{
        background: '#FFFFFF', borderRadius: '24px', padding: '20px 28px', marginBottom: '24px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        border: '1px solid var(--border-color)', boxShadow: '0 4px 14px rgba(0,0,0,0.03)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ background: '#E8F2FF', padding: '12px', borderRadius: '14px', color: '#2B7FFF' }}>
            <Calendar size={24} />
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '4px' }}>
              Selected Hackathon Event ({hackathons.length} Total)
            </div>
            <select className="hackathon-select" value={selectedHackathonId} onChange={(e) => setSelectedHackathonId(e.target.value)}>
              {hackathons.length === 0 && <option value="">No hackathons yet</option>}
              {hackathons.map((h) => <option key={h.id} value={h.id}>{h.title}</option>)}
            </select>
          </div>
        </div>

        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} /> Create New Hackathon
        </button>
      </div>

      <div className="metrics-row">
        <MetricCard
          label="Registered Teams"
          value={`${registeredTeams} Teams`}
          subText={activeHackathon?.is_active ? 'Event Active' : 'Event Inactive'}
          variant="ice-blue"
          badge={activeHackathon?.is_active ? 'Active' : 'Inactive'}
          badgeColor="blue"
          icon={<Users size={22} style={{ color: '#2B7FFF' }} />}
        />

        <MetricCard
          label="Evaluation Progress"
          value={leaderboard.length ? `${Math.round((evaluatedCount / leaderboard.length) * 100)}%` : '0%'}
          subText={`${evaluatedCount}/${leaderboard.length} Evaluated`}
          variant="lavender"
          badge="AI Pipeline"
          badgeColor="blue"
          icon={<Sliders size={22} style={{ color: '#8B5CF6' }} />}
        />

        <MetricCard
          label="Plagiarism & Fraud Alerts"
          value={`${criticalCount} Flagged`}
          subText="Action Required"
          variant="coral-red"
          badge={criticalCount > 0 ? 'High Risk' : 'Clean'}
          badgeColor={criticalCount > 0 ? 'red' : 'green'}
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

      <div className="dashboard-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Evaluation Rubric Configurator</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Adjust weighted criteria for AI score calculation</p>
            </div>
            <button className="role-btn" onClick={() => setActiveTab('rubric')}>Full Configurator →</button>
          </div>

          {weights && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {RUBRIC_KEYS.map((key) => (
                <SliderGroup key={key} label={RUBRIC_LABELS[key]} value={weights[key]} onChange={(v) => handleSliderChange(key, v)} />
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '16px', fontWeight: '800' }}>Plagiarism Monitor Feed</h4>
              <button className="role-btn" style={{ fontSize: '12px' }} onClick={() => setActiveTab('fraud')}>View All →</button>
            </div>
            <div className="data-table-container">
              <table className="data-table">
                <thead><tr><th>Team</th><th>Similarity</th><th>Risk</th></tr></thead>
                <tbody>
                  {leaderboard.slice(0, 3).map((item) => (
                    <tr key={item.submission_id}>
                      <td><div style={{ fontWeight: '700' }}>{item.team_name}</div></td>
                      <td><span style={{ fontWeight: '800', color: item.plagiarism_risk === 'CRITICAL' ? '#EF4444' : '#10B981' }}>{item.plagiarism_percentage}%</span></td>
                      <td><span className={`pill-badge ${item.plagiarism_risk === 'CRITICAL' ? 'red' : 'green'}`}>{item.plagiarism_risk}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{ background: '#18191C', color: '#FFFFFF' }}>
            <h4 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '12px' }}>Invite a Judge</h4>
            <p style={{ fontSize: '13px', color: '#9CA3AF', marginBottom: '16px' }}>
              Sends an invite to review submissions for {activeHackathon?.title || 'this event'}.
            </p>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="email"
                placeholder="judge@email.com"
                className="search-input"
                style={{ flex: 1, background: '#111', color: '#fff', borderColor: '#374151' }}
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              <button className="btn-primary" disabled={inviteJudge.isLoading || !activeHackathon} onClick={() => inviteJudge.run()}>
                <UserPlus size={14} /> {inviteJudge.isLoading ? 'Sending…' : 'Invite'}
              </button>
            </div>
            {inviteJudge.error && <p style={{ color: '#F87171', fontSize: '12px' }}>{inviteJudge.error}</p>}
            {devInviteLink && (
              <p style={{ fontSize: '11px', color: '#9CA3AF', wordBreak: 'break-all' }}>
                No email provider configured - share this link directly: <a href={devInviteLink} style={{ color: '#60A5FA' }}>{devInviteLink}</a>
              </p>
            )}
          </div>
        </div>
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '22px', fontWeight: '800', marginBottom: '6px' }}>Create New Hackathon Event</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
              Configure a new hackathon event with custom dates and evaluation rubrics.
            </p>

            <form onSubmit={handleFormSubmit}>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Hackathon Title</label>
                <input type="text" required placeholder="e.g. AI World Championship 2026" className="search-input" style={{ width: '100%' }} value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Description</label>
                <textarea placeholder="Event guidelines, rules, and track descriptions..." className="search-input" style={{ width: '100%', height: '70px', borderRadius: '12px' }} value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>Start Date</label>
                  <input type="date" required className="search-input" style={{ width: '100%' }} value={newStartDate} onChange={(e) => setNewStartDate(e.target.value)} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: '800', color: '#374151', textTransform: 'uppercase', marginBottom: '6px' }}>End Date</label>
                  <input type="date" required className="search-input" style={{ width: '100%' }} value={newEndDate} onChange={(e) => setNewEndDate(e.target.value)} />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button type="button" className="role-btn" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary">Create Event</button>
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
