from dataclasses import dataclass


@dataclass(frozen=True)
class DiarizationResult:
    speaker: str
    start_ms: int
    end_ms: int


class DiarizationPort:
    def diarize(self, *, storage_key: str, mime_type: str) -> list[DiarizationResult]:
        raise NotImplementedError
