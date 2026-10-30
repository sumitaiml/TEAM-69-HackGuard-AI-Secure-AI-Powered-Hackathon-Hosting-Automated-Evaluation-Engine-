import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MetricCard } from './MetricCard';
import {
  Users, ShieldAlert, Sliders, Trophy, Download, Send, Plus,
  Calendar, UserPlus, Upload, Trash2, X, Sparkles, CheckCircle2,
  FileText, CalendarDays, Copy, Check
} from 'lucide-react';
import type { HackathonItem, LeaderboardEntry, RubricWeights, JudgeInviteCsvResult } from '../lib/types';
import { api } from '../lib/apiClient';
import { useAsyncAction } from '../hooks/useAsyncAction';

interface OrganizerDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
  onCreateHackathon: (title: string, description: string, startDate: string, endDate: string) => Promise<void>;
  onDeleteHackathon?: (id: string) => Promise<void>;
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
  onDeleteHackathon,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newStartDate, setNewStartDate] = useState('');
  const [newEndDate, setNewEndDate] = useState('');
  const [isCreatingEvent, setIsCreatingEvent] = useState(false);

  const getDurationDays = (start: string, end: string): number | null => {
    if (!start || !end) return null;
    const s = new Date(start);
    const e = new Date(end);
    const diffTime = e.getTime() - s.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const fillSampleTemplate = () => {
    setNewDesc(
`# Event Theme & Tracks
- Track 1: Generative AI & Autonomous Agents
- Track 2: Developer Tooling & Cyber Defense
- Track 3: Open Innovation & Web3

## Submission Guidelines
Teams must provide a GitHub repository, live production URL, 3-min demo video, and code ZIP. All submissions are automatically audited for code plagiarism and security vulnerabilities.`
    );
  };

  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [weights, setWeights] = useState<RubricWeights | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteSuccessEmail, setInviteSuccessEmail] = useState<string | null>(null);
  const [devInviteLink, setDevInviteLink] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState<string | null>(null);
  const [csvResult, setCsvResult] = useState<JudgeInviteCsvResult | null>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);

  const handleCopyLink = (link: string) => {
    navigator.clipboard.writeText(link);
    setCopiedLink(link);
    setTimeout(() => setCopiedLink(null), 2500);
  };

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

  const deleteHackathonAction = useAsyncAction(async () => {
    if (!activeHackathon) return;
    if (onDeleteHackathon) {
      await onDeleteHackathon(activeHackathon.id);
    } else {
      await api.delete(`/api/hackathons/${activeHackathon.id}`);
    }
    setShowDeleteModal(false);
  });

  const inviteJudge = useAsyncAction(async () => {
    if (!inviteEmail.trim() || !activeHackathon) return;
    const target = inviteEmail.trim();
    const res = await api.post<{ dev_invite_link?: string }>(`/api/hackathons/${activeHackathon.id}/invite-judge`, { email: target });
    if (res.dev_invite_link) {
      setDevInviteLink(res.dev_invite_link);
      setInviteSuccessEmail(null);
    } else {
      setDevInviteLink(null);
      setInviteSuccessEmail(target);
    }
    setInviteEmail('');
  });

  const inviteJudgesCsv = useAsyncAction(async (file: File) => {
    if (!activeHackathon) return;
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<JudgeInviteCsvResult>(`/api/hackathons/${activeHackathon.id}/invite-judges-csv`, formData);
    setCsvResult(res);
  });

  const handleCsvFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ''; // allow re-selecting the same file name after a retry
    if (file) {
      setCsvResult(null);
      inviteJudgesCsv.run(file);
    }
  };

  const downloadCsvTemplate = () => {
    const blob = new Blob(['email\njudge1@example.com\njudge2@example.com\n'], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'judge-invite-template.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      setIsCreatingEvent(true);
      await onCreateHackathon(newTitle, newDesc, newStartDate, newEndDate);
      setShowCreateModal(false);
      setNewTitle('');
      setNewDesc('');
      setNewStartDate('');
      setNewEndDate('');
    } finally {
      setIsCreatingEvent(false);
    }
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
      <div key={activeTab} className="card animate-fade-in">
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
      <div key={activeTab} className="card animate-fade-in">
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

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '28px 0 12px' }}>
          <div>
            <h4 style={{ fontSize: '16px', fontWeight: '800' }}>README Claim Verification</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Checks whether the README's claims (tech stack, architecture, features) match the actual codebase. Full per-claim breakdown is on the Judge report reader - this is a summary only.
            </p>
          </div>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Team Name</th><th>Claims Checked</th><th>Red Flags</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={3} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{item.repo_claims_checked_count}</td>
                  <td><span className={`pill-badge ${item.repo_red_flags_count > 0 ? 'amber' : 'green'}`}>{item.repo_red_flags_count}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '28px 0 12px' }}>
          <div>
            <h4 style={{ fontSize: '16px', fontWeight: '800' }}>Pitch Deck Relevance Check</h4>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Checks whether the uploaded presentation is actually about this project (vs. an unrelated or placeholder file) by comparing it against the README. A flagged deck's presentation score is zeroed out - it still doesn't affect technical/innovation/documentation scores, which are judged independently.
            </p>
          </div>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr><th>Team Name</th><th>Deck Relevant?</th><th>Explanation</th></tr>
            </thead>
            <tbody>
              {leaderboard.length === 0 && (
                <tr><td colSpan={3} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
              )}
              {leaderboard.map((item) => (
                <tr key={item.submission_id}>
                  <td style={{ fontWeight: '700' }}>{item.team_name}</td>
                  <td><span className={`pill-badge ${item.pitch_deck_relevant ? 'green' : 'red'}`}>{item.pitch_deck_relevant ? 'Relevant' : 'Flagged'}</span></td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{item.pitch_deck_relevance_explanation || '—'}</td>
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
      <div key={activeTab} className="card animate-fade-in">
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
    <div key={activeTab} className="animate-fade-in">
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

        <div style={{ display: 'flex', gap: '12px' }}>
          {activeHackathon && (
            <button
              type="button"
              className="role-btn"
              style={{ color: '#EF4444', borderColor: '#FCA5A5', background: '#FEF2F2' }}
              onClick={() => setShowDeleteModal(true)}
              title="Delete this hackathon event"
            >
              <Trash2 size={16} /> Delete Hackathon
            </button>
          )}
          <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={18} /> Create New Hackathon
          </button>
        </div>
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
            {inviteSuccessEmail && (
              <div style={{ marginTop: '12px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '10px', padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Check size={16} color="#10B981" />
                <span style={{ fontSize: '12px', color: '#6EE7B7' }}>
                  Invitation email sent to <strong>{inviteSuccessEmail}</strong> via Resend!
                </span>
              </div>
            )}
            {devInviteLink && (
              <div style={{ marginTop: '14px', background: 'rgba(37, 99, 235, 0.08)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '12px', padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', fontWeight: '800', color: '#93C5FD', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Judge Direct Activation Link
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopyLink(devInviteLink)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: copiedLink === devInviteLink ? '#10B981' : '#2563EB',
                      color: '#FFFFFF',
                      border: 'none',
                      padding: '3px 10px',
                      borderRadius: '99px',
                      fontSize: '11px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                  >
                    {copiedLink === devInviteLink ? (<><Check size={12} /> Copied!</>) : (<><Copy size={12} /> Copy Link</>)}
                  </button>
                </div>
                <p style={{ fontSize: '11.5px', color: '#CBD5E1', margin: '0 0 6px 0', wordBreak: 'break-all', fontFamily: 'monospace' }}>
                  {devInviteLink}
                </p>
                <p style={{ fontSize: '10.5px', color: '#94A3B8', margin: 0 }}>
                  💡 In Resend sandbox mode, emails deliver to your registered account. For other judge emails, copy and share this link directly with the judge.
                </p>
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '16px 0' }}>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }} />
              <span style={{ fontSize: '11px', color: '#6B7280', fontWeight: '700' }}>OR BULK INVITE</span>
              <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.1)' }} />
            </div>

            <p style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '10px' }}>
              Upload a CSV with an <code>email</code> column to invite many judges at once.{' '}
              <button type="button" onClick={downloadCsvTemplate} style={{ background: 'none', border: 'none', color: '#60A5FA', fontSize: '12px', fontWeight: '700', cursor: 'pointer', padding: 0 }}>
                Download template
              </button>
            </p>

            <input ref={csvInputRef} type="file" accept=".csv" onChange={handleCsvFileChange} style={{ display: 'none' }} />
            <button
              className="role-btn"
              style={{ width: '100%', justifyContent: 'center', background: 'transparent', borderColor: '#374151', color: '#FFFFFF' }}
              disabled={inviteJudgesCsv.isLoading || !activeHackathon}
              onClick={() => csvInputRef.current?.click()}
            >
              <Upload size={14} /> {inviteJudgesCsv.isLoading ? 'Uploading…' : 'Upload CSV'}
            </button>

            {inviteJudgesCsv.error && <p style={{ color: '#F87171', fontSize: '12px', marginTop: '8px' }}>{inviteJudgesCsv.error}</p>}

            {csvResult && (
              <div style={{ marginTop: '12px', background: '#111', borderRadius: '12px', padding: '12px', fontSize: '12px' }}>
                <div style={{ display: 'flex', gap: '8px', marginBottom: csvResult.skipped.length ? '8px' : 0 }}>
                  <span className="pill-badge green">{csvResult.invited_count} invited</span>
                  {csvResult.skipped_count > 0 && <span className="pill-badge amber">{csvResult.skipped_count} skipped</span>}
                </div>
                {csvResult.skipped.length > 0 && (
                  <ul style={{ paddingLeft: '18px', color: '#9CA3AF', lineHeight: '1.6' }}>
                    {csvResult.skipped.map((row, i) => (
                      <li key={i}>{row.email} — {row.reason}</li>
                    ))}
                  </ul>
                )}
                {csvResult.invited.some((row) => row.dev_invite_link) && (
                  <div style={{ marginTop: '8px' }}>
                    <p style={{ color: '#6B7280', marginBottom: '6px' }}>Direct activation links generated:</p>
                    <ul style={{ paddingLeft: '0', listStyle: 'none', margin: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {csvResult.invited.filter((row) => row.dev_invite_link).map((row, i) => (
                        <li key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(255,255,255,0.05)', padding: '6px 10px', borderRadius: '8px', fontSize: '11.5px' }}>
                          <span style={{ color: '#E2E8F0', fontWeight: '600', maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.email}</span>
                          <button
                            type="button"
                            onClick={() => handleCopyLink(row.dev_invite_link!)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              background: copiedLink === row.dev_invite_link ? '#10B981' : '#1E293B',
                              color: '#FFFFFF',
                              border: '1px solid rgba(255,255,255,0.15)',
                              padding: '2px 8px',
                              borderRadius: '6px',
                              fontSize: '10.5px',
                              fontWeight: '600',
                              cursor: 'pointer',
                            }}
                          >
                            {copiedLink === row.dev_invite_link ? (<><Check size={11} /> Copied</>) : (<><Copy size={11} /> Copy</>)}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="create-hackathon-modal-card" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="submission-modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <img
                  src="/product-logo.png"
                  alt="HackGuard Logo"
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: '12px',
                    objectFit: 'contain',
                    boxShadow: '0 4px 14px rgba(0, 0, 0, 0.18)',
                  }}
                />
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '18px', fontWeight: '800', color: '#0F172A', margin: 0, letterSpacing: '-0.3px' }}>
                      Create New Hackathon Event
                    </h3>
                    <span className="pill-badge" style={{ background: '#EFF6FF', color: '#2563EB', fontSize: '11px', padding: '2px 8px' }}>
                      HackGuard Engine
                    </span>
                  </div>
                  <p style={{ fontSize: '12.5px', color: '#64748B', margin: '2px 0 0 0' }}>
                    Configure event timeline, challenge tracks, and automated evaluation engine.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                aria-label="Close"
                style={{
                  background: '#F1F5F9',
                  border: 'none',
                  borderRadius: '50%',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  color: '#64748B',
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#E2E8F0')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#F1F5F9')}
              >
                <X size={16} />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form
              onSubmit={handleFormSubmit}
              style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
            >
              <div className="submission-modal-body">
                {/* Section 1: Event Identity */}
                <div>
                  <div className="submission-section-badge">
                    <Trophy size={13} color="#2563EB" />
                    <span>1. Event Identity & Theme</span>
                  </div>

                  <div style={{ marginBottom: '14px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#334155', marginBottom: '6px' }}>
                      Hackathon Title <span style={{ color: '#EF4444' }}>*</span>
                    </label>
                    <div className="submission-input-wrapper">
                      <Trophy className="input-icon" size={16} />
                      <input
                        type="text"
                        required
                        placeholder="e.g. AI World Championship 2026"
                        className="submission-text-input"
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <label style={{ fontSize: '12px', fontWeight: '700', color: '#334155' }}>
                        Description & Track Guidelines
                      </label>
                      <button
                        type="button"
                        onClick={fillSampleTemplate}
                        style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          color: '#2563EB',
                          background: '#EFF6FF',
                          border: '1px solid #BFDBFE',
                          padding: '2px 10px',
                          borderRadius: '99px',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <FileText size={11} /> Use Template
                      </button>
                    </div>
                    <textarea
                      placeholder="Event guidelines, challenge rules, theme tracks, and judging criteria..."
                      className="submission-text-input"
                      style={{
                        width: '100%',
                        height: '85px',
                        borderRadius: '12px',
                        lineHeight: '1.5',
                        padding: '10px 12px',
                        resize: 'vertical',
                      }}
                      value={newDesc}
                      onChange={(e) => setNewDesc(e.target.value)}
                    />
                  </div>
                </div>

                {/* Section 2: Timeline */}
                <div>
                  <div className="submission-section-badge">
                    <CalendarDays size={13} color="#2563EB" />
                    <span>2. Schedule & Event Window</span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '10px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#334155', marginBottom: '6px' }}>
                        Start Date <span style={{ color: '#EF4444' }}>*</span>
                      </label>
                      <div className="submission-input-wrapper">
                        <Calendar className="input-icon" size={16} />
                        <input
                          type="date"
                          required
                          className="submission-text-input"
                          value={newStartDate}
                          onChange={(e) => setNewStartDate(e.target.value)}
                        />
                      </div>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#334155', marginBottom: '6px' }}>
                        End Date <span style={{ color: '#EF4444' }}>*</span>
                      </label>
                      <div className="submission-input-wrapper">
                        <Calendar className="input-icon" size={16} />
                        <input
                          type="date"
                          required
                          className="submission-text-input"
                          value={newEndDate}
                          onChange={(e) => setNewEndDate(e.target.value)}
                        />
                      </div>
                    </div>
                  </div>

                  {newStartDate && newEndDate && (() => {
                    const days = getDurationDays(newStartDate, newEndDate);
                    if (days === null) return null;
                    if (days < 0) {
                      return (
                        <div style={{ fontSize: '11.5px', color: '#DC2626', background: '#FEF2F2', padding: '6px 12px', borderRadius: '8px', fontWeight: '600' }}>
                          ⚠️ End date cannot precede start date.
                        </div>
                      );
                    }
                    return (
                      <div style={{ fontSize: '11.5px', color: '#1D4ED8', background: '#EFF6FF', border: '1px solid #DBEAFE', padding: '6px 12px', borderRadius: '8px', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Sparkles size={13} color="#2563EB" />
                        <span>Event Window: <strong>{days} {days === 1 ? 'day' : 'days'}</strong> (Submissions open during this period)</span>
                      </div>
                    );
                  })()}
                </div>

                {/* Section 3: Automated Platform Capabilities */}
                <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '14px', padding: '14px 16px' }}>
                  <div style={{ fontSize: '11px', fontWeight: '800', letterSpacing: '0.06em', textTransform: 'uppercase', color: '#64748B', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <img src="/product-logo.png" alt="HackGuard" style={{ width: '16px', height: '16px', borderRadius: '4px', objectFit: 'contain' }} />
                    <span>HackGuard Automated Capabilities Active</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px', color: '#334155' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={13} color="#10B981" /> AST Code Plagiarism Engine
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={13} color="#10B981" /> Gemini + Groq AI Scoring
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={13} color="#10B981" /> Docker Sandbox Execution
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={13} color="#10B981" /> Real-Time Dynamic Leaderboard
                    </div>
                  </div>
                </div>
              </div>

              {/* Sticky Footer */}
              <div className="submission-modal-footer">
                <span style={{ fontSize: '11px', color: '#64748B', maxWidth: '340px' }}>
                  Default rubric weights (100 pts) are automatically initialized and can be edited anytime in Rubric Configurator.
                </span>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    style={{
                      padding: '9px 18px',
                      borderRadius: '99px',
                      border: '1.5px solid #CBD5E1',
                      background: '#FFFFFF',
                      color: '#475569',
                      fontSize: '13px',
                      fontWeight: '700',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#F1F5F9')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#FFFFFF')}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreatingEvent}
                    style={{
                      padding: '9px 22px',
                      borderRadius: '99px',
                      border: 'none',
                      background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                      color: '#FFFFFF',
                      fontSize: '13px',
                      fontWeight: '700',
                      cursor: isCreatingEvent ? 'not-allowed' : 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      boxShadow: '0 4px 14px rgba(37, 99, 235, 0.35)',
                      transition: 'all 0.2s',
                      opacity: isCreatingEvent ? 0.75 : 1,
                    }}
                  >
                    <Plus size={15} />
                    <span>{isCreatingEvent ? 'Creating…' : 'Create Event'}</span>
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
      {showDeleteModal && activeHackathon && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{ background: '#FEE2E2', padding: '10px', borderRadius: '12px', color: '#EF4444' }}>
                <Trash2 size={24} />
              </div>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: '800', color: '#991B1B' }}>Delete Hackathon Event?</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>This action is permanent and cannot be undone.</p>
              </div>
            </div>

            <p style={{ fontSize: '14px', lineHeight: '1.6', color: '#374151', marginBottom: '20px' }}>
              Are you sure you want to permanently delete <strong>{activeHackathon.title}</strong>? All registered submissions, AI evaluation reports, code fingerprints, judge invites, and uploaded zip/demo files for this hackathon will be completely removed.
            </p>

            {deleteHackathonAction.error && (
              <p style={{ color: '#EF4444', fontSize: '13px', marginBottom: '16px' }}>{deleteHackathonAction.error}</p>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="role-btn"
                disabled={deleteHackathonAction.isLoading}
                onClick={() => setShowDeleteModal(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{ background: '#DC2626', borderColor: '#DC2626', color: '#FFFFFF' }}
                disabled={deleteHackathonAction.isLoading}
                onClick={() => deleteHackathonAction.run()}
              >
                {deleteHackathonAction.isLoading ? 'Deleting…' : 'Yes, Delete Permanently'}
              </button>
            </div>
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
