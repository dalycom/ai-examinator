"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ApiStatusBadge() {
  const t = useTranslations("app");
  const [status, setStatus] = useState<"checking" | "healthy" | "unavailable">("checking");

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiUrl}/health`)
      .then((response) => {
        if (!cancelled) {
          setStatus(response.ok ? "healthy" : "unavailable");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const label =
    status === "checking"
      ? t("checking")
      : status === "healthy"
        ? t("healthy")
        : t("unavailable");

  const color =
    status === "healthy"
      ? "bg-emerald-100 text-emerald-800"
      : status === "checking"
        ? "bg-amber-100 text-amber-800"
        : "bg-rose-100 text-rose-800";

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${color}`}>
      {t("apiStatus")}: {label}
    </span>
  );
}
