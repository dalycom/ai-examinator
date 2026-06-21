import { AuthGuard } from "@/components/auth-guard";
import { ConsultationWorkspace } from "@/components/consultation/consultation-workspace";
import { setRequestLocale } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string; patientId: string; sessionId: string }>;
};

export default async function ConsultationPage({ params }: Props) {
  const { locale, patientId, sessionId } = await params;
  setRequestLocale(locale);

  return (
    <AuthGuard>
      <ConsultationWorkspace patientId={patientId} sessionId={sessionId} />
    </AuthGuard>
  );
}
