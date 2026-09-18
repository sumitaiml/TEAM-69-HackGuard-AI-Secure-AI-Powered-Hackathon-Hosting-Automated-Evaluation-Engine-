import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ParticipantDashboard } from './components/ParticipantDashboard';
import { OrganizerDashboard } from './components/OrganizerDashboard';
import { JudgeDashboard } from './components/JudgeDashboard';
import { LoginPage } from './components/LoginPage';

export interface HackathonItem {
  id: string;
  title: string;
  description: string;
  startDate: string;
  endDate: string;
  status: string;
  teamsCount: number;
}

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentRole, setCurrentRole] = useState<'participant' | 'organizer' | 'judge'>('participant');
  const [activeTab, setActiveTab] = useState('overview');

  // Shared Global Hackathons State
  const [hackathons, setHackathons] = useState<HackathonItem[]>([
    {
      id: 'h1',
      title: 'TechNova 2026 AI Hackathon',
      description: 'Global AI & DevOps Challenge',
      startDate: '2026-09-18',
      endDate: '2026-09-20',
      status: 'Active',
      teamsCount: 142
    }
  ]);
  const [selectedHackathonId, setSelectedHackathonId] = useState('h1');

  // Fetch from FastAPI backend on load
  useEffect(() => {
    fetch('http://localhost:8000/api/hackathons')
      .then(res => res.ok ? res.json() : [])
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          const mapped = data.map((h: any) => ({
            id: h.id,
            title: h.title,
            description: h.description || 'AI Hackathon Challenge',
            startDate: h.created_at ? h.created_at.split('T')[0] : '2026-09-18',
            endDate: '2026-09-25',
            status: h.is_active ? 'Active' : 'Ended',
            teamsCount: 142
          }));
          setHackathons(mapped);
          setSelectedHackathonId(mapped[0].id);
        }
      })
      .catch(() => {
        // Fallback to initial state if backend unavailable
      });
  }, []);

  const handleCreateHackathon = (title: string, description: string, startDate: string, endDate: string) => {
    const newHack: HackathonItem = {
      id: `h_${Date.now()}`,
      title,
      description: description || 'Custom Hackathon Event',
      startDate,
      endDate,
      status: 'Active',
      teamsCount: 0
    };

    setHackathons(prev => [newHack, ...prev]);
    setSelectedHackathonId(newHack.id);

    // Sync with FastAPI backend if token exists
    fetch('http://localhost:8000/api/hackathons/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description })
    }).catch(() => {});
  };

  const handleLoginSuccess = (role: 'participant' | 'organizer' | 'judge', _userEmail: string) => {
    setCurrentRole(role);
    setActiveTab('overview');
    setIsAuthenticated(true);
  };

  const getHeaderTitle = () => {
    if (currentRole === 'participant') {
      if (activeTab === 'team') return 'Team Management';
      if (activeTab === 'submit') return 'Project Submission Hub';
      if (activeTab === 'report') return 'AI Evaluation Report';
      if (activeTab === 'leaderboard') return 'Live Leaderboard';
      return 'Participant Overview';
    }
    if (currentRole === 'organizer') {
      if (activeTab === 'rubric') return 'Evaluation Rubric Configurator';
      if (activeTab === 'fraud') return 'Plagiarism & Fraud Monitor';
      if (activeTab === 'leaderboard') return 'Results & Winner Publisher';
      return 'Organizer Command Center';
    }
    if (activeTab === 'report') return 'Multimodal AI Report Audit';
    if (activeTab === 'override') return 'Score Override Console';
    return 'Judge Audit & Review Portal';
  };

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-shell">
      <Sidebar
        currentRole={currentRole}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="main-content">
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
          <button
            onClick={() => setIsAuthenticated(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#6B7280',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            ← Sign Out / Lock Screen
          </button>
        </div>

        <Header
          currentRole={currentRole}
          setCurrentRole={(role) => {
            setCurrentRole(role);
            setActiveTab('overview');
          }}
          title={getHeaderTitle()}
        />

        <div className="animate-fade-in" key={`${currentRole}-${activeTab}`}>
          {currentRole === 'participant' && (
            <ParticipantDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
            />
          )}
          {currentRole === 'organizer' && (
            <OrganizerDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
              setSelectedHackathonId={setSelectedHackathonId}
              onCreateHackathon={handleCreateHackathon}
            />
          )}
          {currentRole === 'judge' && (
            <JudgeDashboard
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              hackathons={hackathons}
              selectedHackathonId={selectedHackathonId}
            />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
