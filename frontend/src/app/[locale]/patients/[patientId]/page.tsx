import { AuthGuard } from "@/components/auth-guard";
import { PatientProfileView } from "@/components/patients/patient-profile";
import { setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string; patientId: string }>;
};

export default async function PatientProfilePage({ params }: Props) {
  const { locale, patientId } = await params;
  setRequestLocale(locale);

  return (
    <AuthGuard>
      <PatientProfileView patientId={patientId} />
    </AuthGuard>
  );
}
