export type ProvenanceBlock = {
  model_id: string;
  provider: string;
  prompt_version: string;
  input_hash: string;
  generated_at: string;
  parameters: Record<string, unknown>;
  latency_ms: number | null;
};

export type ExtractedFact = {
  id: string;
  session_id: string;
  fact_type: string;
  value: string;
  source_segment_ref: string;
  confidence: { level: string; score: number };
  status: string;
  is_ai_generated: boolean;
  provenance: ProvenanceBlock;
};

export type AISuggestion = {
  id: string;
  session_id: string;
  suggestion_type: string;
  concept: { label: string; code_system?: string | null; code?: string | null };
  supporting_facts: Array<{ fact_id?: string | null; text: string; source_segment_ref: string }>;
  missing_information: string[];
  conflicting_information: string[];
  confidence: { level: string; score: number };
  red_flag_warnings: string[];
  source_references: Array<Record<string, unknown>>;
  uncertainty_notes: string | null;
  is_ai_generated: boolean;
  provenance: ProvenanceBlock;
  decision: {
    status: string;
    by: string | null;
    at: string | null;
    reason: string | null;
    edited_value: Record<string, unknown> | null;
  };
};

export type FactsListResponse = {
  run: { id: string; session_id: string; status: string; error_message: string | null; completed_at: string | null } | null;
  facts: ExtractedFact[];
};

export type SummaryResponse = {
  is_ai_generated: boolean;
  summary: string | null;
  run_status: string | null;
  provenance: ProvenanceBlock | null;
};

export type SuggestionsListResponse = {
  suggestions: AISuggestion[];
};
