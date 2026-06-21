"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { useAuth } from "@/lib/auth/auth-context";
import { formatDate, patientDisplayName } from "@/lib/format";

type DashboardSummary = {
  patients_total: number;
  encounters_total: number;
  consultations_completed: number;
  pending_ai_reviews: number;
  appointments_upcoming: number;
  export_jobs_pending: number;
  erasure_requests_pending: number;
  unread_notifications: number;
};

type DashboardPatient = {
  id: string;
  mrn: string;
  given_name: string;
  family_name: string;
  status: string;
  preferred_locale: string;
  updated_at: string;
};

type DashboardActivity = {
  id: string;
  kind: string;
  title: string;
  subtitle: string;
  occurred_at: string;
  patient_id: string | null;
};

type DashboardAiStatus = {
  extraction_enabled: boolean;
  suggestions_enabled: boolean;
  red_flags_enabled: boolean;
  pending_reviews: number;
  eval_passed: boolean;
  provider: string;
};

type DashboardOverview = {
  summary: DashboardSummary;
  recent_patients: DashboardPatient[];
  activity: DashboardActivity[];
  ai_status: DashboardAiStatus;
  consultations_in_progress: number;
  signed_notes_total: number;
};

type NotificationItem = {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

function KpiCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: number;
  hint?: string;
  accent: "teal" | "indigo" | "amber" | "rose" | "slate";
}) {
  const accents: Record<string, string> = {
    teal: "from-teal-500 to-emerald-600",
    indigo: "from-indigo-500 to-violet-600",
    amber: "from-amber-500 to-orange-600",
    rose: "from-rose-500 to-pink-600",
    slate: "from-slate-600 to-slate-800",
  };

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${accents[accent]}`} />
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 text-4xl font-semibold tabular-nums tracking-tight text-slate-900">{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </article>
  );
}

function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        ok ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-slate-400"}`} />
      {label}
    </span>
  );
}

export function DashboardView() {
  const t = useTranslations("dashboard");
  const locale = useLocale();
  const { authorizedRequest, user } = useAuth();
  const queryClient = useQueryClient();

  const overviewQuery = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => authorizedRequest<DashboardOverview>("/dashboard/overview"),
  });

  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: () => authorizedRequest<NotificationItem[]>("/notifications"),
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) =>
      authorizedRequest<NotificationItem>(`/notifications/${notificationId}/read`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
    },
  });

  const overview = overviewQuery.data;
  const summary = overview?.summary;
  const canAdmin =
    (user?.permissions.includes("clinic:read") ?? false) ||
    (user?.permissions.includes("user:read") ?? false);
  const canGovernance = user?.permissions.includes("governance:manage") ?? false;

  const today = new Intl.DateTimeFormat(locale, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date());

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl border border-teal-900/10 bg-gradient-to-br from-slate-900 via-teal-900 to-emerald-900 px-8 py-10 text-white shadow-xl">
        <div className="pointer-events-none absolute -end-16 -top-16 h-64 w-64 rounded-full bg-teal-400/10 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 start-1/3 h-48 w-48 rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-widest text-teal-200/90">{today}</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
              {t("welcome", { name: user?.full_name ?? t("clinician") })}
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-relaxed text-teal-50/90">{t("heroSubtitle")}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/patients"
              className="inline-flex items-center justify-center rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-teal-900 shadow-sm transition hover:bg-teal-50"
            >
              {t("openPatients")}
            </Link>
            {canGovernance ? (
              <Link
                href="/governance"
                className="inline-flex items-center justify-center rounded-xl border border-white/25 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/15"
              >
                {t("openGovernance")}
              </Link>
            ) : null}
            {canAdmin ? (
              <Link
                href="/admin"
                className="inline-flex items-center justify-center rounded-xl border border-white/25 bg-white/10 px-5 py-2.5 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/15"
              >
                {t("openAdmin")}
              </Link>
            ) : null}
          </div>
        </div>
      </section>

      {overviewQuery.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="h-32 animate-pulse rounded-2xl bg-slate-200/70" />
          ))}
        </div>
      ) : overviewQuery.isError || !summary ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-800">
          {t("loadError")}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label={t("patientsTotal")} value={summary.patients_total} accent="teal" />
            <KpiCard
              label={t("consultationsInProgress")}
              value={overview.consultations_in_progress}
              hint={t("signedNotes", { count: overview.signed_notes_total })}
              accent="indigo"
            />
            <KpiCard label={t("appointmentsUpcoming")} value={summary.appointments_upcoming} accent="slate" />
            <KpiCard
              label={t("pendingAiReviews")}
              value={summary.pending_ai_reviews}
              hint={summary.pending_ai_reviews > 0 ? t("actionNeeded") : t("allClear")}
              accent="amber"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-3">
            <section className="xl:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{t("recentPatientsTitle")}</h2>
                  <p className="text-sm text-slate-500">{t("recentPatientsSubtitle")}</p>
                </div>
                <Link href="/patients" className="text-sm font-medium text-teal-700 hover:text-teal-800">
                  {t("viewAll")}
                </Link>
              </div>
              {overview.recent_patients.length === 0 ? (
                <p className="mt-6 rounded-xl bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
                  {t("noPatients")}
                </p>
              ) : (
                <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-50 text-start text-slate-500">
                      <tr>
                        <th className="px-4 py-3 font-medium">{t("patient")}</th>
                        <th className="px-4 py-3 font-medium">{t("mrn")}</th>
                        <th className="px-4 py-3 font-medium">{t("status")}</th>
                        <th className="px-4 py-3 font-medium">{t("updated")}</th>
                        <th className="px-4 py-3 font-medium">{t("actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.recent_patients.map((patient) => (
                        <tr key={patient.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                          <td className="px-4 py-3 font-medium text-slate-900">
                            {patientDisplayName(patient)}
                          </td>
                          <td className="px-4 py-3 text-slate-600">{patient.mrn}</td>
                          <td className="px-4 py-3">
                            <span className="rounded-full bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-800">
                              {patient.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500">{formatDate(patient.updated_at, locale)}</td>
                          <td className="px-4 py-3">
                            <Link
                              href={`/patients/${patient.id}`}
                              className="font-medium text-teal-700 hover:text-teal-900"
                            >
                              {t("examine")}
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{t("aiPanelTitle")}</h2>
              <p className="mt-1 text-sm text-slate-500">{t("aiPanelSubtitle")}</p>
              <div className="mt-5 space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{t("provider")}</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{overview.ai_status.provider}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusPill ok={overview.ai_status.extraction_enabled} label={t("aiExtraction")} />
                  <StatusPill ok={overview.ai_status.suggestions_enabled} label={t("aiSuggestions")} />
                  <StatusPill ok={overview.ai_status.red_flags_enabled} label={t("aiRedFlags")} />
                  <StatusPill ok={overview.ai_status.eval_passed} label={t("evalGates")} />
                </div>
                <p className="text-sm text-slate-600">
                  {overview.ai_status.pending_reviews > 0
                    ? t("aiPendingReviews", { count: overview.ai_status.pending_reviews })
                    : t("aiAllReviewed")}
                </p>
              </div>
            </section>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900">{t("activityTitle")}</h2>
              <p className="text-sm text-slate-500">{t("activitySubtitle")}</p>
              {overview.activity.length === 0 ? (
                <p className="mt-4 rounded-xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  {t("noActivity")}
                </p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {overview.activity.map((item) => (
                    <li
                      key={`${item.kind}-${item.id}`}
                      className="flex items-start gap-3 rounded-xl border border-slate-100 px-4 py-3"
                    >
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-bold uppercase text-teal-800">
                        {item.kind.slice(0, 1)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-slate-900">{item.title}</p>
                        <p className="text-sm text-slate-500">{item.subtitle}</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {new Date(item.occurred_at).toLocaleString(locale)}
                        </p>
                      </div>
                      {item.patient_id ? (
                        <Link
                          href={`/patients/${item.patient_id}`}
                          className="shrink-0 text-xs font-medium text-teal-700 hover:text-teal-900"
                        >
                          {t("open")}
                        </Link>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{t("notificationsTitle")}</h2>
                  <p className="text-sm text-slate-500">{t("notificationsSubtitle")}</p>
                </div>
                {summary.unread_notifications > 0 ? (
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                    {t("unreadBadge", { count: summary.unread_notifications })}
                  </span>
                ) : null}
              </div>
              {notificationsQuery.isLoading ? (
                <div className="mt-4 space-y-3">
                  {Array.from({ length: 3 }).map((_, index) => (
                    <div key={index} className="h-16 animate-pulse rounded-xl bg-slate-100" />
                  ))}
                </div>
              ) : (notificationsQuery.data ?? []).length === 0 ? (
                <p className="mt-4 rounded-xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  {t("noNotifications")}
                </p>
              ) : (
                <ul className="mt-4 max-h-80 space-y-3 overflow-y-auto">
                  {(notificationsQuery.data ?? []).slice(0, 8).map((item) => (
                    <li
                      key={item.id}
                      className={`rounded-xl border px-4 py-3 ${
                        item.is_read ? "border-slate-200 bg-slate-50" : "border-teal-200 bg-teal-50/50"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className={`font-medium ${item.is_read ? "text-slate-700" : "text-slate-900"}`}>
                            {item.title}
                          </p>
                          <p className="mt-1 text-sm text-slate-600">{item.body}</p>
                        </div>
                        {!item.is_read ? (
                          <button
                            type="button"
                            onClick={() => markReadMutation.mutate(item.id)}
                            disabled={markReadMutation.isPending}
                            className="shrink-0 rounded-lg border border-teal-300 bg-white px-2.5 py-1 text-xs font-medium text-teal-800 hover:bg-teal-50"
                          >
                            {t("markRead")}
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-50 to-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t("complianceTitle")}</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-2xl font-semibold text-slate-900">{summary.export_jobs_pending}</p>
                <p className="mt-1 text-sm text-slate-600">{t("exportJobsPending")}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-2xl font-semibold text-slate-900">{summary.erasure_requests_pending}</p>
                <p className="mt-1 text-sm text-slate-600">{t("erasurePending")}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-2xl font-semibold text-slate-900">{summary.encounters_total}</p>
                <p className="mt-1 text-sm text-slate-600">{t("encountersTotal")}</p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
