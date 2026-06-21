"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { useAuth } from "@/lib/auth/auth-context";

type FeatureFlag = {
  key: string;
  enabled: boolean;
  description: string | null;
};

type RetentionPolicy = {
  id: string;
  resource_type: string;
  retention_days: number;
  erasure_enabled: boolean;
};

type GovernanceDashboard = {
  feature_flags: FeatureFlag[];
  pending_ai_suggestions: number;
  recent_eval_runs: Array<{
    id: string;
    passed_gates: boolean;
    metrics: Record<string, unknown>;
    created_at: string;
  }>;
  retention_policies: RetentionPolicy[];
};

export function GovernanceView() {
  const t = useTranslations("governance");
  const { authorizedRequest, user } = useAuth();

  const dashboardQuery = useQuery({
    queryKey: ["governance-dashboard"],
    queryFn: () => authorizedRequest<GovernanceDashboard>("/governance/dashboard"),
    enabled: user?.permissions.includes("governance:manage") ?? false,
  });

  if (!user?.permissions.includes("governance:manage")) {
    return <p className="text-slate-600">{t("noAccess")}</p>;
  }

  const dashboard = dashboardQuery.data;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
        <p className="mt-1 text-slate-600">{t("subtitle")}</p>
      </header>

      {dashboardQuery.isLoading ? (
        <p className="text-slate-600">{t("loading")}</p>
      ) : dashboardQuery.isError ? (
        <p className="text-red-700">{t("loadError")}</p>
      ) : dashboard ? (
        <>
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {t("pendingAiReviews", { count: dashboard.pending_ai_suggestions })}
          </div>

          <section>
            <h2 className="text-lg font-medium text-slate-900">{t("featureFlagsTitle")}</h2>
            <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
              {dashboard.feature_flags.map((flag) => (
                <li key={flag.key} className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
                  <div>
                    <p className="font-medium text-slate-900">{flag.key}</p>
                    <p className="text-slate-500">{flag.description}</p>
                  </div>
                  <span
                    className={
                      flag.enabled
                        ? "rounded-full bg-teal-100 px-2 py-0.5 text-teal-800"
                        : "rounded-full bg-slate-100 px-2 py-0.5 text-slate-600"
                    }
                  >
                    {flag.enabled ? t("enabled") : t("disabled")}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-medium text-slate-900">{t("retentionTitle")}</h2>
            <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-start">
                  <tr>
                    <th className="px-4 py-2">{t("resourceType")}</th>
                    <th className="px-4 py-2">{t("retentionDays")}</th>
                    <th className="px-4 py-2">{t("erasureEnabled")}</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.retention_policies.map((policy) => (
                    <tr key={policy.id} className="border-t border-slate-200">
                      <td className="px-4 py-2">{policy.resource_type}</td>
                      <td className="px-4 py-2">{policy.retention_days}</td>
                      <td className="px-4 py-2">{policy.erasure_enabled ? t("yes") : t("no")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-medium text-slate-900">{t("evalRunsTitle")}</h2>
            {(dashboard.recent_eval_runs ?? []).length === 0 ? (
              <p className="mt-2 text-slate-600">{t("noEvalRuns")}</p>
            ) : (
              <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
                {dashboard.recent_eval_runs.map((run) => (
                  <li key={run.id} className="px-4 py-3 text-sm">
                    <span className="font-medium text-slate-900">{run.id.slice(0, 8)}</span>
                    <span className="ms-2 text-slate-500">
                      {run.passed_gates ? t("passed") : t("failed")} · {run.created_at}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
