from app.adapters.llm.local_adapter import LocalLlmAdapter
from app.adapters.llm.port import LlmPort
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.core.config import get_settings


def get_llm_adapter() -> LlmPort:
    settings = get_settings()
    match settings.llm_provider:
        case "local" | "self_hosted":
            return LocalLlmAdapter()
        case "stub":
            return StubLlmAdapter()
        case _:
            return StubLlmAdapter()
