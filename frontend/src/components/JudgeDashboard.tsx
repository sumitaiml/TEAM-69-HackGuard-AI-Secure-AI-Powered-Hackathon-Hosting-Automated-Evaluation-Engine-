import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MetricCard } from './MetricCard';
import { FileText, ShieldCheck, Sliders, CheckCircle, Video, Calendar } from 'lucide-react';

import type { HackathonItem, LeaderboardEntry, EvaluationReport, RubricWeights } from '../lib/types';
import { api } from '../lib/apiClient';
import { useAsyncAction } from '../hooks/useAsyncAction';

interface JudgeDashboardProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
}

const DEFAULT_WEIGHTS: RubricWeights = {
  technical_complexity: 30, innovation: 20, ui_ux: 15, business_impact: 15, documentation: 10, presentation: 10,
};

export const JudgeDashboard: React.FC<JudgeDashboardProps> = ({
  activeTab, setActiveTab, hackathons, selectedHackathonId, setSelectedHackathonId,
}) => {
  const [activeReportTab, setActiveReportTab] = useState<'ai' | 'static' | 'docker' | 'video'>('ai');
  const [queue, setQueue] = useState<LeaderboardEntry[]>([]);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(null);
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);

  const [overrideScores, setOverrideScores] = useState<RubricWeights>(DEFAULT_WEIGHTS);
  const [justification, setJustification] = useState('');
  const [comments, setComments] = useState('');

  const activeHackathon = hackathons.find((h) => h.id === selectedHackathonId) || null;
  const weightCaps = activeHackathon?.rubric_weights_json || DEFAULT_WEIGHTS;

  const loadQueue = useCallback(() => {
    if (!selectedHackathonId) { setQueue([]); return; }
    api.get<LeaderboardEntry[]>(`/api/evaluation/leaderboard/${selectedHackathonId}`).then((entries) => {
      setQueue(entries);
      setSelectedSubmissionId((prev) => (prev && entries.some((e) => e.submission_id === prev)) ? prev : (entries[0]?.submission_id || null));
    }).catch(() => setQueue([]));
  }, [selectedHackathonId]);
  useEffect(() => { loadQueue(); }, [loadQueue]);

  const loadReport = useCallback(() => {
    if (!selectedSubmissionId) { setReport(null); return; }
    setReportError(null);
    api.get<EvaluationReport>(`/api/evaluation/report/${selectedSubmissionId}`)
      .then((r) => {
        setReport(r);
        const scores = (r.ai_scores_json?.parameter_scores || {}) as Partial<RubricWeights>;
        setOverrideScores({ ...DEFAULT_WEIGHTS, ...scores });
      })
      .catch(() => { setReport(null); setReportError('This submission has not been evaluated yet.'); });
  }, [selectedSubmissionId]);
  useEffect(() => { loadReport(); }, [loadReport]);

  const selectedEntry = useMemo(() => queue.find((q) => q.submission_id === selectedSubmissionId) || null, [queue, selectedSubmissionId]);

  const handleScoreChange = (param: keyof RubricWeights, val: number) => {
    setOverrideScores((prev) => ({ ...prev, [param]: val }));
  };
  const calculatedTotal = Math.round(
    Object.entries(overrideScores).reduce((sum, [key, val]) => sum + val * ((weightCaps[key as keyof RubricWeights] || 0) / 100), 0)
  );

  const submitOverride = useAsyncAction(async () => {
    if (!report) return;
    if (justification.trim().length < 5) throw new Error('Justification must be at least 5 characters.');
    const updated = await api.post<EvaluationReport>(`/api/evaluation/override/${report.id}`, {
      parameter_scores: overrideScores,
      justification_notes: justification,
      judge_comments: comments || undefined,
    });
    setReport(updated);
    loadQueue();
  });

  // ---- 1. Full AI Report Audit View ----
  if (activeTab === 'report') {
    return (
      <div className="card">
        <ReportHeader hackathons={hackathons} selectedHackathonId={selectedHackathonId} setSelectedHackathonId={setSelectedHackathonId} queue={queue} selectedSubmissionId={selectedSubmissionId} setSelectedSubmissionId={setSelectedSubmissionId} />
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

  // ---- 2. Score Override Console View ----
  if (activeTab === 'override') {
    return (
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Manual Score Override Console</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{selectedEntry ? `Reviewing: ${selectedEntry.team_name}` : 'Select a submission from the report tab first.'}</p>
          </div>
          <span className="pill-badge blue">Weighted Total: {calculatedTotal} / 100</span>
        </div>

        {!report ? (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{reportError || 'No submission selected.'}</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {(Object.keys(DEFAULT_WEIGHTS) as (keyof RubricWeights)[]).map((key) => (
                <JudgeSlider key={key} label={`${formatLabel(key)} (Max ${weightCaps[key]})`} value={overrideScores[key]} max={weightCaps[key]} onChange={(v) => handleScoreChange(key, v)} />
              ))}
            </div>

            <div style={{ background: '#F9FAFB', padding: '24px', borderRadius: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Mandatory Justification Notes (Required for Override)</label>
                <textarea className="search-input" style={{ width: '100%', height: '80px', borderRadius: '12px' }} value={justification} onChange={(e) => setJustification(e.target.value)} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: '700', marginBottom: '6px' }}>Qualitative Mentor Comments (Participant Facing)</label>
                <textarea className="search-input" style={{ width: '100%', height: '70px', borderRadius: '12px' }} value={comments} onChange={(e) => setComments(e.target.value)} />
              </div>
              {submitOverride.error && <p style={{ color: '#EF4444', fontSize: '13px' }}>{submitOverride.error}</p>}
              {submitOverride.successMessage && <p style={{ color: '#10B981', fontSize: '13px' }}>{submitOverride.successMessage}</p>}
              <button
                className="btn-primary"
                style={{ width: '100%', marginTop: 'auto' }}
                disabled={submitOverride.isLoading}
                onClick={() => submitOverride.run().then(() => submitOverride.setSuccessMessage('Override saved.'))}
              >
                <CheckCircle size={16} /> {submitOverride.isLoading ? 'Saving…' : 'Save Score Override & Approve Project'}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ---- 3. Default Overview View ----
  const pendingCount = queue.filter((q) => q.status !== 'completed').length;

  return (
    <div>
      <div className="metrics-row">
        <MetricCard
          label="Submissions in Queue"
          value={`${queue.length} Total`}
          subText={`${pendingCount} pending evaluation`}
          variant="ice-blue"
          badge="Queue"
          badgeColor="blue"
          icon={<FileText size={22} style={{ color: '#2B7FFF' }} />}
        />
        <MetricCard
          label="Selected Hackathon"
          value={activeHackathon?.title || 'None'}
          subText={`${hackathons.length} events total`}
          variant="mint-green"
          badge={activeHackathon?.is_active ? 'Active' : undefined}
          badgeColor="green"
          icon={<Calendar size={22} style={{ color: '#10B981' }} />}
        />
        <MetricCard
          label="Reviewing"
          value={selectedEntry ? selectedEntry.team_name : 'None'}
          subText={selectedEntry ? `Rank #${selectedEntry.rank}` : 'Pick from the report tab'}
          variant="lavender"
          badge={report?.judge_override_json ? 'Overridden' : undefined}
          badgeColor="blue"
          icon={<Sliders size={22} style={{ color: '#8B5CF6' }} />}
        />
        <MetricCard
          label="AI Confidence"
          value={report?.ai_scores_json?.ai_evaluation_degraded ? 'Degraded' : 'Nominal'}
          subText={report?.ai_scores_json?.ai_evaluation_degraded ? 'Manual review suggested' : 'Gemini scoring succeeded'}
          variant="cream-yellow"
          badge={report?.ai_scores_json?.ai_evaluation_degraded ? 'Check' : 'OK'}
          badgeColor={report?.ai_scores_json?.ai_evaluation_degraded ? 'amber' : 'green'}
          icon={<ShieldCheck size={22} style={{ color: '#F59E0B' }} />}
        />
      </div>

      <div className="dashboard-grid">
        <div className="card">
          <ReportHeader hackathons={hackathons} selectedHackathonId={selectedHackathonId} setSelectedHackathonId={setSelectedHackathonId} queue={queue} selectedSubmissionId={selectedSubmissionId} setSelectedSubmissionId={setSelectedSubmissionId} compact />
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

          {report ? (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '20px' }}>
                {(['technical_complexity', 'innovation', 'ui_ux', 'business_impact'] as (keyof RubricWeights)[]).map((key) => (
                  <JudgeSlider key={key} label={`${formatLabel(key)} (Max ${weightCaps[key]})`} value={overrideScores[key]} max={weightCaps[key]} onChange={(v) => handleScoreChange(key, v)} />
                ))}
              </div>
              <button className="btn-primary" style={{ width: '100%' }} onClick={() => setActiveTab('override')}>
                <CheckCircle size={16} /> Open Full Override Console
              </button>
            </>
          ) : (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{reportError || 'No submission selected.'}</p>
          )}
        </div>
      </div>
    </div>
  );

  function renderTabContent() {
    if (!report) {
      return <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{reportError || 'No submission selected.'}</p>;
    }

    if (activeReportTab === 'ai') {
      const scores = report.ai_scores_json;
      const repoVerification = report.repo_verification_json;
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: '#F0F7FF', padding: '16px', borderRadius: '16px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: '800', color: '#1E40AF', marginBottom: '6px' }}>AI Key Evaluation Strengths</h4>
            <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#1F2937' }}>
              {(scores?.ai_feedback || []).map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </div>
          {(scores?.improvement_suggestions?.length ?? 0) > 0 && (
            <div>
              <h4 style={{ fontSize: '14px', fontWeight: '800', marginBottom: '6px' }}>AI Improvement Recommendations</h4>
              <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                {scores!.improvement_suggestions.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {repoVerification?.status === 'completed' && (
            <div style={{ background: '#F9FAFB', padding: '16px', borderRadius: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: '800' }}>README Claim Verification</h4>
                <span className="pill-badge blue">{Math.round(repoVerification.confidence * 100)}% confidence</span>
              </div>
              {repoVerification.architecture_summary && (
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '10px' }}>{repoVerification.architecture_summary}</p>
              )}
              {repoVerification.claims_checked.length > 0 && (
                <ul style={{ paddingLeft: '20px', fontSize: '12px', lineHeight: '1.6', color: '#374151', marginBottom: '10px' }}>
                  {repoVerification.claims_checked.map((c, i) => (
                    <li key={i}>
                      <span className={`pill-badge ${c.verdict === 'confirmed' ? 'green' : c.verdict === 'contradicted' ? 'red' : 'blue'}`} style={{ marginRight: '6px' }}>{c.verdict}</span>
                      {c.claim} — <span style={{ color: 'var(--text-secondary)' }}>{c.evidence}</span>
                    </li>
                  ))}
                </ul>
              )}
              {repoVerification.red_flags.length > 0 && (
                <>
                  <div style={{ fontSize: '12px', fontWeight: '800', color: '#B45309', marginBottom: '4px' }}>Red Flags</div>
                  <ul style={{ paddingLeft: '20px', fontSize: '12px', color: '#B45309' }}>
                    {repoVerification.red_flags.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </>
              )}
            </div>
          )}
          {scores?.pitch_deck_analysis?.status === 'completed' && (
            <div style={{ background: '#F9FAFB', padding: '16px', borderRadius: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: '800' }}>Pitch Deck Breakdown</h4>
                <span className="pill-badge blue">{Math.round(scores.pitch_deck_analysis.overall_narrative_score)}/100 narrative</span>
              </div>
              <ul style={{ paddingLeft: '20px', fontSize: '12px', lineHeight: '1.6', color: '#374151' }}>
                {scores.pitch_deck_analysis.slides.map((s) => (
                  <li key={s.slide_number}>
                    Slide #{s.slide_number} <span className="pill-badge blue">{s.narrative_role}</span> {Math.round(s.clarity_score)}% clarity — <span style={{ color: 'var(--text-secondary)' }}>{s.notes}</span>
                  </li>
                ))}
              </ul>
              {scores.pitch_deck_analysis.missing_narrative_elements.length > 0 && (
                <p style={{ fontSize: '12px', color: '#B45309', marginTop: '8px' }}>
                  Missing: {scores.pitch_deck_analysis.missing_narrative_elements.join(', ')}
                </p>
              )}
            </div>
          )}
        </div>
      );
    }

    if (activeReportTab === 'static') {
      const staticReport = report.static_analysis_json;
      const tools: string[] = staticReport?.tools_executed || [];
      const vulns: any[] = staticReport?.security_vulnerabilities || [];
      const aiDetection = staticReport?.ai_generated_code_detection;
      return (
        <div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {tools.length === 0 && <span className="pill-badge amber">{staticReport?.reason || 'No source code analyzed'}</span>}
            {tools.map((t) => <span key={t} className="pill-badge blue">{t}</span>)}
          </div>
          {vulns.length === 0 ? (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No security vulnerabilities were found during static code inspection.</p>
          ) : (
            <ul style={{ paddingLeft: '20px', fontSize: '13px', lineHeight: '1.6', color: '#374151' }}>
              {vulns.map((v, i) => <li key={i}><strong>{v.tool}</strong> [{v.severity}] {v.message} ({v.path}:{v.line})</li>)}
            </ul>
          )}
          {aiDetection?.status === 'completed' && (
            <div style={{ marginTop: '16px', background: '#F9FAFB', borderRadius: '12px', padding: '12px 16px' }}>
              <div style={{ fontWeight: '800', fontSize: '13px', marginBottom: '4px' }}>
                AI-Generated Code Detection: <span className={`pill-badge ${aiDetection.risk_level === 'HIGH' ? 'red' : aiDetection.risk_level === 'MEDIUM' ? 'amber' : 'green'}`}>{aiDetection.risk_level}</span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Estimated {aiDetection.estimated_ai_usage_percentage}% likelihood (confidence {Math.round((aiDetection.confidence ?? 0) * 100)}%) - heuristic signal from comment density, naming patterns, and boilerplate phrasing, not proof.
              </p>
            </div>
          )}
        </div>
      );
    }

    if (activeReportTab === 'docker') {
      const sandbox = report.static_analysis_json?.sandbox_execution;
      const logs: string[] = sandbox?.execution_logs || [];
      return (
        <div>
          {sandbox?.status === 'completed' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginBottom: '12px' }}>
              <MiniStat label="Build" value={sandbox.build_status} />
              <MiniStat label="Tests Passed" value={`${sandbox.unit_tests_passed ?? 0}`} />
              <MiniStat label="Tests Failed" value={`${sandbox.unit_tests_failed ?? 0}`} />
              <MiniStat label="Peak Memory" value={`${sandbox.peak_memory_mb ?? 0} MB`} />
              <MiniStat label="Avg CPU" value={`${sandbox.avg_cpu_percent ?? 0}%`} />
            </div>
          )}
          <div style={{ background: '#1E1F24', color: '#10B981', padding: '16px', borderRadius: '16px', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.6', maxHeight: '260px', overflowY: 'auto' }}>
            {logs.length === 0 ? <div>{sandbox?.reason || 'No sandbox execution recorded.'}</div> : logs.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        </div>
      );
    }

    const transcript = report.ai_scores_json?.whisper_transcript;
    return (
      <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6', background: '#F9FAFB', padding: '16px', borderRadius: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: '800', color: '#111827', marginBottom: '8px' }}>
          <Video size={16} /> Whisper Speech-to-Text Transcript
        </div>
        {transcript?.transcript || transcript?.reason || 'No demo video was submitted.'}
      </div>
    );
  }
};

const MiniStat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div style={{ background: '#F9FAFB', borderRadius: '10px', padding: '8px 10px', textAlign: 'center' }}>
    <div style={{ fontSize: '10px', fontWeight: '700', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{label}</div>
    <div style={{ fontSize: '14px', fontWeight: '800', color: '#111827' }}>{value}</div>
  </div>
);

function formatLabel(key: string): string {
  return key.split('_').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');
}

interface ReportHeaderProps {
  hackathons: HackathonItem[];
  selectedHackathonId: string;
  setSelectedHackathonId: (id: string) => void;
  queue: LeaderboardEntry[];
  selectedSubmissionId: string | null;
  setSelectedSubmissionId: (id: string) => void;
  compact?: boolean;
}

const ReportHeader: React.FC<ReportHeaderProps> = ({ hackathons, selectedHackathonId, setSelectedHackathonId, queue, selectedSubmissionId, setSelectedSubmissionId, compact }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: compact ? '12px' : '20px', flexWrap: 'wrap', gap: '12px' }}>
    {!compact && (
      <div>
        <h3 style={{ fontSize: '20px', fontWeight: '800' }}>Multimodal AI Report Audit Reader</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Static code checks, sandbox logs, and video transcripts</p>
      </div>
    )}
    <div style={{ display: 'flex', gap: '8px' }}>
      <select className="hackathon-select" value={selectedHackathonId} onChange={(e) => setSelectedHackathonId(e.target.value)}>
        {hackathons.length === 0 && <option value="">No hackathons</option>}
        {hackathons.map((h) => <option key={h.id} value={h.id}>{h.title}</option>)}
      </select>
      <select className="hackathon-select" value={selectedSubmissionId || ''} onChange={(e) => setSelectedSubmissionId(e.target.value)}>
        {queue.length === 0 && <option value="">No submissions</option>}
        {queue.map((q) => <option key={q.submission_id} value={q.submission_id}>{q.team_name} (#{q.rank})</option>)}
      </select>
    </div>
  </div>
);

const JudgeSlider: React.FC<{ label: string; value: number; max: number; onChange: (v: number) => void }> = ({ label, value, max, onChange }) => (
  <div className="slider-group">
    <div className="slider-label">
      <span style={{ fontSize: '13px' }}>{label}</span>
      <span style={{ fontWeight: '800', color: '#2B7FFF' }}>{Math.round(value)} / {max}</span>
    </div>
    <input type="range" min="0" max={max} value={value} onChange={(e) => onChange(Number(e.target.value))} className="range-input" />
  </div>
);
