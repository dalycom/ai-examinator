import { getTranslations, setRequestLocale } from "next-intl/server";

import { Link } from "@/i18n/navigation";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("app");
  const labels = await getTranslations("labels");

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="max-w-2xl text-lg leading-8 text-slate-700">{t("description")}</p>
        <Link
          href="/dashboard"
          className="mt-6 inline-flex rounded-lg bg-teal-700 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-800"
        >
          {t("getStarted")}
        </Link>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {labels("patientProvided")}
          </p>
          <p className="mt-2 text-sm text-slate-700">
            Patient-reported symptoms and history appear with a neutral clinical label.
          </p>
        </article>
        <article className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
            {labels("aiSuggestion")}
          </p>
          <p className="mt-2 text-sm text-amber-950">
            AI outputs are suggestions only and require explicit doctor review before entering the record.
          </p>
        </article>
        <article className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
            {labels("doctorApproved")}
          </p>
          <p className="mt-2 text-sm text-emerald-950">
            Only doctor-approved content can become part of a signed medical record.
          </p>
        </article>
      </section>
    </div>
  );
}
