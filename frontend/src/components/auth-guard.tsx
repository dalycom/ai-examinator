"use client";

import { useEffect, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import { useRouter } from "@/i18n/navigation";
import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  children: ReactNode;
};

export function AuthGuard({ children }: Props) {
  const t = useTranslations("auth");
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-600">
        {t("loadingSession")}
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return children;
}
