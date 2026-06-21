"use client";

import { useTranslations } from "next-intl";

export function SkipToMainLink() {
  const t = useTranslations("a11y");

  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-teal-800 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white focus:outline-none focus:ring-2 focus:ring-teal-300"
    >
      {t("skipToMain")}
    </a>
  );
}
