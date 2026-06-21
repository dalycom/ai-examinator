"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";

import { Link } from "@/i18n/navigation";
import { StartConsultationButton } from "@/components/consultation/start-consultation-button";
import { ApiError } from "@/lib/api/client";
import type { Allergy, HistoryEntry, Medication, Patient, TimelineEvent } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/auth-context";
import { formatDate, formatDateTime, patientDisplayName } from "@/lib/format";

type TabKey = "overview" | "allergies" | "medications" | "history" | "timeline";

type Props = {
  patientId: string;
};

export function PatientProfileView({ patientId }: Props) {
  const t = useTranslations("patients");
  const locale = useLocale();
  const { authorizedRequest } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  const patientQuery = useQuery({
    queryKey: ["patient", patientId],
    queryFn: () => authorizedRequest<Patient>(`/patients/${patientId}`),
  });

  const allergiesQuery = useQuery({
    queryKey: ["patient", patientId, "allergies"],
    queryFn: () => authorizedRequest<Allergy[]>(`/patients/${patientId}/allergies`),
    enabled: activeTab === "allergies" || activeTab === "overview",
  });

  const medicationsQuery = useQuery({
    queryKey: ["patient", patientId, "medications"],
    queryFn: () => authorizedRequest<Medication[]>(`/patients/${patientId}/medications`),
    enabled: activeTab === "medications" || activeTab === "overview",
  });

  const historyQuery = useQuery({
    queryKey: ["patient", patientId, "history"],
    queryFn: () => authorizedRequest<HistoryEntry[]>(`/patients/${patientId}/history`),
    enabled: activeTab === "history" || activeTab === "overview",
  });

  const timelineQuery = useQuery({
    queryKey: ["patient", patientId, "timeline"],
    queryFn: () => authorizedRequest<TimelineEvent[]>(`/patients/${patientId}/timeline`),
    enabled: activeTab === "timeline",
  });

  const invalidatePatientData = () => {
    void queryClient.invalidateQueries({ queryKey: ["patient", patientId] });
    void queryClient.invalidateQueries({ queryKey: ["patient", patientId, "allergies"] });
    void queryClient.invalidateQueries({ queryKey: ["patient", patientId, "medications"] });
    void queryClient.invalidateQueries({ queryKey: ["patient", patientId, "history"] });
    void queryClient.invalidateQueries({ queryKey: ["patient", patientId, "timeline"] });
  };

  const addAllergyMutation = useMutation({
    mutationFn: (payload: { substance_name: string; reaction?: string; severity?: string }) =>
      authorizedRequest(`/patients/${patientId}/allergies`, { method: "POST", body: payload }),
    onSuccess: invalidatePatientData,
  });

  const addMedicationMutation = useMutation({
    mutationFn: (payload: { drug_name: string; dose?: string }) =>
      authorizedRequest(`/patients/${patientId}/medications`, { method: "POST", body: payload }),
    onSuccess: invalidatePatientData,
  });

  const addHistoryMutation = useMutation({
    mutationFn: (payload: { category: HistoryEntry["category"]; description: string }) =>
      authorizedRequest(`/patients/${patientId}/history`, { method: "POST", body: payload }),
    onSuccess: invalidatePatientData,
  });

  if (patientQuery.isLoading) {
    return <p className="text-slate-600">{t("loading")}</p>;
  }

  if (patientQuery.isError || !patientQuery.data) {
    return (
      <div className="space-y-4">
        <Link href="/patients" className="text-sm font-medium text-teal-700 hover:text-teal-900">
          ← {t("backToList")}
        </Link>
        <p className="text-rose-700">
          {patientQuery.error instanceof ApiError ? patientQuery.error.message : t("loadError")}
        </p>
      </div>
    );
  }

  const patient = patientQuery.data;
  const tabs: { key: TabKey; label: string }[] = [
    { key: "overview", label: t("tabOverview") },
    { key: "allergies", label: t("tabAllergies") },
    { key: "medications", label: t("tabMedications") },
    { key: "history", label: t("tabHistory") },
    { key: "timeline", label: t("tabTimeline") },
  ];

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link href="/patients" className="text-sm font-medium text-teal-700 hover:text-teal-900">
          ← {t("backToList")}
        </Link>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">{patient.mrn}</p>
          <h2 className="mt-1 text-3xl font-semibold text-slate-900">{patientDisplayName(patient)}</h2>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-slate-500">{t("dateOfBirth")}</dt>
              <dd className="font-medium text-slate-900">{formatDate(patient.date_of_birth, locale)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("sex")}</dt>
              <dd className="font-medium text-slate-900">{patient.sex ?? t("sexUnknown")}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("status")}</dt>
              <dd className="font-medium text-slate-900">{patient.status}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{t("preferredLocale")}</dt>
              <dd className="font-medium text-slate-900">{patient.preferred_locale}</dd>
            </div>
          </dl>
          <div className="mt-6 border-t border-slate-100 pt-4">
            <StartConsultationButton patientId={patient.id} clinicId={patient.clinic_id} />
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-4 py-2 text-sm ${
              activeTab === tab.key
                ? "bg-teal-700 text-white"
                : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "overview" ? (
        <OverviewPanel
          allergies={allergiesQuery.data ?? []}
          medications={medicationsQuery.data ?? []}
          history={historyQuery.data ?? []}
        />
      ) : null}

      {activeTab === "allergies" ? (
        <RecordPanel
          title={t("tabAllergies")}
          emptyLabel={t("noAllergies")}
          items={(allergiesQuery.data ?? []).map((item) => ({
            id: item.id,
            primary: item.substance_name,
            secondary: [item.reaction, item.severity].filter(Boolean).join(" · ") || item.status,
          }))}
          formFields={[
            { name: "substance_name", label: t("substance"), required: true },
            { name: "reaction", label: t("reaction") },
            { name: "severity", label: t("severity") },
          ]}
          isPending={addAllergyMutation.isPending}
          onSubmit={(values) =>
            addAllergyMutation.mutate({
              substance_name: values.substance_name ?? "",
              reaction: values.reaction,
              severity: values.severity,
            })
          }
        />
      ) : null}

      {activeTab === "medications" ? (
        <RecordPanel
          title={t("tabMedications")}
          emptyLabel={t("noMedications")}
          items={(medicationsQuery.data ?? []).map((item) => ({
            id: item.id,
            primary: item.drug_name,
            secondary: item.dose ?? item.status,
          }))}
          formFields={[
            { name: "drug_name", label: t("drugName"), required: true },
            { name: "dose", label: t("dose") },
          ]}
          isPending={addMedicationMutation.isPending}
          onSubmit={(values) =>
            addMedicationMutation.mutate({
              drug_name: values.drug_name ?? "",
              dose: values.dose,
            })
          }
        />
      ) : null}

      {activeTab === "history" ? (
        <HistoryPanel
          entries={historyQuery.data ?? []}
          isPending={addHistoryMutation.isPending}
          onSubmit={(values) => addHistoryMutation.mutate(values)}
        />
      ) : null}

      {activeTab === "timeline" ? (
        <TimelinePanel events={timelineQuery.data ?? []} isLoading={timelineQuery.isLoading} locale={locale} />
      ) : null}
    </div>
  );
}

function OverviewPanel({
  allergies,
  medications,
  history,
}: {
  allergies: Allergy[];
  medications: Medication[];
  history: HistoryEntry[];
}) {
  const t = useTranslations("patients");

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <SummaryCard title={t("tabAllergies")} count={allergies.length} empty={t("noAllergies")} />
      <SummaryCard title={t("tabMedications")} count={medications.length} empty={t("noMedications")} />
      <SummaryCard title={t("tabHistory")} count={history.length} empty={t("noHistory")} />
    </div>
  );
}

function SummaryCard({ title, count, empty }: { title: string; count: number; empty: string }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-3 text-3xl font-semibold text-teal-800">{count}</p>
      <p className="mt-2 text-sm text-slate-600">{count === 0 ? empty : title}</p>
    </article>
  );
}

type FormField = {
  name: string;
  label: string;
  required?: boolean;
};

function RecordPanel({
  title,
  emptyLabel,
  items,
  formFields,
  isPending,
  onSubmit,
}: {
  title: string;
  emptyLabel: string;
  items: { id: string; primary: string; secondary: string }[];
  formFields: FormField[];
  isPending: boolean;
  onSubmit: (values: Record<string, string>) => void;
}) {
  const t = useTranslations("patients");
  const [values, setValues] = useState<Record<string, string>>({});

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const requiredMissing = formFields.some((field) => field.required && !values[field.name]?.trim());
    if (requiredMissing) {
      return;
    }

    onSubmit(values);
    setValues({});
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        {items.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">{emptyLabel}</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {items.map((item) => (
              <li key={item.id} className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="font-medium text-slate-900">{item.primary}</p>
                <p className="text-sm text-slate-600">{item.secondary}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-900">{t("addRecord")}</h4>
        <div className="mt-4 space-y-3">
          {formFields.map((field) => (
            <label key={field.name} className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-slate-700">{field.label}</span>
              <input
                required={field.required}
                value={values[field.name] ?? ""}
                onChange={(event) =>
                  setValues((current) => ({ ...current, [field.name]: event.target.value }))
                }
                className="rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
          ))}
        </div>
        <button
          type="submit"
          disabled={isPending}
          className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {isPending ? t("saving") : t("saveRecord")}
        </button>
      </form>
    </div>
  );
}

function HistoryPanel({
  entries,
  isPending,
  onSubmit,
}: {
  entries: HistoryEntry[];
  isPending: boolean;
  onSubmit: (values: { category: HistoryEntry["category"]; description: string }) => void;
}) {
  const t = useTranslations("patients");
  const [category, setCategory] = useState<HistoryEntry["category"]>("medical");
  const [description, setDescription] = useState("");

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!description.trim()) {
      return;
    }

    onSubmit({ category, description });
    setDescription("");
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">{t("tabHistory")}</h3>
        {entries.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">{t("noHistory")}</p>
        ) : (
          <ul className="mt-4 space-y-3">
            {entries.map((entry) => (
              <li key={entry.id} className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                  {t(`historyCategory.${entry.category}`)}
                </p>
                <p className="mt-1 font-medium text-slate-900">{entry.description}</p>
                {entry.onset_date ? (
                  <p className="mt-1 text-sm text-slate-600">{entry.onset_date}</p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <form onSubmit={handleSubmit} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h4 className="text-sm font-semibold text-slate-900">{t("addRecord")}</h4>
        <div className="mt-4 space-y-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("historyCategoryLabel")}</span>
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as HistoryEntry["category"])}
              className="rounded-md border border-slate-300 px-3 py-2"
            >
              <option value="medical">{t("historyCategory.medical")}</option>
              <option value="surgical">{t("historyCategory.surgical")}</option>
              <option value="family">{t("historyCategory.family")}</option>
              <option value="social">{t("historyCategory.social")}</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("description")}</span>
            <textarea
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={4}
              className="rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={isPending}
          className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {isPending ? t("saving") : t("saveRecord")}
        </button>
      </form>
    </div>
  );
}

function timelineTypeLabel(
  t: ReturnType<typeof useTranslations<"patients">>,
  eventType: string,
): string {
  switch (eventType) {
    case "appointment":
      return t("timelineType.appointment");
    case "encounter":
      return t("timelineType.encounter");
    case "history":
      return t("timelineType.history");
    case "medication":
      return t("timelineType.medication");
    case "document":
      return t("timelineType.document");
    default:
      return eventType;
  }
}

function TimelinePanel({
  events,
  isLoading,
  locale,
}: {
  events: TimelineEvent[];
  isLoading: boolean;
  locale: string;
}) {
  const t = useTranslations("patients");

  if (isLoading) {
    return <p className="text-slate-600">{t("loading")}</p>;
  }

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        {t("noTimeline")}
      </div>
    );
  }

  return (
    <ol className="relative space-y-4 border-s-2 border-slate-200 ps-6">
      {events.map((event, index) => (
        <li key={`${event.event_type}-${event.occurred_at}-${index}`} className="relative">
          <span className="absolute -start-[1.6rem] top-1 h-3 w-3 rounded-full bg-teal-700" />
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-slate-900">{event.title}</p>
              <time className="text-xs text-slate-500">{formatDateTime(event.occurred_at, locale)}</time>
            </div>
            <p className="mt-1 text-xs uppercase tracking-wide text-teal-700">
              {timelineTypeLabel(t, event.event_type)}
            </p>
          </article>
        </li>
      ))}
    </ol>
  );
}
