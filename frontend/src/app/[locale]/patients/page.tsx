import { AuthGuard } from "@/components/auth-guard";
import { PatientListView } from "@/components/patients/patient-list";
import { getTranslations, setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function PatientsPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  await getTranslations("patients");

  return (
    <AuthGuard>
      <PatientListView />
    </AuthGuard>
  );
}
