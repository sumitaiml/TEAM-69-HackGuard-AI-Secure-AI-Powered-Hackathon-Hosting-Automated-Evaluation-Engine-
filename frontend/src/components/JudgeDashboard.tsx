import React, { useState } from 'react';
import { MetricCard } from './MetricCard';
import { FileText, ShieldCheck, Sliders, CheckCircle, Video } from 'lucide-react';

import type { HackathonItem } from '../App';

interface JudgeDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
}

export const JudgeDashboard: React.FC<JudgeDashboardProps> = ({ activeTab, setActiveTab, hackathons: _hackathons, selectedHackathonId: _selectedHackathonId }) => {
  const [activeReportTab, setActiveReportTab] = useState<'ai' | 'static' | 'docker' | 'video'>('ai');
  const [overrideScores, setOverrideScores] = useState({
    technical: 28,
    innovation: 18,
    ui_ux: 14,
    business_impact: 13,
    documentation: 9,
    presentation: 9,
  });
  const [justification, setJustification] = useState('Increased UI score by +2 points due to exceptional polished demonstration.');
  const [comments, setComments] = useState('Impressive implementation and clean architecture.');

  const handleScoreChange = (param: keyof typeof overrideScores, val: number) => {
    setOverrideScores((prev) => ({ ...prev, [param]: val }));
  };

  const calculatedTotal = Object.values(overrideScores).reduce((a, b) => a + b, 0);

  // 1. Full AI Report Audit View
  if (activeTab === 'report') {
    return (
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Multimodal AI Report Audit Reader</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Detailed AI report breakdown, static code checks, build logs, and video transcripts</p>
          </div>
          <span className="pill-badge blue">Auditing: Team Beta (ID: sub_c8f3)</span>
        </div>

        <div className="tabs-header">
          <button className={`tab-btn ${activeReportTab === 'ai' ? 'active' : ''}`} onClick={() => setActiveReportTab('ai')}>🤖 AI Summary</button>
          <button className={`tab-btn ${activeReportTab === 'static' ? 'active' : ''}`} onClick={() => setActiveReportTab('static')}>🛡️ Security & Static Code</button>
          <button className={`tab-btn ${activeReportTab === 'docker' ? 'active' : ''}`} onClick={() => setActiveReportTab('docker')}>🐳 Docker Sandbox Logs</button>
          <button className={`tab-btn ${activeReportTab === 'video' ? 'active' : ''}`} onClick={() => setActiveReportTab('video')}>🎥 Video Transcript (Whisper)</button>
        </div>

        {renderTabContent()}
      </div>
    );
  }

  // 2. Score Override Console View
  if (activeTab === 'override') {
    return (
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Manual Score Override Console</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Adjust baseline AI scores and supply mandatory justification notes.</p>
          </div>
          <span className="pill-badge blue">Final Adjusted Score: {calculatedTotal} / 100</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <JudgeSlider label="Technical Complexity (Max 30)" value={overrideScores.technical} max={30} onChange={(v) => handleScoreChange('technical', v)} />
            <JudgeSlider label="Innovation (Max 20)" value={overrideScores.innovation} max={20} onChange={(v) => handleScoreChange('innovation', v)} />
            <JudgeSlider label="UI/UX Design (Max 15)" value={overrideScores.ui_ux} max={15} onChange={(v) => handleScoreChange('ui_ux', v)} />
            <JudgeSlider label="Business Impact (Max 15)" value={overrideScores.business_impact} max={15} onChange={(v) => handleScoreChange('business_impact', v)} />
            <JudgeSlider label="Documentation (Max 10)" value={overrideScores.documentation} max={10} onChange={(v) => handleScoreChange('documentation', v)} />
            <JudgeSlider label="Presentation (Max 10)" value={overrideScores.presentation} max={10} onChange={(v) => handleScoreChange('presentation', v)} />
          </div>

          <div style={{ background: '#F9FAFB', padding: '24px', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>
                Mandatory Justification Notes (Required for Override)
              </label>
              <textarea
                className="search-input"
                style={{ width: '100%', height: '80px', borderRadius: '12px' }}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>
                Qualitative Mentor Comments (Participant Facing)
              </label>
              <textarea
                className="search-input"
                style={{ width: '100%', height: '70px', borderRadius: '12px' }}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
              />
            </div>

            <button className="btn-primary" style={{ width: '100%', marginTop: 'auto' }} onClick={() => alert('Score override saved!')}>
              <CheckCircle size={16} /> Save Score Override & Approve Project
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 3. Default Overview View
  return (
    <div>
      {/* Top Hero Row */}
      <div className="metrics-row">
        <MetricCard
          label="Pending Reviews"
          value="8 Left"
          subText="8 of 25 Reviews Completed"
          variant="ice-blue"
          badge="In Progress"
          badgeColor="blue"
          icon={<FileText size={22} style={{ color: '#2B7FFF' }} />}
        />

        <MetricCard
          label="AI Confidence Score"
          value="94%"
          subText="Low Score Variance"
          variant="mint-green"
          badge="High Accuracy"
          badgeColor="green"
          icon={<ShieldCheck size={22} style={{ color: '#10B981' }} />}
        />

        <MetricCard
          label="Overridden Scores"
          value="2 Teams"
          subText="Manual Adjustments Logged"
          variant="lavender"
          badge="Audited"
          badgeColor="blue"
          icon={<Sliders size={22} style={{ color: '#8B5CF6' }} />}
        />

        <MetricCard
          label="Active Audit Focus"
          value="Team Beta"
          subText="Rank #4 Entry"
          variant="cream-yellow"
          badge="Active Queue"
          badgeColor="amber"
          icon={<CheckCircle size={22} style={{ color: '#F59E0B' }} />}
        />
      </div>

      {/* Main Content Grid */}
      <div className="dashboard-grid">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Multimodal AI Evaluation Reader</h3>
            <button className="role-btn" onClick={() => setActiveTab('report')}>Expand Full Reader →</button>
          </div>

          <div className="tabs-header">
            <button className={`tab-btn ${activeReportTab === 'ai' ? 'active' : ''}`} onClick={() => setActiveReportTab('ai')}>🤖 AI Summary</button>
            <button className={`tab-btn ${activeReportTab === 'static' ? 'active' : ''}`} onClick={() => setActiveReportTab('static')}>🛡️ Security & Static Code</button>
            <button className={`tab-btn ${activeReportTab === 'docker' ? 'active' : ''}`} onClick={() => setActiveReportTab('docker')}>🐳 Docker Sandbox Logs</button>
            <button className={`tab-btn ${activeReportTab === 'video' ? 'active' : ''}`} onClick={() => setActiveReportTab('video')}>🎥 Video Transcript (Whisper)</button>
          </div>

          {renderTabContent()}
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Score Override Console</h3>
            <button className="role-btn" onClick={() => setActiveTab('override')}>Full Sliders →</button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' }}>
            <JudgeSlider label="Technical Complexity (Max 30)" value={overrideScores.technical} max={30} onChange={(v) => handleScoreChange('technical', v)} />
            <JudgeSlider label="Innovation (Max 20)" value={overrideScores.innovation} max={20} onChange={(v) => handleScoreChange('innovation', v)} />
            <JudgeSlider label="UI/UX Design (Max 15)" value={overrideScores.ui_ux} max={15} onChange={(v) => handleScoreChange('ui_ux', v)} />
            <JudgeSlider label="Business Impact (Max 15)" value={overrideScores.business_impact} max={15} onChange={(v) => handleScoreChange('business_impact', v)} />
          </div>

          <button className="btn-primary" style={{ width: '100%' }} onClick={() => alert('Score override saved!')}>
            <CheckCircle size={16} /> Save Score Override
          </button>
        </div>
      </div>
    </div>
  );

  function renderTabContent() {
    if (activeReportTab === 'ai') {
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: '#F0F7FF', padding: '16px', borderRadius: '16px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: '800', color: '#1E40AF', marginBottom: '6px' }}>AI Key Evaluation Strengths</h4>
            <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#1F2937' }}>
              <li>Microservices architecture with clean modular code structure (FastAPI + React).</li>
              <li>Zero hardcoded credentials detected during static analysis.</li>
              <li>Docker container unit tests passed 100% (12/12 passed).</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: '800', marginBottom: '6px' }}>AI Improvement Recommendations</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Consider adding unit test coverage for edge case handling in authentication router and rate-limiting middleware.
            </p>
          </div>
        </div>
      );
    }
    if (activeReportTab === 'static') {
      return (
        <div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <span className="pill-badge green">Semgrep: Clean</span>
            <span className="pill-badge green">ESLint: 0 Errors</span>
            <span className="pill-badge blue">Pylint: 9.2/10</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            No high or critical severity vulnerabilities were found during static code inspection.
          </p>
        </div>
      );
    }
    if (activeReportTab === 'docker') {
      return (
        <div style={{ background: '#1E1F24', color: '#10B981', padding: '16px', borderRadius: '16px', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.6' }}>
          <div>[INFO] Spawning isolated Docker container (ID: c8f3a921)...</div>
          <div>[INFO] Policy applied: --read-only rootfs, --memory=512m, --cpus=1.0, --network=none post-install.</div>
          <div>[BUILD] Executing build command: `npm run build`... SUCCESS (2.4s)</div>
          <div>[TEST] Running unit tests: 12 passed, 0 failed.</div>
          <div>[METRICS] Max Memory: 142 MB / 512 MB | CPU Usage: 12.4% avg.</div>
          <div>[CONTAINER] Execution finished. Container destroyed.</div>
        </div>
      );
    }
    return (
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', background: '#F9FAFB', padding: '16px', borderRadius: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '800', color: '#111827', marginBottom: '8px' }}>
          <Video size={16} /> Whisper Speech-to-Text Transcript (Feature Coverage: 95%)
        </div>
        "Welcome to Team Beta's presentation of HackGuard AI. Today we are demonstrating our secure Docker sandbox execution engine, AST plagiarism detection algorithm, and real-time leaderboards..."
      </div>
    );
  }
};

const JudgeSlider: React.FC<{ label: string; value: number; max: number; onChange: (v: number) => void }> = ({ label, value, max, onChange }) => (
  <div className="slider-group">
    <div className="slider-label">
      <span style={{ fontSize: '13px' }}>{label}</span>
      <span style={{ fontWeight: '800', color: '#2B7FFF' }}>{value} / {max}</span>
    </div>
    <input
      type="range"
      min="0"
      max={max}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className="range-input"
    />
  </div>
);
