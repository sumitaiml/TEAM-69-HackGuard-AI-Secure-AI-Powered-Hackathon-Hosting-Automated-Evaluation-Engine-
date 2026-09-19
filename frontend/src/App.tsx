import { useState, useEffect, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ParticipantDashboard } from './components/ParticipantDashboard';
import { OrganizerDashboard } from './components/OrganizerDashboard';
import { JudgeDashboard } from './components/JudgeDashboard';
import { LoginPage } from './components/LoginPage';
import { AcceptInvitePage } from './components/AcceptInvitePage';
import { useAuth } from './context/AuthContext';
import { api } from './lib/apiClient';
import type { HackathonItem } from './lib/types';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function DashboardShell() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [hackathons, setHackathons] = useState<HackathonItem[]>([]);
  const [selectedHackathonId, setSelectedHackathonId] = useState('');
  const [loadError, setLoadError] = useState<string | null>(null);

  const refetchHackathons = useCallback(() => {
    api
      .get<HackathonItem[]>('/api/hackathons')
      .then((data) => {
        setHackathons(data);
        setLoadError(null);
        setSelectedHackathonId((prev) => (prev && data.some((h) => h.id === prev) ? prev : data[0]?.id || ''));
      })
      .catch(() => setLoadError('Could not reach the backend to load hackathons.'));
  }, []);

  useEffect(() => {
    refetchHackathons();
  }, [refetchHackathons]);

  const handleCreateHackathon = async (title: string, description: string, startDate: string, endDate: string) => {
    const created = await api.post<HackathonItem>('/api/hackathons/create', {
      title,
      description,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });
    setHackathons((prev) => [created, ...prev]);
    setSelectedHackathonId(created.id);
  };

  if (!user) return null;

  const getHeaderTitle = () => {
    if (user.role === 'participant') {
      if (activeTab === 'team') return 'Team Management';
      if (activeTab === 'submit') return 'Project Submission Hub';
      if (activeTab === 'report') return 'AI Evaluation Report';
      if (activeTab === 'leaderboard') return 'Live Leaderboard';
      return 'Participant Overview';
    }
    if (user.role === 'organizer') {
      if (activeTab === 'rubric') return 'Evaluation Rubric Configurator';
      if (activeTab === 'fraud') return 'Plagiarism & Fraud Monitor';
      if (activeTab === 'leaderboard') return 'Results & Winner Publisher';
      return 'Organizer Command Center';
    }
    if (activeTab === 'report') return 'Multimodal AI Report Audit';
    if (activeTab === 'override') return 'Score Override Console';
    return 'Judge Audit & Review Portal';
  };

  return (
    <div className="app-shell">
      <Sidebar currentRole={user.role} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
          <button
            onClick={logout}
            style={{ background: 'transparent', border: 'none', color: '#6B7280', fontSize: '12px', fontWeight: '600', cursor: 'pointer', textDecoration: 'underline' }}
          >
            ← Sign Out
          </button>
        </div>

        <Header title={getHeaderTitle()} />

        {/* Keyed on role only (not activeTab) - remounting on every tab switch used to
            wipe in-flight evaluation-polling state (evalTaskId) inside the dashboards. */}
        <div className="animate-fade-in" key={user.role}>
          {loadError && (
            <div style={{ background: '#FEE2E2', color: '#991B1B', padding: '12px 16px', borderRadius: '12px', fontSize: '13px', fontWeight: 600, marginBottom: '16px' }}>
              {loadError}
            </div>
          )}

          {user.role === 'participant' && (
            <ParticipantDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
              setSelectedHackathonId={setSelectedHackathonId}
            />
          )}
          {user.role === 'organizer' && (
            <OrganizerDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
              setSelectedHackathonId={setSelectedHackathonId}
              onCreateHackathon={handleCreateHackathon}
            />
          )}
          {user.role === 'judge' && (
            <JudgeDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
              setSelectedHackathonId={setSelectedHackathonId}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/accept-invite" element={<AcceptInvitePage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <DashboardShell />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
