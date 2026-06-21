"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "next/navigation";

import { localeNames, routing, type AppLocale } from "@/i18n/routing";

export function LocaleSwitcher() {
  const t = useTranslations("app");
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const pathname = usePathname();

  const onChange = (nextLocale: AppLocale) => {
    const segments = pathname.split("/");
    segments[1] = nextLocale;
    router.replace(segments.join("/") || `/${nextLocale}`);
  };

  return (
    <label className="flex items-center gap-2 text-sm text-slate-600">
      <span>{t("language")}</span>
      <select
        className="rounded-md border border-slate-300 bg-white px-2 py-1 text-slate-900"
        value={locale}
        onChange={(event) => onChange(event.target.value as AppLocale)}
        aria-label={t("language")}
      >
        {routing.locales.map((code) => (
          <option key={code} value={code}>
            {localeNames[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
