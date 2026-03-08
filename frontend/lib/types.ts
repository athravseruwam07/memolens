export type ApiResponse<T> = {
  data: T;
  error?: string | null;
};

export type UserOut = {
  id: string;
  email: string;
  name: string;
  role: "caregiver" | "patient";
  created_at: string;
};

export type AuthData = {
  user: UserOut;
  token: string;
};

export type Patient = {
  id: string;
  name: string;
  age?: number | null;
  primary_caregiver?: string | null;
  emergency_contact?: Record<string, unknown> | null;
  tracked_items?: string[] | null;
  common_issues?: string | null;
  created_at?: string;
};

export type CaregiverLink = {
  caregiver_id: string;
  role: string;
  invited_at: string;
  caregiver_name?: string | null;
  caregiver_email?: string | null;
};

export type FamiliarPerson = {
  id: string;
  patient_id: string;
  name: string;
  relationship?: string | null;
  photos?: string[] | null;
  notes?: string | null;
  conversation_prompt?: string | null;
  importance_level?: number;
  created_at?: string;
};

export type Reminder = {
  id: string;
  patient_id: string;
  type?: string | null;
  trigger_meta?: Record<string, unknown> | null;
  message: string;
  active: boolean;
  created_at?: string;
};

export type DailyNote = {
  id: string;
  patient_id: string;
  note_date: string;
  content: string;
  created_at?: string;
};

export type ItemState = {
  id: string;
  patient_id: string;
  item_name: string;
  last_seen_room?: string | null;
  last_seen_at?: string | null;
  snapshot_url?: string | null;
  confidence?: number | null;
};

export type EventItem = {
  id: string;
  patient_id: string;
  type?: string | null;
  payload?: Record<string, unknown> | null;
  occurred_at: string;
};

export type QueryResult = {
  question: string;
  answer_type: string;
  results: unknown;
};

export type VoiceQueryResponse = {
  type: string;
  message: string;
  results?: unknown;
};

export type VoiceState = "idle" | "listening" | "processing" | "speaking" | "error";
