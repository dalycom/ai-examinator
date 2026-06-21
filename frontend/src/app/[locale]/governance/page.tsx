import { AuthGuard } from "@/components/auth-guard";
import { GovernanceView } from "@/components/governance/governance-view";
import { getTranslations, setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function GovernancePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  await getTranslations("governance");

  return (
    <AuthGuard>
      <GovernanceView />
    </AuthGuard>
  );
}
