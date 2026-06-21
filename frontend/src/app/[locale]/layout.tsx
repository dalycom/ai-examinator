import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { ApiStatusBadge } from "@/components/api-status-badge";
import { AppNav } from "@/components/app-nav";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { SkipToMainLink } from "@/components/skip-to-main";
import { AppProviders } from "@/components/providers";
import { localeDirection, routing, type AppLocale } from "@/i18n/routing";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  if (!routing.locales.includes(locale as AppLocale)) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();
  const t = await getTranslations("app");
  const direction = localeDirection[locale as AppLocale];

  return (
    <html lang={locale} dir={direction}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <NextIntlClientProvider messages={messages}>
          <AppProviders>
            <SkipToMainLink />
            <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
              <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-6">
                <div>
                  <p className="text-sm font-medium uppercase tracking-wide text-teal-700">
                    {t("phase")}
                  </p>
                  <h1 className="text-3xl font-semibold text-slate-900">{t("title")}</h1>
                  <p className="mt-1 text-slate-600">{t("subtitle")}</p>
                </div>
                <div className="flex flex-col items-end gap-3 sm:flex-row sm:items-center">
                  <ApiStatusBadge />
                  <LocaleSwitcher />
                </div>
              </header>
              <AppNav />
              <main id="main-content" tabIndex={-1} className="flex-1 outline-none focus-visible:ring-2 focus-visible:ring-teal-500">
                {children}
              </main>
            </div>
          </AppProviders>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
