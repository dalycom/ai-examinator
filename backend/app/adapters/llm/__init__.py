from app.adapters.llm.local_adapter import LocalLlmAdapter
from app.adapters.llm.model_presets import list_model_presets
from app.adapters.llm.port import LlmPort
from app.adapters.llm.settings_resolver import resolve_llm_config
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.core.config import get_settings


def get_llm_adapter() -> LlmPort:
    resolved = resolve_llm_config(get_settings())
    match resolved.provider:
        case "local" | "self_hosted":
            return LocalLlmAdapter()
        case "stub":
            return StubLlmAdapter()
        case _:
            return StubLlmAdapter()


__all__ = ["LocalLlmAdapter", "StubLlmAdapter", "get_llm_adapter", "list_model_presets", "resolve_llm_config"]
