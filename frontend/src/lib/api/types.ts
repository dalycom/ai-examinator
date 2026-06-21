export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string | null;
  mfa_required?: boolean;
  mfa_token?: string | null;
};

export type UserProfile = {
  id: string;
  email: string;
  full_name: string;
  preferred_locale: string;
  organization_id: string;
  permissions: string[];
};

export type Patient = {
  id: string;
  mrn: string;
  given_name: string;
  family_name: string;
  date_of_birth: string | null;
  sex: string | null;
  contact: Record<string, unknown> | null;
  preferred_locale: string;
  status: string;
  clinic_id: string | null;
};

export type Allergy = {
  id: string;
  substance_code: string | null;
  substance_name: string;
  reaction: string | null;
  severity: string | null;
  status: string;
};

export type Medication = {
  id: string;
  drug_code: string | null;
  drug_name: string;
  dose: string | null;
  status: string;
};

export type HistoryEntry = {
  id: string;
  category: "medical" | "surgical" | "family" | "social";
  description: string;
  onset_date: string | null;
};

export type TimelineEvent = {
  occurred_at: string;
  event_type: string;
  title: string;
  metadata: Record<string, unknown>;
};

export type ApiErrorBody = {
  code?: string;
  message?: string;
  message_key?: string;
};
