"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { useState } from "react";

import { useAuth } from "@/lib/auth/auth-context";

export function LoginForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("doctor@synthetic-demo.example.com");
  const [password, setPassword] = useState("SyntheticDoctor123!");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : t("loginFailed"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">{t("loginTitle")}</h2>
        <p className="mt-1 text-sm text-slate-600">{t("loginSubtitle")}</p>
      </div>

      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t("email")}</span>
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t("password")}</span>
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2"
          />
        </label>

        {error ? <p className="text-sm text-rose-700">{error}</p> : null}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
        >
          {isSubmitting ? t("signingIn") : t("signIn")}
        </button>
      </form>

      <div className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-4 text-sm text-teal-950">
        <p className="font-semibold">{t("demoCredentialsTitle")}</p>
        <ul className="mt-2 space-y-2 text-xs leading-5">
          <li>
            <span className="font-medium">{t("demoDoctor")}:</span> doctor@synthetic-demo.example.com / SyntheticDoctor123!
          </li>
          <li>
            <span className="font-medium">{t("demoAdmin")}:</span> admin@synthetic-demo.example.com / SyntheticDemo123!
          </li>
        </ul>
        <p className="mt-3 text-xs text-teal-800">{t("demoSeedHint")}</p>
      </div>
    </div>
  );
}
