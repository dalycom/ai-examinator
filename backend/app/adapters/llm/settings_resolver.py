"""Resolve effective LLM settings with optional clinical model presets."""

from dataclasses import dataclass

from app.adapters.llm.model_presets import get_model_preset
from app.core.config import Settings


@dataclass(frozen=True)
class ResolvedLlmConfig:
    provider: str
    model_id: str
    endpoint_url: str | None
    api_key: str | None
    timeout_seconds: int
    temperature: float
    prompt_version: str
    preset_name: str | None


def resolve_llm_config(settings: Settings) -> ResolvedLlmConfig:
    preset_name = settings.llm_model_preset
    if not preset_name:
        return ResolvedLlmConfig(
            provider=settings.llm_provider,
            model_id=settings.llm_model_id,
            endpoint_url=settings.llm_endpoint_url,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            prompt_version=settings.llm_prompt_version,
            preset_name=None,
        )

    preset = get_model_preset(preset_name)
    provider = settings.llm_provider if settings.llm_provider not in {"stub"} else "local"
    return ResolvedLlmConfig(
        provider=provider,
        model_id=settings.llm_model_id if settings.llm_model_id not in {"stub-clinical-v1"} else preset.model_id,
        endpoint_url=settings.llm_endpoint_url or preset.endpoint_url,
        api_key=settings.llm_api_key,
        timeout_seconds=preset.timeout_seconds,
        temperature=preset.temperature,
        prompt_version=preset.prompt_version,
        preset_name=preset.name,
    )
