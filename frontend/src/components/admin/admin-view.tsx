"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { useAuth } from "@/lib/auth/auth-context";

type Clinic = {
  id: string;
  name: string;
  timezone: string;
  status: string;
};

type User = {
  id: string;
  email: string;
  full_name: string;
  status: string;
};

type Role = {
  id: string;
  key: string;
  name: string;
  is_system: boolean;
};

export function AdminView() {
  const t = useTranslations("admin");
  const { authorizedRequest, user } = useAuth();

  const clinicsQuery = useQuery({
    queryKey: ["admin-clinics"],
    queryFn: () => authorizedRequest<Clinic[]>("/clinics"),
    enabled: user?.permissions.includes("clinic:read") ?? false,
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => authorizedRequest<User[]>("/users"),
    enabled: user?.permissions.includes("user:read") ?? false,
  });

  const rolesQuery = useQuery({
    queryKey: ["admin-roles"],
    queryFn: () => authorizedRequest<Role[]>("/roles"),
    enabled: user?.permissions.includes("role:read") ?? false,
  });

  if (!user?.permissions.includes("clinic:read") && !user?.permissions.includes("user:read")) {
    return <p className="text-slate-600">{t("noAccess")}</p>;
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">{t("title")}</h1>
        <p className="mt-1 text-slate-600">{t("subtitle")}</p>
      </header>

      <section>
        <h2 className="text-lg font-medium text-slate-900">{t("clinicsTitle")}</h2>
        {clinicsQuery.isLoading ? (
          <p className="mt-2 text-slate-600">{t("loading")}</p>
        ) : (
          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-start">
                <tr>
                  <th className="px-4 py-2">{t("name")}</th>
                  <th className="px-4 py-2">{t("timezone")}</th>
                  <th className="px-4 py-2">{t("status")}</th>
                </tr>
              </thead>
              <tbody>
                {(clinicsQuery.data ?? []).map((clinic) => (
                  <tr key={clinic.id} className="border-t border-slate-200">
                    <td className="px-4 py-2">{clinic.name}</td>
                    <td className="px-4 py-2">{clinic.timezone}</td>
                    <td className="px-4 py-2">{clinic.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-medium text-slate-900">{t("usersTitle")}</h2>
        {usersQuery.isLoading ? (
          <p className="mt-2 text-slate-600">{t("loading")}</p>
        ) : (
          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-start">
                <tr>
                  <th className="px-4 py-2">{t("name")}</th>
                  <th className="px-4 py-2">{t("email")}</th>
                  <th className="px-4 py-2">{t("status")}</th>
                </tr>
              </thead>
              <tbody>
                {(usersQuery.data ?? []).map((row) => (
                  <tr key={row.id} className="border-t border-slate-200">
                    <td className="px-4 py-2">{row.full_name}</td>
                    <td className="px-4 py-2">{row.email}</td>
                    <td className="px-4 py-2">{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-medium text-slate-900">{t("rolesTitle")}</h2>
        {rolesQuery.isLoading ? (
          <p className="mt-2 text-slate-600">{t("loading")}</p>
        ) : (
          <ul className="mt-3 divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {(rolesQuery.data ?? []).map((role) => (
              <li key={role.id} className="flex items-center justify-between px-4 py-3 text-sm">
                <span className="font-medium text-slate-900">{role.name}</span>
                <span className="text-slate-500">{role.key}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
