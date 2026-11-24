export async function api<T = any>(
  path: string,
  student: string,
  method = 'GET',
  body?: unknown,
  extraHeaders: Record<string, string> = {}
): Promise<T> {
  const response = await fetch('/api' + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(student ? { 'X-Demo-Student-ID': student } : {}),
      ...extraHeaders
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  }
  return data;
}

export const time = (value: string | number) => {
  if (!value) return '—';
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
  return date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    dateStyle: 'medium',
    timeStyle: 'short'
  });
};

export const formatClock = (secondsRemaining: number): string => {
  const m = Math.floor(Math.max(0, secondsRemaining) / 60);
  const s = Math.floor(Math.max(0, secondsRemaining) % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

export function fromIST(value: string) {
  return value ? new Date(value + ':00+05:30').toISOString() : null;
}

export interface Skill {
  domain: string;
  tag: string;
  level: number;
}

export interface AvailabilityWindow {
  id: string;
  student_id?: string;
  start: string;
  end: string;
}

export interface Student {
  id: string;
  name: string;
  mentoring: boolean;
  points_balance: number;
  skills: Skill[];
  availability: AvailabilityWindow[];
  history?: {
    completed: number;
    resolved: number;
    reliability: number;
  };
}

export interface PointTransaction {
  id: string;
  student_id: string;
  amount: number;
  transaction_type: 'INITIAL_GRANT' | 'BOUNTY_RESERVED' | 'BOUNTY_AWARDED' | 'BOUNTY_REFUNDED' | 'BOUNTY_ADJUSTED';
  doubt_id?: string | null;
  session_id?: string | null;
  reference_id: string;
  balance_after: number;
  created_at: string;
  notes?: string | null;
}

export interface Doubt {
  id: string;
  requester_id: string;
  title: string;
  description: string;
  domain: string;
  skills: string[];
  urgency: 'Urgent' | 'Normal' | 'Flexible';
  bounty: number;
  status: 'OPEN' | 'MATCHED' | 'IN_SESSION' | 'AWAITING_CONFIRMATION' | 'RESOLVED' | 'UNMATCHED' | 'CANCELLED';
  assigned_session_id?: string | null;
  created_at: string;
  preferred_start?: string | null;
  deadline?: string | null;
}

export interface SessionMessage {
  id: string;
  session_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export interface SessionExplanation {
  suitability?: number;
  utility?: number;
  reason?: string;
  evidence_label?: string;
  skill_relevance?: number;
  assessment_evidence?: number;
  reliability?: number;
  availability?: number;
  waiting_bonus?: number;
  bounty_bonus?: number;
  [key: string]: any;
}

export interface Session {
  id: string;
  doubt_id: string;
  mentor_id: string;
  requester_id: string;
  mentor_name?: string;
  requester_name?: string;
  doubt_title?: string;
  doubt_description?: string;
  doubt_domain?: string;
  doubt_skills?: string[];
  doubt_urgency?: string;
  bounty?: number;
  start: string;
  end: string;
  state: 'OFFERED' | 'ACCEPTED' | 'ACTIVE' | 'AWAITING_CONFIRMATION' | 'RESOLVED' | 'DECLINED' | 'EXPIRED' | 'CANCELLED';
  offer_expires_at: string;
  accepted_at?: string | null;
  actual_started_at?: string | null;
  mentor_completed_at?: string | null;
  outcome_deadline?: string | null;
  completed_at?: string | null;
  is_demo_accelerated: boolean;
  mentor_completed: boolean;
  resolved?: boolean | null;
  notes?: string | null;
  explanation: SessionExplanation;
  feedback?: {
    id: string;
    rating: number;
    notes: string;
  } | null;
  active_seconds_remaining?: number;
  server_time?: number;
}

export interface MentorProfile {
  id: string;
  name: string;
  mentoring: boolean;
  points_balance: number;
  skills: Skill[];
  availability: AvailabilityWindow[];
  assessments: {
    id: string;
    domain: string;
    score: number;
    question_count: number;
    correct_count: number;
    version: number;
    created_at: string;
  }[];
  completed_sessions: number;
  resolved_sessions: number;
  resolution_rate: number | null;
  resolution_history_label: string;
  feedback_count: number;
  average_rating: number | null;
  bounties_earned: number;
  smoothed_reliability_heuristic: number;
}

export type Domains = Record<string, string[]>;

// ==========================================
// MENTORING WORKSPACE TYPES (P0 & P1)
// ==========================================

export interface SessionMeeting {
  session_id: string;
  meeting_url: string;
  attached_by_id: string;
  attached_at: string;
  updated_at: string;
}

export interface SessionCodeSnippet {
  id: string;
  session_id: string;
  author_id: string;
  author_name?: string;
  title: string;
  filename?: string | null;
  language: string;
  content: string;
  snippet_type: 'ORIGINAL' | 'PROPOSED_FIX' | 'EXAMPLE' | 'ERROR_LOG' | 'OTHER';
  parent_snippet_id?: string | null;
  created_at: string;
}

export interface DiffLine {
  type: 'added' | 'removed' | 'unchanged';
  text: string;
}

export interface SnippetDiff {
  lines: DiffLine[];
  added_count: number;
  removed_count: number;
  unchanged_count: number;
  original: {
    id: string;
    title: string;
    language: string;
    author_id: string;
  };
  proposed: {
    id: string;
    title: string;
    language: string;
    author_id: string;
  };
}

export interface SessionResolution {
  id: string;
  session_id: string;
  doubt_id: string;
  mentor_id: string;
  requester_id: string;
  root_cause: string;
  solution_explanation: string;
  follow_up_steps?: string | null;
  original_snippet_id?: string | null;
  corrected_snippet_id?: string | null;
  original_snippet?: SessionCodeSnippet | null;
  corrected_snippet?: SessionCodeSnippet | null;
  reference_urls?: string[];
  created_at: string;
  updated_at: string;
  submitted_at?: string | null;
  confirmed_at?: string | null;
  requester_status: 'PENDING' | 'CONFIRMED_RESOLVED' | 'CONFIRMED_UNRESOLVED';
}

export interface SolutionHistoryItem {
  session_id: string;
  doubt_id: string;
  doubt_title: string;
  doubt_description: string;
  domain: string;
  skills: string[];
  bounty: number;
  role: 'mentor' | 'requester';
  other_student_id: string;
  other_student_name: string;
  session_state: string;
  resolved?: boolean | null;
  date: string;
  rating?: number | null;
  feedback_notes?: string | null;
  resolution?: SessionResolution | null;
  snippet_count: number;
  snippets: SessionCodeSnippet[];
}

