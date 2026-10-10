import React, { useState, useEffect, useCallback } from 'react';
import { MetricCard } from './MetricCard';
import { GitBranch, ShieldCheck, Trophy, Rocket, Upload, UserPlus } from 'lucide-react';

import type { HackathonItem, Team, Submission, EvaluationReport, LeaderboardEntry } from '../lib/types';
import { api } from '../lib/apiClient';
import { useAsyncAction } from '../hooks/useAsyncAction';
import { useTaskPolling } from '../hooks/useTaskPolling';

interface ParticipantDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
}

export const ParticipantDashboard: React.FC<ParticipantDashboardProps> = ({
  activeTab, setActiveTab, hackathons, selectedHackathonId, setSelectedHackathonId,
}) => {
  const [teams, setTeams] = useState<Team[] | null>(null); // null = still loading
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [evalTaskId, setEvalTaskId] = useState<string | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  const [newTeamName, setNewTeamName] = useState('');
  const [inviteCodeInput, setInviteCodeInput] = useState('');

  const team = teams?.[0] || null;
  const latestSubmission = submissions[0] || null;

  const loadTeams = useCallback(() => {
    api.get<Team[]>('/api/teams/my-team').then(setTeams).catch(() => setTeams([]));
  }, []);
  useEffect(() => { loadTeams(); }, [loadTeams]);

  const loadSubmissions = useCallback(() => {
    if (!team) { setSubmissions([]); return; }
    api.get<Submission[]>(`/api/submissions/team/${team.id}`)
      .then((subs) => setSubmissions([...subs].sort((a, b) => b.submitted_at.localeCompare(a.submitted_at))))
      .catch(() => setSubmissions([]));
  }, [team]);
  useEffect(() => { loadSubmissions(); }, [loadSubmissions]);

  useEffect(() => {
    if (!latestSubmission) { setReport(null); return; }
    api.get<EvaluationReport>(`/api/evaluation/report/${latestSubmission.id}`).then(setReport).catch(() => setReport(null));
  }, [latestSubmission]);

  const loadLeaderboard = useCallback(() => {
    if (!selectedHackathonId) { setLeaderboard([]); return; }
    api.get<LeaderboardEntry[]>(`/api/evaluation/leaderboard/${selectedHackathonId}`).then(setLeaderboard).catch(() => setLeaderboard([]));
  }, [selectedHackathonId]);
  useEffect(() => { loadLeaderboard(); }, [loadLeaderboard]);

  const evalTaskStatus = useTaskPolling(evalTaskId);
  useEffect(() => {
    if (evalTaskStatus?.status === 'SUCCESS' || evalTaskStatus?.status === 'FAILURE') {
      setEvalTaskId(null);
      loadSubmissions();
      loadLeaderboard();
    }
  }, [evalTaskStatus, loadSubmissions, loadLeaderboard]);

  const createTeam = useAsyncAction(async () => {
    if (!newTeamName.trim()) return;
    const created = await api.post<Team>('/api/teams/create', { name: newTeamName });
    setTeams((prev) => [created, ...(prev || [])]);
    setNewTeamName('');
  });

  const joinTeam = useAsyncAction(async () => {
    if (!inviteCodeInput.trim()) return;
    const joined = await api.post<Team>('/api/teams/join', { invite_code: inviteCodeInput.toUpperCase() });
    setTeams((prev) => [joined, ...(prev || []).filter((t) => t.id !== joined.id)]);
    setInviteCodeInput('');
  });

  const myTeamRank = team ? leaderboard.find((l) => l.team_id === team.id) : undefined;

  const own = report?.judge_override_json
    ? { scores: report.judge_override_json.parameter_scores, overall: report.final_score }
    : { scores: report?.ai_scores_json?.parameter_scores || null, overall: report?.final_score };

  // ---- 1. Team Management View ----
  if (activeTab === 'team') {
    return (
      <div key={activeTab} className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {team ? (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Team Management — {team.name}</h3>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Share your invite code so teammates can join.</p>
              </div>
              <div style={{ background: '#E8F2FF', padding: '8px 16px', borderRadius: '12px', fontSize: '13px', fontWeight: '700', color: '#2B7FFF' }}>
                Invite Code: <span style={{ fontFamily: 'monospace', fontSize: '15px' }}>{team.invite_code}</span>
              </div>
            </div>

            <h4 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>Current Members ({team.members.length})</h4>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr><th>Name</th><th>Email</th><th>Role</th></tr>
                </thead>
                <tbody>
                  {team.members.map((m) => (
                    <tr key={m.id}>
                      <td style={{ fontWeight: '700' }}>{m.user.full_name}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{m.user.email}</td>
                      <td><span className="pill-badge green">{m.user.id === team.leader_id ? 'Team Leader' : 'Member'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="card">
            <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '6px' }}>You're not on a team yet</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Create a new team or join one with an invite code below.</p>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div className="card">
            <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '8px' }}>Create a New Team</h4>
            <input
              type="text"
              placeholder="Team name"
              className="search-input"
              style={{ width: '100%', marginBottom: '8px' }}
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
            />
            <button className="btn-primary" style={{ width: '100%', fontSize: '13px' }} disabled={createTeam.isLoading} onClick={() => createTeam.run()}>
              <UserPlus size={14} /> {createTeam.isLoading ? 'Creating…' : 'Create Team'}
            </button>
            {createTeam.error && <p style={{ color: '#EF4444', fontSize: '12px', marginTop: '8px' }}>{createTeam.error}</p>}
          </div>

          <div className="card">
            <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '8px' }}>Join Another Team</h4>
            <input
              type="text"
              placeholder="Enter 6-char Invite Code"
              className="search-input"
              style={{ width: '100%', marginBottom: '8px' }}
              value={inviteCodeInput}
              onChange={(e) => setInviteCodeInput(e.target.value)}
            />
            <button className="role-btn" style={{ width: '100%', background: '#18191C', color: '#FFFFFF' }} disabled={joinTeam.isLoading} onClick={() => joinTeam.run()}>
              {joinTeam.isLoading ? 'Joining…' : 'Join Team'}
            </button>
            {joinTeam.error && <p style={{ color: '#EF4444', fontSize: '12px', marginTop: '8px' }}>{joinTeam.error}</p>}
          </div>
        </div>
      </div>
    );
  }

  // ---- 2. Project Submission View ----
  if (activeTab === 'submit') {
    return (
      <div key={activeTab} className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Project Submission Hub</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Upload your GitHub repo link, ZIP archive, PPT slides, and demo video.</p>
            </div>
            <button className="btn-primary" disabled={!team || !selectedHackathonId} onClick={() => setShowSubmitModal(true)}>
              <Upload size={16} /> New Submission
            </button>
          </div>

          {!team && <p style={{ fontSize: '13px', color: '#EF4444' }}>Join or create a team before submitting a project.</p>}
          {team && !selectedHackathonId && <p style={{ fontSize: '13px', color: '#EF4444' }}>No active hackathon to submit to yet - check back once one is created.</p>}

          {latestSubmission && (
            <div style={{ background: '#F0F7FF', borderRadius: '16px', padding: '24px', border: '1px solid #BFDBFE', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span className="pill-badge blue">Latest Submission (ID: {latestSubmission.id.slice(0, 8)})</span>
                <span style={{ fontSize: '12px', color: '#1E40AF', fontWeight: '600' }}>{new Date(latestSubmission.submitted_at).toLocaleString()}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', fontSize: '14px' }}>
                <div><strong>GitHub URL:</strong> <br />{latestSubmission.github_url ? <a href={latestSubmission.github_url} target="_blank" rel="noreferrer" style={{ color: '#2B7FFF' }}>{latestSubmission.github_url}</a> : '—'}</div>
                <div><strong>Tech Stack:</strong> <br />{latestSubmission.tech_stack || '—'}</div>
                <div><strong>Status:</strong> <br /><span className="pill-badge blue">{latestSubmission.status}</span></div>
              </div>
              {evalTaskId && <p style={{ fontSize: '12px', color: '#1E40AF', marginTop: '12px' }}>Evaluation running… ({evalTaskStatus?.status || 'queued'})</p>}
            </div>
          )}

          <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>Submission History</h4>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr><th>Submitted At</th><th>Tech Stack</th><th>Status</th></tr>
              </thead>
              <tbody>
                {submissions.length === 0 && (
                  <tr><td colSpan={3} style={{ color: 'var(--text-secondary)' }}>No submissions yet.</td></tr>
                )}
                {submissions.map((s) => (
                  <tr key={s.id}>
                    <td style={{ fontWeight: '700' }}>{new Date(s.submitted_at).toLocaleString()}</td>
                    <td>{s.tech_stack || '—'}</td>
                    <td><span className="pill-badge blue">{s.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showSubmitModal && team && (
          <SubmitModal
            hackathonId={selectedHackathonId}
            teamId={team.id}
            onClose={() => setShowSubmitModal(false)}
            onSubmitted={(sub) => {
              setSubmissions((prev) => [sub, ...prev]);
              setShowSubmitModal(false);
            }}
            onEvaluationTriggered={setEvalTaskId}
          />
        )}
      </div>
    );
  }

  // ---- 3. AI Report View ----
  if (activeTab === 'report') {
    const scores = own.scores;
    return (
      <div key={activeTab} className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>AI Evaluation Breakdown Report</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Detailed feedback generated by HackEval Engine.</p>
            </div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#2B7FFF' }}>
              {report ? `${own.overall} / 100` : '—'}
            </div>
          </div>

          {!report ? (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {latestSubmission ? 'Not evaluated yet - submit or run an evaluation from the Submit tab.' : 'Submit a project to see your AI evaluation here.'}
            </p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {scores && Object.entries(scores).map(([label, score]) => (
                  <ParamRow key={label} label={formatParamLabel(label)} score={Math.round(score)} />
                ))}
              </div>

              <div style={{ background: '#F9FAFB', padding: '20px', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>AI Feedback Highlights</h4>
                {report.ai_scores_json?.ai_evaluation_degraded && (
                  <p style={{ fontSize: '12px', color: '#B45309', background: '#FEF3C7', padding: '8px 12px', borderRadius: '10px' }}>
                    AI scoring was temporarily unavailable for part of this evaluation - a judge may review this manually.
                  </p>
                )}
                <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#374151' }}>
                  {(report.ai_scores_json?.ai_feedback || []).map((f, i) => <li key={i}>{f}</li>)}
                </ul>
                {(report.ai_scores_json?.improvement_suggestions?.length ?? 0) > 0 && (
                  <>
                    <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>Suggestions</h4>
                    <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#374151' }}>
                      {report.ai_scores_json!.improvement_suggestions.map((f, i) => <li key={i}>{f}</li>)}
                    </ul>
                  </>
                )}
                {report.judge_comments && (
                  <>
                    <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>Judge Comments</h4>
                    <p style={{ fontSize: '13px', color: '#374151' }}>{report.judge_comments}</p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {report?.ai_scores_json?.pitch_deck_analysis?.status === 'completed' && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h4 style={{ fontSize: '15px', fontWeight: '700' }}>Pitch Deck Breakdown</h4>
              <span className="pill-badge blue">{Math.round(report.ai_scores_json.pitch_deck_analysis.overall_narrative_score)}/100 narrative</span>
            </div>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr><th>Slide</th><th>Role</th><th>Clarity</th><th>Notes</th></tr>
                </thead>
                <tbody>
                  {report.ai_scores_json.pitch_deck_analysis.slides.map((s) => (
                    <tr key={s.slide_number}>
                      <td style={{ fontWeight: '700' }}>#{s.slide_number}</td>
                      <td><span className="pill-badge blue">{s.narrative_role}</span></td>
                      <td>{Math.round(s.clarity_score)}%</td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{s.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {report.ai_scores_json.pitch_deck_analysis.missing_narrative_elements.length > 0 && (
              <p style={{ fontSize: '12px', color: '#B45309', marginTop: '10px' }}>
                Missing: {report.ai_scores_json.pitch_deck_analysis.missing_narrative_elements.join(', ')}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  // ---- 4. Live Leaderboard View ----
  if (activeTab === 'leaderboard') {
    return (
      <div key={activeTab} className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Official Hackathon Live Leaderboard</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{leaderboard.length} teams ranked by AI score.</p>
            </div>
            <HackathonPicker hackathons={hackathons} selectedId={selectedHackathonId} onChange={setSelectedHackathonId} />
          </div>

          <LeaderboardTable entries={leaderboard} highlightTeamId={team?.id} />
        </div>
      </div>
    );
  }

  // ---- 5. Default Overview View ----
  return (
    <div key={activeTab} className="animate-fade-in">
      <div style={{ marginBottom: '16px' }}>
        <HackathonPicker hackathons={hackathons} selectedId={selectedHackathonId} onChange={setSelectedHackathonId} />
      </div>

      <div className="metrics-row">
        <div className="metric-card ice-blue">
          <div className="metric-card-header">
            <span className="metric-label">Overall AI Evaluation Score</span>
            <span className="pill-badge blue">{report ? 'Evaluated' : 'Pending'}</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span className="metric-value" style={{ color: '#2B7FFF' }}>{report ? own.overall : '—'}</span>
              <span style={{ fontSize: '18px', fontWeight: '700', color: '#6B7280' }}>/ 100</span>
            </div>
          </div>
        </div>

        <MetricCard
          label="Submission Status"
          value={latestSubmission ? latestSubmission.status : 'None yet'}
          subText={latestSubmission?.github_url ? 'Git repo linked' : 'No repo linked'}
          variant="lavender"
          badge={latestSubmission ? 'Uploaded' : undefined}
          badgeColor="blue"
          icon={<GitBranch size={22} style={{ color: '#8B5CF6' }} />}
        />

        <MetricCard
          label="Plagiarism Risk"
          value={report?.plagiarism_json?.risk_level || 'N/A'}
          subText={report?.plagiarism_json?.similarity_percentage != null ? `${report.plagiarism_json.similarity_percentage}% similarity` : 'Not yet checked'}
          variant="mint-green"
          badge={report?.plagiarism_json?.risk_level || undefined}
          badgeColor={report?.plagiarism_json?.risk_level === 'CRITICAL' ? 'red' : report?.plagiarism_json?.risk_level === 'MEDIUM' ? 'amber' : 'green'}
          icon={<ShieldCheck size={22} style={{ color: '#10B981' }} />}
        />

        <MetricCard
          label="Leaderboard Rank"
          value={myTeamRank ? `#${myTeamRank.rank} of ${leaderboard.length}` : 'Unranked'}
          subText={team ? team.name : 'No team yet'}
          variant="cream-yellow"
          badge={myTeamRank ? 'Ranked' : undefined}
          badgeColor="amber"
          icon={<Trophy size={22} style={{ color: '#F59E0B' }} />}
        />
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Live Hackathon Leaderboard</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Top competing teams & dynamic AI scores</p>
            </div>
            <button className="role-btn" onClick={() => setActiveTab('leaderboard')}>View Full Ranks →</button>
          </div>
          <LeaderboardTable entries={leaderboard.slice(0, 4)} highlightTeamId={team?.id} compact />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="dark-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#60A5FA', fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', marginBottom: '8px' }}>
              <Rocket size={16} /> {team ? 'Ready to Submit' : 'Get Started'}
            </div>
            <h3 className="dark-banner-title">{team ? 'Submit Updated Code & Video Demo!' : 'Create or join a team first'}</h3>
            <p className="dark-banner-sub">
              {team ? 'Run Docker sandbox validation and AI evaluation after uploading.' : 'You need a team before you can submit a project.'}
            </p>
            <button className="btn-primary" disabled={!team} onClick={() => { setActiveTab('submit'); setShowSubmitModal(true); }}>
              <Upload size={16} /> Submit Project Now
            </button>
          </div>

          <div className="card">
            <h4 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '16px' }}>Parameter Score Breakdown</h4>
            {own.scores ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {Object.entries(own.scores).map(([label, score]) => (
                  <ParamRow key={label} label={formatParamLabel(label)} score={Math.round(score)} />
                ))}
              </div>
            ) : (
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No evaluation yet.</p>
            )}
          </div>
        </div>
      </div>

      {showSubmitModal && team && (
        <SubmitModal
          hackathonId={selectedHackathonId}
          teamId={team.id}
          onClose={() => setShowSubmitModal(false)}
          onSubmitted={(sub) => { setSubmissions((prev) => [sub, ...prev]); setShowSubmitModal(false); }}
          onEvaluationTriggered={setEvalTaskId}
        />
      )}
    </div>
  );
};

function formatParamLabel(key: string): string {
  return key.split('_').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');
}

const HackathonPicker: React.FC<{ hackathons: HackathonItem[]; selectedId: string; onChange: (id: string) => void }> = ({ hackathons, selectedId, onChange }) => (
  <select className="hackathon-select" value={selectedId} onChange={(e) => onChange(e.target.value)}>
    {hackathons.length === 0 && <option value="">No hackathons yet</option>}
    {hackathons.map((h) => <option key={h.id} value={h.id}>{h.title}</option>)}
  </select>
);

const LeaderboardTable: React.FC<{ entries: LeaderboardEntry[]; highlightTeamId?: string; compact?: boolean }> = ({ entries, highlightTeamId, compact }) => (
  <div className="data-table-container">
    <table className="data-table">
      <thead>
        <tr>
          <th>Rank</th><th>Team Name</th>{!compact && <th>Tech Stack</th>}<th>AI Score</th>
          {!compact && <th>Technical</th>}
          {!compact && <th>Innovation</th>}
          {!compact && <th>UI/UX</th>}
          {!compact && <th>Impact</th>}
          <th>Plagiarism Risk</th><th>Status</th>
        </tr>
      </thead>
      <tbody>
        {entries.length === 0 && (
          <tr><td colSpan={compact ? 5 : 10} style={{ color: 'var(--text-secondary)' }}>No submissions evaluated yet.</td></tr>
        )}
        {entries.map((t) => (
          <tr key={t.submission_id} style={{ background: t.team_id === highlightTeamId ? '#F0F7FF' : 'transparent' }}>
            <td style={{ fontWeight: '800', color: t.team_id === highlightTeamId ? '#2B7FFF' : 'inherit' }}>#{t.rank}</td>
            <td style={{ fontWeight: '700' }}>{t.team_name}</td>
            {!compact && <td style={{ color: 'var(--text-secondary)' }}>{t.tech_stack}</td>}
            <td style={{ fontWeight: '800', fontSize: '15px' }}>{t.score}</td>
            {!compact && <td style={{ color: 'var(--text-secondary)' }}>{t.parameter_scores?.technical_complexity ?? '—'}</td>}
            {!compact && <td style={{ color: 'var(--text-secondary)' }}>{t.parameter_scores?.innovation ?? '—'}</td>}
            {!compact && <td style={{ color: 'var(--text-secondary)' }}>{t.parameter_scores?.ui_ux ?? '—'}</td>}
            {!compact && <td style={{ color: 'var(--text-secondary)' }}>{t.parameter_scores?.business_impact ?? '—'}</td>}
            <td><span className={`pill-badge ${t.plagiarism_risk === 'CRITICAL' ? 'red' : t.plagiarism_risk === 'MEDIUM' ? 'amber' : 'green'}`}>{t.plagiarism_risk}</span></td>
            <td><span className="pill-badge blue">{t.status}</span></td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const ParamRow: React.FC<{ label: string; score: number }> = ({ label, score }) => (
  <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
      <span>{label}</span>
      <span style={{ fontWeight: '800' }}>{score}%</span>
    </div>
    <div style={{ height: '8px', background: '#F3F4F6', borderRadius: '99px', overflow: 'hidden' }}>
      <div style={{ width: `${Math.min(score, 100)}%`, height: '100%', background: '#2B7FFF', borderRadius: '99px' }} />
    </div>
  </div>
);

interface SubmitModalProps {
  hackathonId: string;
  teamId: string;
  onClose: () => void;
  onSubmitted: (sub: Submission) => void;
  onEvaluationTriggered: (taskId: string) => void;
}

const SubmitModal: React.FC<SubmitModalProps> = ({ hackathonId, teamId, onClose, onSubmitted, onEvaluationTriggered }) => {
  const [githubUrl, setGithubUrl] = useState('');
  const [techStack, setTechStack] = useState('');
  const [liveUrl, setLiveUrl] = useState('');
  const [readmeText, setReadmeText] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [pptFile, setPptFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [runEvalAfter, setRunEvalAfter] = useState(true);

  const submitAction = useAsyncAction(async () => {
    const form = new FormData();
    form.append('hackathon_id', hackathonId);
    form.append('team_id', teamId);
    if (githubUrl) form.append('github_url', githubUrl);
    if (techStack) form.append('tech_stack', techStack);
    if (liveUrl) form.append('live_url', liveUrl);
    if (readmeText) form.append('readme_text', readmeText);
    if (zipFile) form.append('zip_file', zipFile);
    if (pptFile) form.append('ppt_file', pptFile);
    if (videoFile) form.append('video_file', videoFile);

    const sub = await api.post<Submission>('/api/submissions/upload', form);
    onSubmitted(sub);

    if (runEvalAfter) {
      const task = await api.post<{ task_id: string }>(`/api/evaluation/evaluate/${sub.id}`);
      onEvaluationTriggered(task.task_id);
    }
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '8px' }}>Project Asset Submission</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Upload your GitHub repository, demo video, and PPT presentation.
        </p>

        <form onSubmit={(e) => { e.preventDefault(); submitAction.run(); }}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>GitHub Repository URL</label>
            <input type="text" className="search-input" style={{ width: '100%' }} value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Tech Stack Tags</label>
            <input type="text" className="search-input" style={{ width: '100%' }} value={techStack} onChange={(e) => setTechStack(e.target.value)} placeholder="React, FastAPI, Docker" />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Live Deployment URL</label>
            <input type="text" className="search-input" style={{ width: '100%' }} value={liveUrl} onChange={(e) => setLiveUrl(e.target.value)} />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>README / Project Description</label>
            <textarea className="search-input" style={{ width: '100%', height: '80px', borderRadius: '12px' }} value={readmeText} onChange={(e) => setReadmeText(e.target.value)} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <FileField label="ZIP Archive" accept=".zip" file={zipFile} onChange={setZipFile} />
            <FileField label="PPT (.pptx)" accept=".pptx" file={pptFile} onChange={setPptFile} />
            <FileField label="Demo Video (3-5 min)" accept="video/*" file={videoFile} onChange={setVideoFile} />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', marginBottom: '20px', cursor: 'pointer' }}>
            <input type="checkbox" checked={runEvalAfter} onChange={(e) => setRunEvalAfter(e.target.checked)} />
            Run AI evaluation immediately after submitting
          </label>

          {submitAction.error && <p style={{ color: '#EF4444', fontSize: '13px', marginBottom: '16px' }}>{submitAction.error}</p>}

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button type="button" className="role-btn" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={submitAction.isLoading}>
              {submitAction.isLoading ? 'Uploading…' : 'Confirm Submission'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const FileField: React.FC<{ label: string; accept: string; file: File | null; onChange: (f: File | null) => void }> = ({ label, accept, file, onChange }) => (
  <div>
    <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', marginBottom: '6px' }}>{label}</label>
    <div style={{ border: '2px dashed #E5E7EB', padding: '12px', borderRadius: '12px', textAlign: 'center' }}>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files?.[0] || null)}
        style={{ fontSize: '11px', width: '100%' }}
      />
      {file && <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>{file.name}</p>}
    </div>
  </div>
);
