"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type {
  AISuggestion,
  FactsListResponse,
  ProvenanceBlock,
  SuggestionsListResponse,
  SummaryResponse,
} from "@/lib/api/ai-types";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  sessionId: string;
  hasAiConsent: boolean;
};

export function AiAssistantPanel({ sessionId, hasAiConsent }: Props) {
  const t = useTranslations("consultation.ai");
  const { authorizedRequest } = useAuth();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editedLabel, setEditedLabel] = useState("");
  const [provenanceId, setProvenanceId] = useState<string | null>(null);

  const factsQuery = useQuery({
    queryKey: ["ai-facts", sessionId],
    queryFn: () => authorizedRequest<FactsListResponse>(`/sessions/${sessionId}/facts`),
    refetchInterval: (query) => {
      const status = query.state.data?.run?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });

  const runStatus = factsQuery.data?.run?.status;
  const isComplete = runStatus === "completed";

  const summaryQuery = useQuery({
    queryKey: ["ai-summary", sessionId],
    queryFn: () => authorizedRequest<SummaryResponse>(`/sessions/${sessionId}/summary`),
    enabled: isComplete,
  });

  const suggestionsQuery = useQuery({
    queryKey: ["ai-suggestions", sessionId],
    queryFn: () => authorizedRequest<SuggestionsListResponse>(`/sessions/${sessionId}/suggestions`),
    enabled: isComplete,
  });

  const extractMutation = useMutation({
    mutationFn: () =>
      authorizedRequest<FactsListResponse>(`/sessions/${sessionId}/extract`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-facts", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["ai-summary", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["ai-suggestions", sessionId] });
      void queryClient.invalidateQueries({ queryKey: ["note", sessionId] });
    },
  });

  const decideMutation = useMutation({
    mutationFn: ({
      suggestionId,
      decision,
      editedValue,
      reason,
    }: {
      suggestionId: string;
      decision: "approved" | "edited" | "rejected";
      editedValue?: Record<string, unknown>;
      reason?: string;
    }) =>
      authorizedRequest<AISuggestion>(`/suggestions/${suggestionId}/decision`, {
        method: "POST",
        body: { decision, edited_value: editedValue, reason },
      }),
    onSuccess: () => {
      setEditingId(null);
      setEditedLabel("");
      void queryClient.invalidateQueries({ queryKey: ["ai-suggestions", sessionId] });
    },
  });

  return (
    <section className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h3 className="text-lg font-semibold text-slate-900">{t("title")}</h3>
        <p className="mt-2 text-sm text-slate-600">{t("description")}</p>
        <p className="mt-3 rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-900">{t("aiLabel")}</p>
      </div>

      {!hasAiConsent ? (
        <p className="text-sm text-rose-700">{t("consentRequired")}</p>
      ) : (
        <button
          type="button"
          disabled={extractMutation.isPending || runStatus === "pending" || runStatus === "running"}
          onClick={() => extractMutation.mutate()}
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {extractMutation.isPending || runStatus === "pending" || runStatus === "running"
            ? t("running")
            : t("runExtraction")}
        </button>
      )}

      {runStatus ? (
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {t("runStatus")}: {runStatus}
        </p>
      ) : null}

      {factsQuery.data?.facts.length ? (
        <div>
          <h4 className="text-sm font-semibold text-slate-900">{t("factsTitle")}</h4>
          <ul className="mt-3 space-y-2">
            {factsQuery.data.facts.map((fact) => (
              <li key={fact.id} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm">
                <span className="font-medium text-teal-700">{fact.fact_type}</span>
                <p className="mt-1 text-slate-900">{fact.value}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {t("confidence")}: {fact.confidence.level} ({Math.round(fact.confidence.score * 100)}%)
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {summaryQuery.data?.summary ? (
        <div>
          <h4 className="text-sm font-semibold text-slate-900">{t("summaryTitle")}</h4>
          <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50/50 p-4 text-sm text-slate-900">
            {summaryQuery.data.summary}
          </p>
          {summaryQuery.data.provenance ? (
            <ProvenanceDetails provenance={summaryQuery.data.provenance} t={t} />
          ) : null}
        </div>
      ) : null}

      {suggestionsQuery.data?.suggestions.length ? (
        <div>
          <h4 className="text-sm font-semibold text-slate-900">{t("suggestionsTitle")}</h4>
          <ul className="mt-3 space-y-3">
            {suggestionsQuery.data.suggestions.map((item) => (
              <li key={item.id} className="rounded-lg border border-slate-200 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-slate-900">{item.concept.label}</span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs uppercase text-slate-600">
                    {item.suggestion_type.replaceAll("_", " ")}
                  </span>
                </div>
                {item.red_flag_warnings.length ? (
                  <ul className="mt-2 list-disc space-y-1 ps-5 text-rose-800">
                    {item.red_flag_warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                ) : null}
                {item.uncertainty_notes ? (
                  <p className="mt-2 text-xs text-slate-500">{item.uncertainty_notes}</p>
                ) : null}
                <button
                  type="button"
                  onClick={() => setProvenanceId(provenanceId === item.id ? null : item.id)}
                  className="mt-2 text-xs font-medium text-teal-700 hover:text-teal-900"
                >
                  {provenanceId === item.id ? t("hideProvenance") : t("showProvenance")}
                </button>
                {provenanceId === item.id ? (
                  <ProvenanceDetails provenance={item.provenance} t={t} />
                ) : null}
                {item.decision.status === "pending" ? (
                  <div className="mt-3 space-y-2">
                    {editingId === item.id ? (
                      <div className="space-y-2">
                        <label className="flex flex-col gap-1 text-xs">
                          <span className="font-medium text-slate-700">{t("editLabel")}</span>
                          <input
                            value={editedLabel}
                            onChange={(event) => setEditedLabel(event.target.value)}
                            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
                          />
                        </label>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              decideMutation.mutate({
                                suggestionId: item.id,
                                decision: "edited",
                                editedValue: { label: editedLabel },
                                reason: t("editReason"),
                              })
                            }
                            className="rounded-md bg-teal-700 px-3 py-1.5 text-xs font-medium text-white"
                          >
                            {t("saveEdit")}
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs"
                          >
                            {t("cancelEdit")}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => decideMutation.mutate({ suggestionId: item.id, decision: "approved" })}
                          className="rounded-md bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800"
                        >
                          {t("approve")}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingId(item.id);
                            setEditedLabel(item.concept.label);
                          }}
                          className="rounded-md border border-teal-300 px-3 py-1.5 text-xs font-medium text-teal-800 hover:bg-teal-50"
                        >
                          {t("edit")}
                        </button>
                        <button
                          type="button"
                          onClick={() => decideMutation.mutate({ suggestionId: item.id, decision: "rejected" })}
                          className="rounded-md border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-800 hover:bg-rose-50"
                        >
                          {t("reject")}
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="mt-2 text-xs font-medium text-slate-600">
                    {t("decision")}: {item.decision.status}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function ProvenanceDetails({
  provenance,
  t,
}: {
  provenance: ProvenanceBlock;
  t: ReturnType<typeof useTranslations<"consultation.ai">>;
}) {
  return (
    <dl className="mt-2 grid gap-1 rounded-md bg-slate-50 p-3 text-xs text-slate-600">
      <div>
        <dt className="font-medium text-slate-700">{t("provenanceModel")}</dt>
        <dd>{provenance.model_id}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-700">{t("provenanceProvider")}</dt>
        <dd>{provenance.provider}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-700">{t("provenancePrompt")}</dt>
        <dd>{provenance.prompt_version}</dd>
      </div>
      <div>
        <dt className="font-medium text-slate-700">{t("provenanceHash")}</dt>
        <dd className="break-all font-mono">{provenance.input_hash.slice(0, 16)}…</dd>
      </div>
    </dl>
  );
}
