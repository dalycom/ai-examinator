from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptSegmentResult:
    seq: int
    speaker: str
    language: str
    text: str
    confidence: float
    start_ms: int
    end_ms: int


class SpeechToTextPort:
    def transcribe_batch(
        self,
        *,
        storage_key: str,
        mime_type: str,
        language_hint: str | None = None,
    ) -> list[TranscriptSegmentResult]:
        raise NotImplementedError
