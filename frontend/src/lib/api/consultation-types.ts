export type ConsentRecord = {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  scopes: Record<string, boolean>;
  method: string;
  captured_at: string;
  status: string;
};

export type ConsultationSession = {
  id: string;
  encounter_id: string;
  patient_id: string;
  clinic_id: string;
  clinician_id: string;
  status: string;
  recovery_checkpoint: Record<string, unknown> | null;
  started_at: string;
  ended_at: string | null;
};

export type TranscriptSegment = {
  id: string;
  seq: number;
  speaker: string;
  language: string;
  text: string;
  corrected_text: string | null;
  confidence: number | null;
  start_ms: number;
  end_ms: number;
  is_corrected: boolean;
};

export type ClinicalNote = {
  id: string;
  session_id: string;
  encounter_id: string;
  patient_id: string;
  status: string;
  content: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
  content_hash: string | null;
  signed_at: string | null;
  addendum_of_id: string | null;
};

export type NoteContent = ClinicalNote["content"];
