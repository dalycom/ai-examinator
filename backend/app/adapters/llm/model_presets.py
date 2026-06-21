"""Pre-configured clinical LLM profiles for self-hosted inference."""

from dataclasses import dataclass
from typing import Literal

ModelPresetName = Literal["meditron-7b", "meditron-70b", "biomistral-7b", "biomistral-7b-vllm"]


@dataclass(frozen=True)
class ClinicalModelPreset:
    name: ModelPresetName
    model_id: str
    endpoint_url: str
    prompt_version: str
    temperature: float
    timeout_seconds: int
    description: str
    ollama_pull_command: str | None
    huggingface_repo: str


MODEL_PRESETS: dict[ModelPresetName, ClinicalModelPreset] = {
    "meditron-7b": ClinicalModelPreset(
        name="meditron-7b",
        model_id="meditron:7b",
        endpoint_url="http://host.docker.internal:11434",
        prompt_version="extraction-v2-meditron",
        temperature=0.05,
        timeout_seconds=180,
        description="EPFL Meditron 7B — clinical instruction-tuned LLM (recommended starter model).",
        ollama_pull_command="ollama pull meditron:7b",
        huggingface_repo="epfl-llm/meditron-7b-gpt",
    ),
    "meditron-70b": ClinicalModelPreset(
        name="meditron-70b",
        model_id="meditron:70b",
        endpoint_url="http://host.docker.internal:11434",
        prompt_version="extraction-v2-meditron",
        temperature=0.05,
        timeout_seconds=300,
        description="EPFL Meditron 70B — higher quality, requires substantial GPU VRAM.",
        ollama_pull_command="ollama pull meditron:70b",
        huggingface_repo="epfl-llm/meditron-70b-gpt",
    ),
    "biomistral-7b": ClinicalModelPreset(
        name="biomistral-7b",
        model_id="biomistral:7b",
        endpoint_url="http://host.docker.internal:11434",
        prompt_version="extraction-v2-biomistral",
        temperature=0.1,
        timeout_seconds=180,
        description="BioMistral 7B — biomedical domain LLM via Ollama OpenAI-compatible API.",
        ollama_pull_command="ollama pull biomistral:7b",
        huggingface_repo="BioMistral/BioMistral-7B",
    ),
    "biomistral-7b-vllm": ClinicalModelPreset(
        name="biomistral-7b-vllm",
        model_id="BioMistral/BioMistral-7B",
        endpoint_url="http://host.docker.internal:8001/v1",
        prompt_version="extraction-v2-biomistral",
        temperature=0.1,
        timeout_seconds=120,
        description="BioMistral 7B served via vLLM OpenAI-compatible endpoint.",
        ollama_pull_command=None,
        huggingface_repo="BioMistral/BioMistral-7B",
    ),
}


def get_model_preset(name: str) -> ClinicalModelPreset:
    if name not in MODEL_PRESETS:
        supported = ", ".join(sorted(MODEL_PRESETS))
        msg = f"Unknown LLM_MODEL_PRESET {name!r}. Supported: {supported}"
        raise ValueError(msg)
    return MODEL_PRESETS[name]  # type: ignore[index]


def list_model_presets() -> list[ClinicalModelPreset]:
    return list(MODEL_PRESETS.values())
