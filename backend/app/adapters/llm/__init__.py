from dataclasses import replace

from app.adapters.llm.port import LlmPort
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.core.config import get_settings


class LocalLlmAdapter(StubLlmAdapter):
    """Self-hosted LLM path scaffold — delegates to stub until a real endpoint is configured."""

    def extract_clinical_information(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        result = super().extract_clinical_information(*args, **kwargs)
        return replace(
            result,
            model_id=get_settings().llm_model_id,
            provider="self_hosted",
        )


def get_llm_adapter() -> LlmPort:
    settings = get_settings()
    match settings.llm_provider:
        case "local" | "self_hosted":
            return LocalLlmAdapter()
        case "stub":
            return StubLlmAdapter()
        case _:
            return StubLlmAdapter()
