"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { AiAssistantPanel } from "@/components/consultation/ai-assistant-panel";
import { AudioRecorder } from "@/components/consultation/audio-recorder";
import { Link } from "@/i18n/navigation";
import type {
  ClinicalNote,
  ConsentRecord,
  ConsultationSession,
  NoteContent,
  TranscriptSegment,
} from "@/lib/api/consultation-types";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  patientId: string;
  sessionId: string;
};

type Step = "consent" | "recording" | "transcript" | "ai" | "note";

const emptyNote: NoteContent = {
  subjective: "",
  objective: "",
  assessment: "",
  plan: "",
};

export function ConsultationWorkspace({ patientId, sessionId }: Props) {
  const t = useTranslations("consultation");
  const locale = useLocale();
  const { authorizedRequest } = useAuth();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("consent");
  const [noteDraft, setNoteDraft] = useState<NoteContent>(emptyNote);

  const sessionQuery = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => authorizedRequest<ConsultationSession>(`/sessions/${sessionId}`),
  });

  const consentsQuery = useQuery({
    queryKey: ["consents", patientId],
    queryFn: () => authorizedRequest<ConsentRecord[]>(`/patients/${patientId}/consents`),
  });

  const transcriptQuery = useQuery({
    queryKey: ["transcript", sessionId],
    queryFn: () => authorizedRequest<TranscriptSegment[]>(`/sessions/${sessionId}/transcript`),
    enabled: step === "transcript" || step === "note",
  });

  const noteQuery = useQuery({
    queryKey: ["note", sessionId],
    queryFn: () => authorizedRequest<ClinicalNote>(`/sessions/${sessionId}/note`),
    enabled: step === "note",
  });

  const hasAiConsent = useMemo(
    () =>
      (consentsQuery.data ?? []).some(
        (record) => record.status === "active" && record.scopes.ai_processing === true,
      ),
    [consentsQuery.data],
  );

  const hasRecordingConsent = useMemo(
    () =>
      (consentsQuery.data ?? []).some(
        (record) => record.status === "active" && record.scopes.recording === true,
      ),
    [consentsQuery.data],
  );

  const captureConsentMutation = useMutation({
    mutationFn: () =>
      authorizedRequest<ConsentRecord>(`/patients/${patientId}/consents`, {
        method: "POST",
        body: {
          scopes: { recording: true, ai_processing: true },
          method: "verbal_confirmed",
          encounter_id: sessionQuery.data?.encounter_id,
        },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["consents", patientId] });
    },
  });

  const finalizeAudioMutation = useMutation({
    mutationFn: async () => {
      await authorizedRequest(`/sessions/${sessionId}/audio:create-upload`, {
        method: "POST",
        body: { filename: "consultation.webm", mime_type: "audio/webm" },
      });
      return authorizedRequest(`/sessions/${sessionId}/audio:finalize`, {
        method: "POST",
        body: { size_bytes: 2048, duration_ms: 11000 },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["transcript", sessionId] });
      setStep("transcript");
    },
  });

  const updateSegmentMutation = useMutation({
    mutationFn: ({ segmentId, correctedText }: { segmentId: string; correctedText: string }) =>
      authorizedRequest<TranscriptSegment>(`/sessions/${sessionId}/transcript/${segmentId}`, {
        method: "PATCH",
        body: { corrected_text: correctedText },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["transcript", sessionId] }),
  });

  const saveNoteMutation = useMutation({
    mutationFn: (content: NoteContent) =>
      authorizedRequest<ClinicalNote>(`/sessions/${sessionId}/note`, {
        method: "PATCH",
        body: { content },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["note", sessionId] }),
  });

  const signNoteMutation = useMutation({
    mutationFn: () =>
      authorizedRequest<ClinicalNote>(`/sessions/${sessionId}/note:sign`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["note", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    },
  });

  const addendumMutation = useMutation({
    mutationFn: (content: NoteContent) =>
      authorizedRequest<ClinicalNote>(`/sessions/${sessionId}/note:addendum`, {
        method: "POST",
        body: { content },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["note", sessionId] }),
  });

  const sessionStatus = sessionQuery.data?.status ?? "draft";

  useEffect(() => {
    if (noteQuery.data && step === "note") {
      setNoteDraft(noteQuery.data.content);
    }
  }, [noteQuery.data?.id, step, noteQuery.data]);

  const steps: { key: Step; label: string }[] = [
    { key: "consent", label: t("stepConsent") },
    { key: "recording", label: t("stepRecording") },
    { key: "transcript", label: t("stepTranscript") },
    { key: "ai", label: t("stepAi") },
    { key: "note", label: t("stepNote") },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link href={`/patients/${patientId}`} className="text-sm font-medium text-teal-700 hover:text-teal-900">
          ← {t("backToPatient")}
        </Link>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-2xl font-semibold text-slate-900">{t("title")}</h2>
          <p className="mt-1 text-sm text-slate-600">{t("subtitle")}</p>
          <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-teal-700">
            {t("sessionStatus")}: {sessionStatus}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {steps.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setStep(item.key)}
            className={`rounded-full px-4 py-2 text-sm ${
              step === item.key
                ? "bg-teal-700 text-white"
                : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {step === "consent" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">{t("consentTitle")}</h3>
          <p className="mt-2 text-sm text-slate-600">{t("consentDescription")}</p>
          {hasRecordingConsent ? (
            <p className="mt-4 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{t("consentActive")}</p>
          ) : (
            <button
              type="button"
              disabled={captureConsentMutation.isPending}
              onClick={() => captureConsentMutation.mutate()}
              className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {captureConsentMutation.isPending ? t("saving") : t("captureConsent")}
            </button>
          )}
        </section>
      ) : null}

      {step === "recording" ? (
        <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">{t("recordingTitle")}</h3>
          <p className="text-sm text-slate-600">{t("recordingDescription")}</p>
          {!hasRecordingConsent ? (
            <p className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900">{t("consentRequired")}</p>
          ) : (
            <div className="space-y-4">
              <AudioRecorder
                sessionId={sessionId}
                disabled={finalizeAudioMutation.isPending}
                onRecordingStarted={() => {
                  void queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
                }}
                onTranscriptReady={() => {
                  void queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
                  void queryClient.invalidateQueries({ queryKey: ["transcript", sessionId] });
                  setStep("transcript");
                }}
              />
              <div className="border-t border-slate-100 pt-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t("demoFallback")}
                </p>
                <button
                  type="button"
                  disabled={finalizeAudioMutation.isPending}
                  onClick={() => finalizeAudioMutation.mutate()}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-60"
                >
                  {finalizeAudioMutation.isPending ? t("processing") : t("simulateUploadTranscribe")}
                </button>
              </div>
            </div>
          )}
        </section>
      ) : null}

      {step === "transcript" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">{t("transcriptTitle")}</h3>
          {(transcriptQuery.data ?? []).length === 0 ? (
            <p className="mt-4 text-sm text-slate-600">{t("noTranscript")}</p>
          ) : (
            <ul className="mt-4 space-y-4">
              {(transcriptQuery.data ?? []).map((segment) => (
                <TranscriptEditor
                  key={segment.id}
                  segment={segment}
                  locale={locale}
                  onSave={(text) =>
                    updateSegmentMutation.mutate({ segmentId: segment.id, correctedText: text })
                  }
                  t={t}
                />
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {step === "ai" ? <AiAssistantPanel sessionId={sessionId} hasAiConsent={hasAiConsent} /> : null}

      {step === "note" ? (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">{t("noteTitle")}</h3>
          {noteQuery.data?.status === "signed" ? (
            <div className="mt-4 space-y-4">
              <p className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{t("noteSigned")}</p>
              <NotePreview content={noteQuery.data.content} t={t} />
              <form
                className="space-y-3 border-t border-slate-100 pt-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  addendumMutation.mutate(noteDraft);
                }}
              >
                <h4 className="text-sm font-semibold text-slate-900">{t("addendumTitle")}</h4>
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-700">{t("note.assessment")}</span>
                  <textarea
                    rows={3}
                    value={noteDraft.assessment}
                    onChange={(event) =>
                      setNoteDraft((current) => ({ ...current, assessment: event.target.value }))
                    }
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
                <button
                  type="submit"
                  disabled={addendumMutation.isPending}
                  className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {addendumMutation.isPending ? t("saving") : t("createAddendum")}
                </button>
              </form>
            </div>
          ) : (
            <form
              className="mt-4 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                saveNoteMutation.mutate(noteDraft);
              }}
            >
              {(["subjective", "objective", "assessment", "plan"] as const).map((field) => (
                <label key={field} className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-700">{t(`note.${field}`)}</span>
                  <textarea
                    rows={3}
                    value={noteDraft[field]}
                    onChange={(event) => setNoteDraft((current) => ({ ...current, [field]: event.target.value }))}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
              ))}
              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={saveNoteMutation.isPending}
                  className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
                >
                  {saveNoteMutation.isPending ? t("saving") : t("saveNote")}
                </button>
                <button
                  type="button"
                  disabled={signNoteMutation.isPending}
                  onClick={() => {
                    saveNoteMutation.mutate(noteDraft, {
                      onSuccess: () => signNoteMutation.mutate(),
                    });
                  }}
                  className="rounded-lg border border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50 disabled:opacity-60"
                >
                  {signNoteMutation.isPending ? t("signing") : t("signNote")}
                </button>
              </div>
            </form>
          )}
        </section>
      ) : null}
    </div>
  );
}

function TranscriptEditor({
  segment,
  locale,
  onSave,
  t,
}: {
  segment: TranscriptSegment;
  locale: string;
  onSave: (text: string) => void;
  t: ReturnType<typeof useTranslations<"consultation">>;
}) {
  const [value, setValue] = useState(segment.corrected_text ?? segment.text);

  return (
    <li className="rounded-lg border border-slate-100 bg-slate-50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
        {speakerLabel(t, segment.speaker)} · {segment.start_ms}ms
      </p>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={2}
        className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        dir={locale === "ar" ? "rtl" : "ltr"}
      />
      <button
        type="button"
        onClick={() => onSave(value)}
        className="mt-2 text-sm font-medium text-teal-700 hover:text-teal-900"
      >
        {t("saveCorrection")}
      </button>
    </li>
  );
}

function NotePreview({
  content,
  t,
}: {
  content: NoteContent;
  t: ReturnType<typeof useTranslations<"consultation">>;
}) {
  return (
    <dl className="grid gap-3 text-sm">
      {(["subjective", "objective", "assessment", "plan"] as const).map((field) => (
        <div key={field}>
          <dt className="font-medium text-slate-700">{t(`note.${field}`)}</dt>
          <dd className="mt-1 whitespace-pre-wrap text-slate-900">{content[field] || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

function speakerLabel(
  t: ReturnType<typeof useTranslations<"consultation">>,
  speaker: string,
): string {
  switch (speaker) {
    case "doctor":
      return t("speaker.doctor");
    case "patient":
      return t("speaker.patient");
    default:
      return speaker;
  }
}
