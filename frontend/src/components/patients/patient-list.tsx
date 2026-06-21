"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Link } from "@/i18n/navigation";
import { ApiError } from "@/lib/api/client";
import type { Patient } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/auth-context";
import { formatDate, patientDisplayName } from "@/lib/format";

type CreatePatientInput = {
  given_name: string;
  family_name: string;
  date_of_birth?: string;
  sex?: string;
  preferred_locale?: string;
};

export function PatientListView() {
  const t = useTranslations("patients");
  const locale = useLocale();
  const { authorizedRequest } = useAuth();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<CreatePatientInput>({
    given_name: "",
    family_name: "",
    date_of_birth: "",
    sex: "",
    preferred_locale: locale,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const patientsQuery = useQuery({
    queryKey: ["patients"],
    queryFn: () => authorizedRequest<Patient[]>("/patients"),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreatePatientInput) =>
      authorizedRequest<Patient>("/patients", {
        method: "POST",
        body: {
          given_name: payload.given_name,
          family_name: payload.family_name,
          date_of_birth: payload.date_of_birth || null,
          sex: payload.sex || null,
          preferred_locale: payload.preferred_locale || locale,
        },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["patients"] });
      setShowForm(false);
      setForm({
        given_name: "",
        family_name: "",
        date_of_birth: "",
        sex: "",
        preferred_locale: locale,
      });
      setFormError(null);
    },
    onError: (error: Error) => {
      setFormError(error.message);
    },
  });

  const filteredPatients = useMemo(() => {
    const rows = patientsQuery.data ?? [];
    const needle = search.trim().toLowerCase();
    if (!needle) {
      return rows;
    }

    return rows.filter((patient) => {
      const haystack = `${patient.mrn} ${patient.given_name} ${patient.family_name}`.toLowerCase();
      return haystack.includes(needle);
    });
  }, [patientsQuery.data, search]);

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.given_name.trim() || !form.family_name.trim()) {
      setFormError(t("validationNameRequired"));
      return;
    }

    createMutation.mutate(form);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">{t("title")}</h2>
          <p className="mt-1 text-slate-600">{t("subtitle")}</p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
        >
          {showForm ? t("cancelCreate") : t("createPatient")}
        </button>
      </div>

      {showForm ? (
        <form
          onSubmit={onSubmit}
          className="grid gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-2"
        >
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("givenName")}</span>
            <input
              required
              value={form.given_name}
              onChange={(event) => setForm((current) => ({ ...current, given_name: event.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("familyName")}</span>
            <input
              required
              value={form.family_name}
              onChange={(event) => setForm((current) => ({ ...current, family_name: event.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("dateOfBirth")}</span>
            <input
              type="date"
              value={form.date_of_birth}
              onChange={(event) => setForm((current) => ({ ...current, date_of_birth: event.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">{t("sex")}</span>
            <select
              value={form.sex}
              onChange={(event) => setForm((current) => ({ ...current, sex: event.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2"
            >
              <option value="">{t("sexUnknown")}</option>
              <option value="female">{t("sexFemale")}</option>
              <option value="male">{t("sexMale")}</option>
              <option value="other">{t("sexOther")}</option>
            </select>
          </label>
          {formError ? <p className="text-sm text-rose-700 md:col-span-2">{formError}</p> : null}
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
            >
              {createMutation.isPending ? t("saving") : t("savePatient")}
            </button>
          </div>
        </form>
      ) : null}

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">{t("search")}</span>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className="max-w-md rounded-md border border-slate-300 px-3 py-2"
        />
      </label>

      {patientsQuery.isLoading ? (
        <p className="text-slate-600">{t("loading")}</p>
      ) : patientsQuery.isError ? (
        <p className="text-rose-700">
          {patientsQuery.error instanceof ApiError ? patientsQuery.error.message : t("loadError")}
        </p>
      ) : filteredPatients.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
          {t("empty")}
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-start">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-700">{t("mrn")}</th>
                <th className="px-4 py-3 font-medium text-slate-700">{t("name")}</th>
                <th className="px-4 py-3 font-medium text-slate-700">{t("dateOfBirth")}</th>
                <th className="px-4 py-3 font-medium text-slate-700">{t("status")}</th>
                <th className="px-4 py-3 font-medium text-slate-700">{t("actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredPatients.map((patient) => (
                <tr key={patient.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{patient.mrn}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{patientDisplayName(patient)}</td>
                  <td className="px-4 py-3 text-slate-700">{formatDate(patient.date_of_birth, locale)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">
                      {patient.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/patients/${patient.id}`} className="font-medium text-teal-700 hover:text-teal-900">
                      {t("viewProfile")}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
