"use client";

import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { useAuth } from "@/lib/auth/auth-context";

type Props = {
  patientId: string;
  clinicId: string | null;
};

export function StartConsultationButton({ patientId, clinicId }: Props) {
  const t = useTranslations("consultation");
  const router = useRouter();
  const { authorizedRequest } = useAuth();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onStart = async () => {
    setError(null);
    setIsStarting(true);
    try {
      const me = await authorizedRequest<{ id: string }>("/auth/me");
      let resolvedClinicId = clinicId;
      if (!resolvedClinicId) {
        const clinics = await authorizedRequest<Array<{ id: string }>>("/clinics");
        resolvedClinicId = clinics[0]?.id ?? null;
      }
      if (!resolvedClinicId) {
        throw new Error(t("noClinic"));
      }

      const encounter = await authorizedRequest<{ id: string }>("/encounters", {
        method: "POST",
        body: {
          patient_id: patientId,
          clinic_id: resolvedClinicId,
          clinician_id: me.id,
        },
      });

      const session = await authorizedRequest<{ id: string }>(
        `/encounters/${encounter.id}/sessions`,
        { method: "POST" },
      );

      router.push(`/patients/${patientId}/consultation/${session.id}`);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : t("startFailed"));
    } finally {
      setIsStarting(false);
    }
  };

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        type="button"
        disabled={isStarting}
        onClick={() => void onStart()}
        className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-60"
      >
        {isStarting ? t("starting") : t("startConsultation")}
      </button>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
    </div>
  );
}
