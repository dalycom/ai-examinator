from app.adapters.diarization.port import DiarizationPort, DiarizationResult


class StubDiarizationAdapter(DiarizationPort):
    def diarize(self, *, storage_key: str, mime_type: str) -> list[DiarizationResult]:
        return [
            DiarizationResult(speaker="doctor", start_ms=0, end_ms=3200),
            DiarizationResult(speaker="patient", start_ms=3300, end_ms=7100),
            DiarizationResult(speaker="doctor", start_ms=7200, end_ms=11000),
        ]


def get_diarization_adapter() -> DiarizationPort:
    return StubDiarizationAdapter()
