import { AuthGuard } from "@/components/auth-guard";
import { AdminView } from "@/components/admin/admin-view";
import { getTranslations, setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function AdminPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  await getTranslations("admin");

  return (
    <AuthGuard>
      <AdminView />
    </AuthGuard>
  );
}
