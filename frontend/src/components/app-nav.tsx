"use client";

import { useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";
import { useAuth } from "@/lib/auth/auth-context";

export function AppNav() {
  const t = useTranslations("nav");
  const auth = useTranslations("auth");
  const pathname = usePathname();
  const { user, isAuthenticated, logout } = useAuth();

  const linkClass = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`)
      ? "font-medium text-teal-800"
      : "text-slate-600 hover:text-teal-700";

  const canManage = user?.permissions.includes("governance:manage") ?? false;
  const canAdmin =
    (user?.permissions.includes("clinic:read") ?? false) ||
    (user?.permissions.includes("user:read") ?? false);

  return (
    <nav className="mb-8 flex flex-wrap items-center gap-4 border-b border-slate-200 pb-4 text-sm" aria-label={t("primary")}>
      <Link href="/" className={linkClass("/")}>
        {t("home")}
      </Link>
      {isAuthenticated ? (
        <>
          <Link href="/dashboard" className={linkClass("/dashboard")}>
            {t("dashboard")}
          </Link>
          <Link href="/patients" className={linkClass("/patients")}>
            {t("patients")}
          </Link>
          {canAdmin ? (
            <Link href="/admin" className={linkClass("/admin")}>
              {t("admin")}
            </Link>
          ) : null}
          {canManage ? (
            <Link href="/governance" className={linkClass("/governance")}>
              {t("governance")}
            </Link>
          ) : null}
          <div className="ms-auto flex flex-wrap items-center gap-3">
            <span className="text-slate-600">{user?.full_name}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-100"
            >
              {auth("logout")}
            </button>
          </div>
        </>
      ) : (
        <Link href="/login" className={`ms-auto ${linkClass("/login")}`}>
          {auth("login")}
        </Link>
      )}
    </nav>
  );
}
