import { AuthGuard } from "@/components/auth-guard";
import { DashboardView } from "@/components/dashboard/dashboard-view";
import { getTranslations, setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function DashboardPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  await getTranslations("dashboard");

  return (
    <AuthGuard>
      <DashboardView />
    </AuthGuard>
  );
}
