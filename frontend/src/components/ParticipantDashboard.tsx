import React, { useState } from 'react';
import { MetricCard } from './MetricCard';
import { GitBranch, ShieldCheck, Trophy, Rocket, Upload, Users, FileText, UserPlus, ExternalLink, Code } from 'lucide-react';

import { HackathonItem } from '../App';

interface ParticipantDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
}

export const ParticipantDashboard: React.FC<ParticipantDashboardProps> = ({ activeTab, setActiveTab, hackathons: _hackathons, selectedHackathonId: _selectedHackathonId }) => {
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [githubUrl, setGithubUrl] = useState('https://github.com/alphacoders/ai-solution');
  const [techStack, setTechStack] = useState('React, FastAPI, Docker');
  const [inviteCodeInput, setInviteCodeInput] = useState('');
  const [newMemberEmail, setNewMemberEmail] = useState('');

  const teams = [
    { rank: 1, name: 'CyberCrew', score: 92.4, status: 'Verified & Clean', risk: '0.1%', tech: 'PyTorch, Next.js' },
    { rank: 2, name: 'AI-Knights', score: 90.1, status: 'Verified & Clean', risk: '0.4%', tech: 'FastAPI, Vue' },
    { rank: 3, name: 'AlphaCoders (You)', score: 88.5, status: 'Verified & Clean', risk: '0.2%', tech: 'React, FastAPI' },
    { rank: 4, name: 'NeuralNet', score: 86.0, status: 'Verified & Clean', risk: '1.2%', tech: 'TensorFlow, Flask' },
    { rank: 5, name: 'QuantumBytes', score: 84.2, status: 'Audit Pending', risk: '3.5%', tech: 'Node.js, Express' },
  ];

  const teamMembers = [
    { name: 'Zoia M.', role: 'Team Leader / Frontend', email: 'zoia.m@alphacoders.io', status: 'Active' },
    { name: 'Alex Rivera', role: 'Backend / FastAPI', email: 'alex.r@alphacoders.io', status: 'Active' },
    { name: 'Elena Rostova', role: 'AI / ML Engineer', email: 'elena.r@alphacoders.io', status: 'Active' },
  ];

  // 1. Team Management View
  if (activeTab === 'team') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Team Management — AlphaCoders</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Manage team members, roles, and invite codes.</p>
            </div>
            <div style={{ background: '#E8F2FF', padding: '8px 16px', borderRadius: '12px', fontSize: '13px', fontWeight: '700', color: '#2B7FFF' }}>
              Invite Code: <span style={{ fontFamily: 'monospace', fontSize: '15px' }}>CYBER6</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
            {/* Members Table */}
            <div>
              <h4 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>Current Members (3/4)</h4>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Role</th>
                      <th>Email</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teamMembers.map((m, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: '700' }}>{m.name}</td>
                        <td>{m.role}</td>
                        <td style={{ color: 'var(--text-secondary)' }}>{m.email}</td>
                        <td><span className="pill-badge green">{m.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Invite & Join Box */}
            <div style={{ background: '#F9FAFB', padding: '20px', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '8px' }}>Invite Teammate</h4>
                <input
                  type="email"
                  placeholder="teammate@email.com"
                  className="search-input"
                  style={{ width: '100%', marginBottom: '8px' }}
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                />
                <button className="btn-primary" style={{ width: '100%', fontSize: '13px' }} onClick={() => alert(`Invite sent to ${newMemberEmail}`)}>
                  <UserPlus size={14} /> Send Invitation
                </button>
              </div>

              <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: '16px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: '700', marginBottom: '8px' }}>Join Another Team</h4>
                <input
                  type="text"
                  placeholder="Enter 6-char Invite Code"
                  className="search-input"
                  style={{ width: '100%', marginBottom: '8px' }}
                  value={inviteCodeInput}
                  onChange={(e) => setInviteCodeInput(e.target.value)}
                />
                <button className="role-btn" style={{ width: '100%', background: '#18191C', color: '#FFFFFF' }} onClick={() => alert('Joined Team!')}>
                  Join Team
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. Project Submission View
  if (activeTab === 'submit') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Project Submission Hub</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Upload your GitHub repo link, ZIP archive, PPT slides, and demo video.</p>
            </div>
            <button className="btn-primary" onClick={() => setShowSubmitModal(true)}>
              <Upload size={16} /> New Submission Update
            </button>
          </div>

          {/* Current Active Submission Details */}
          <div style={{ background: '#F0F7FF', borderRadius: '16px', padding: '24px', border: '1px solid #BFDBFE', marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <span className="pill-badge blue">Active Submission (ID: sub_c8f3)</span>
              <span style={{ fontSize: '12px', color: '#1E40AF', fontWeight: '600' }}>Submitted 2h ago</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', fontSize: '14px' }}>
              <div><strong>GitHub URL:</strong> <br /><a href={githubUrl} target="_blank" rel="noreferrer" style={{ color: '#2B7FFF' }}>{githubUrl}</a></div>
              <div><strong>Tech Stack:</strong> <br />{techStack}</div>
              <div><strong>Build Status:</strong> <br /><span className="pill-badge green">Docker Passed</span></div>
            </div>
          </div>

          <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '12px' }}>Past Submission History</h4>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Submitted At</th>
                  <th>Assets Included</th>
                  <th>Plagiarism Risk</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ fontWeight: '700' }}>v1.2 (Latest)</td>
                  <td>Today, 20:45</td>
                  <td>GitHub, PPT, Video MP4</td>
                  <td><span className="pill-badge green">0.2% Low</span></td>
                  <td><span className="pill-badge blue">Evaluated (88.5)</span></td>
                </tr>
                <tr>
                  <td style={{ fontWeight: '700' }}>v1.0 (Draft)</td>
                  <td>Yesterday, 14:20</td>
                  <td>GitHub Repo Only</td>
                  <td><span className="pill-badge green">0.1% Low</span></td>
                  <td><span className="pill-badge amber">Superceded</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {showSubmitModal && renderSubmitModal()}
      </div>
    );
  }

  // 3. AI Report View
  if (activeTab === 'report') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>AI Evaluation Breakdown Report</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Detailed feedback generated by HackGuard AI Engine.</p>
            </div>
            <div style={{ fontSize: '24px', fontWeight: '800', color: '#2B7FFF' }}>88.5 / 100</div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <ParamRow label="Technical Complexity (30%)" score={90} />
              <ParamRow label="Innovation (20%)" score={88} />
              <ParamRow label="UI/UX Design (15%)" score={92} />
              <ParamRow label="Business Impact (15%)" score={85} />
              <ParamRow label="Documentation (10%)" score={94} />
              <ParamRow label="Presentation (10%)" score={86} />
            </div>

            <div style={{ background: '#F9FAFB', padding: '20px', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h4 style={{ fontSize: '15px', fontWeight: '700', color: '#111827' }}>AI Feedback Highlights</h4>
              <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#374151' }}>
                <li>FastAPI backend architecture is well modularized with zero security vulnerabilities.</li>
                <li>React TypeScript frontend exhibits clean component decoupling and sleek design.</li>
                <li>Docker sandbox unit test execution passed 100% (12/12 tests passed).</li>
                <li>Whisper speech-to-text confirmed 95% feature coverage against presentation claims.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 4. Live Leaderboard View
  if (activeTab === 'leaderboard') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Official Hackathon Live Leaderboard</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Complete list of 142 competing teams ranked by AI score.</p>
            </div>
            <span className="pill-badge green">🟢 Live Sync</span>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Team Name</th>
                  <th>Tech Stack</th>
                  <th>AI Score</th>
                  <th>Plagiarism Risk</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((t) => (
                  <tr key={t.rank} style={{ background: t.rank === 3 ? '#F0F7FF' : 'transparent' }}>
                    <td style={{ fontWeight: '800', color: t.rank === 3 ? '#2B7FFF' : 'inherit' }}>#{t.rank}</td>
                    <td style={{ fontWeight: '700' }}>{t.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{t.tech}</td>
                    <td style={{ fontWeight: '800', fontSize: '15px' }}>{t.score}</td>
                    <td><span className="pill-badge green">{t.risk}</span></td>
                    <td><span className="pill-badge blue">{t.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // 5. Default Overview View
  return (
    <div>
      {/* Top Hero Row */}
      <div className="metrics-row">
        <div className="metric-card ice-blue">
          <div className="metric-card-header">
            <span className="metric-label">Overall AI Evaluation Score</span>
            <span className="pill-badge blue">Evaluated</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span className="metric-value" style={{ color: '#2B7FFF' }}>88.5</span>
              <span style={{ fontSize: '18px', fontWeight: '700', color: '#6B7280' }}>/ 100</span>
            </div>
            <div style={{ height: '36px', marginTop: '8px' }}>
              <svg width="100%" height="100%" viewBox="0 0 200 40" preserveAspectRatio="none">
                <path d="M 0 30 Q 40 10, 80 25 T 160 10 T 200 5" fill="none" stroke="#2B7FFF" strokeWidth="3" />
              </svg>
            </div>
          </div>
        </div>

        <MetricCard
          label="Submission Status"
          value="Verified"
          subText="Git Synced (main)"
          variant="lavender"
          badge="Build Passed"
          badgeColor="blue"
          icon={<GitBranch size={22} style={{ color: '#8B5CF6' }} />}
        />

        <MetricCard
          label="Plagiarism Risk"
          value="0.2%"
          subText="AST Code Check Passed"
          variant="mint-green"
          badge="Low Risk"
          badgeColor="green"
          icon={<ShieldCheck size={22} style={{ color: '#10B981' }} />}
        />

        <MetricCard
          label="Leaderboard Rank"
          value="#3 of 142"
          subText="▲ +2 positions rise"
          variant="cream-yellow"
          badge="Top 3%"
          badgeColor="amber"
          icon={<Trophy size={22} style={{ color: '#F59E0B' }} />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Live Hackathon Leaderboard</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Top competing teams & dynamic AI scores</p>
            </div>
            <button className="role-btn" onClick={() => setActiveTab('leaderboard')}>View Full Ranks →</button>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Team Name</th>
                  <th>AI Score</th>
                  <th>Plagiarism Risk</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {teams.slice(0, 4).map((team) => (
                  <tr key={team.rank} style={{ backgroundColor: team.rank === 3 ? '#F0F7FF' : 'transparent' }}>
                    <td><span style={{ fontWeight: '800', color: team.rank === 3 ? '#2B7FFF' : 'inherit' }}>#{team.rank}</span></td>
                    <td><div style={{ fontWeight: '700' }}>{team.name}</div></td>
                    <td><span style={{ fontWeight: '800', fontSize: '15px' }}>{team.score}</span></td>
                    <td><span className="pill-badge green">{team.risk}</span></td>
                    <td><span className="pill-badge blue">{team.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="dark-banner">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#60A5FA', fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', marginBottom: '8px' }}>
              <Rocket size={16} /> Submission Deadline Notice
            </div>
            <h3 className="dark-banner-title">Submit Updated Code & Video Demo!</h3>
            <p className="dark-banner-sub">
              Final submission window closes in <strong>04h 12m</strong>. Run Docker Sandbox validation before locking.
            </p>
            <button className="btn-primary" onClick={() => setShowSubmitModal(true)}>
              <Upload size={16} /> Submit Project Now
            </button>
          </div>

          <div className="card">
            <h4 style={{ fontSize: '16px', fontWeight: '800', marginBottom: '16px' }}>Parameter Score Breakdown</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <ParamRow label="Technical Complexity (30%)" score={90} />
              <ParamRow label="Innovation (20%)" score={88} />
              <ParamRow label="UI/UX (15%)" score={92} />
              <ParamRow label="Business Impact (15%)" score={85} />
              <ParamRow label="Documentation (10%)" score={94} />
              <ParamRow label="Presentation (10%)" score={86} />
            </div>
          </div>
        </div>
      </div>

      {showSubmitModal && renderSubmitModal()}
    </div>
  );

  function renderSubmitModal() {
    return (
      <div className="modal-overlay" onClick={() => setShowSubmitModal(false)}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <h3 style={{ fontSize: '20px', fontWeight: '800', marginBottom: '8px' }}>Project Asset Submission</h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Upload your GitHub repository, demo video, and PPT presentation.
          </p>

          <form onSubmit={(e) => { e.preventDefault(); alert('Submission updated!'); setShowSubmitModal(false); }}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>GitHub Repository URL</label>
              <input
                type="text"
                className="search-input"
                style={{ width: '100%' }}
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Tech Stack Tags</label>
              <input
                type="text"
                className="search-input"
                style={{ width: '100%' }}
                value={techStack}
                onChange={(e) => setTechStack(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Upload PPT / Demo Video</label>
              <div style={{ border: '2px dashed #E5E7EB', padding: '24px', borderRadius: '16px', textAlign: 'center', cursor: 'pointer' }}>
                <Upload size={24} style={{ color: '#9CA3AF', marginBottom: '8px' }} />
                <p style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)' }}>Drag & drop presentation slides or video file</p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button type="button" className="role-btn" onClick={() => setShowSubmitModal(false)}>Cancel</button>
              <button type="submit" className="btn-primary">Confirm Submission</button>
            </div>
          </form>
        </div>
      </div>
    );
  }
};

const ParamRow: React.FC<{ label: string; score: number }> = ({ label, score }) => (
  <div>
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: '600', marginBottom: '4px' }}>
      <span>{label}</span>
      <span style={{ fontWeight: '800' }}>{score}%</span>
    </div>
    <div style={{ height: '8px', background: '#F3F4F6', borderRadius: '99px', overflow: 'hidden' }}>
      <div style={{ width: `${score}%`, height: '100%', background: '#2B7FFF', borderRadius: '99px' }} />
    </div>
  </div>
);
