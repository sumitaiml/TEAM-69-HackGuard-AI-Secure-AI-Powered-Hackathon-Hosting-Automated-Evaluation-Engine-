export type Role = 'participant' | 'organizer' | 'judge';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
}

export interface RubricWeights {
  technical_complexity: number;
  innovation: number;
  ui_ux: number;
  business_impact: number;
  documentation: number;
  presentation: number;
}

export interface HackathonItem {
  id: string;
  title: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  rubric_weights_json: RubricWeights | null;
  is_active: boolean;
  created_at: string;
}

export interface TeamMember {
  id: string;
  user: AuthUser;
  joined_at: string;
}

export interface Team {
  id: string;
  name: string;
  invite_code: string;
  leader_id: string;
  created_at: string;
  members: TeamMember[];
}

export interface UploadMetadataEntry {
  original_filename: string;
  size_bytes: number;
  duration_seconds?: number;
}

export interface Submission {
  id: string;
  team_id: string;
  hackathon_id: string;
  github_url: string | null;
  zip_path: string | null;
  ppt_path: string | null;
  video_path: string | null;
  readme_text: string | null;
  tech_stack: string | null;
  live_url: string | null;
  status: string;
  upload_metadata_json: Record<string, UploadMetadataEntry> | null;
  timeline_risk_json: { status: string; risk_level: string; reasoning: string; suspicious_commits: string[] } | null;
  submitted_at: string;
}

export interface AiScores {
  overall_score: number;
  parameter_scores: Record<string, number>;
  ai_feedback: string[];
  improvement_suggestions: string[];
  ai_evaluation_degraded: boolean;
  degraded_reason?: string;
  whisper_transcript?: {
    status: string;
    transcript?: string;
    reason?: string;
  };
  ppt_analysis?: {
    status: string;
    slide_count?: number;
    slides?: { slide_number: number; text: string; has_image: boolean }[];
    reason?: string;
  };
  pitch_deck_analysis?: {
    status: string;
    slides: { slide_number: number; narrative_role: string; clarity_score: number; notes: string }[];
    missing_narrative_elements: string[];
    overall_narrative_score: number;
    slides_inspected_visually?: number[];
  };
}

export interface EvaluationReport {
  id: string;
  submission_id: string;
  static_analysis_json: Record<string, any> | null;
  plagiarism_json: Record<string, any> | null;
  ai_scores_json: AiScores | null;
  repo_verification_json: {
    status: string;
    claims_checked: { claim: string; verdict: string; evidence: string }[];
    architecture_summary: string;
    red_flags: string[];
    confidence: number;
  } | null;
  final_score: number;
  judge_override_json: {
    overridden_by: string;
    overridden_by_id: string;
    parameter_scores: Record<string, number>;
    justification: string;
  } | null;
  judge_comments: string | null;
  created_at: string;
}

export interface LeaderboardEntry {
  submission_id: string;
  team_id: string;
  team_name: string;
  tech_stack: string;
  github_url: string | null;
  live_url: string | null;
  score: number;
  parameter_scores: Record<string, number> | null;
  plagiarism_risk: string;
  plagiarism_percentage: number;
  plagiarism_explanation: { verdict: string; explanation: string; cited_file_pairs: string[] } | null;
  ai_code_risk: string;
  ai_code_usage_percentage: number | null;
  timeline_risk_level: string;
  timeline_reasoning: string;
  repo_red_flags_count: number;
  repo_claims_checked_count: number;
  status: string;
  submitted_at: string;
  rank: number;
}

export interface TaskStatus<T = any> {
  task_id: string;
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE';
  result?: T;
  error?: string;
}

export interface JudgeInviteOut {
  id: string;
  hackathon_id: string;
  email: string;
  status: string;
  expires_at: string;
  created_at: string;
  dev_invite_link?: string;
}

export interface InviteDetails {
  email: string;
  hackathon_id: string;
  hackathon_title: string;
  status: string;
  expires_at: string;
}
