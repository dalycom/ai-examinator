from app.adapters.stt.port import SpeechToTextPort, TranscriptSegmentResult


class StubSpeechToTextAdapter(SpeechToTextPort):
    """Deterministic synthetic transcript for dev/demo (no real PHI, no external API)."""

    def transcribe_batch(
        self,
        *,
        storage_key: str,
        mime_type: str,
        language_hint: str | None = None,
    ) -> list[TranscriptSegmentResult]:
        language = language_hint or "en"
        return [
            TranscriptSegmentResult(
                seq=1,
                speaker="doctor",
                language=language,
                text="Good morning. What brings you in today?",
                confidence=0.91,
                start_ms=0,
                end_ms=3200,
            ),
            TranscriptSegmentResult(
                seq=2,
                speaker="patient",
                language=language,
                text="I've had a headache for two days.",
                confidence=0.88,
                start_ms=3300,
                end_ms=7100,
            ),
            TranscriptSegmentResult(
                seq=3,
                speaker="doctor",
                language=language,
                text="Any fever, vision changes, or neck stiffness?",
                confidence=0.9,
                start_ms=7200,
                end_ms=11000,
            ),
        ]


def get_speech_to_text_adapter() -> SpeechToTextPort:
    return StubSpeechToTextAdapter()
