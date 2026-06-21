from app.adapters.llm.model_presets import get_model_preset, list_model_presets
from app.adapters.llm.settings_resolver import resolve_llm_config
from app.core.config import Settings


def test_clinical_model_presets_include_meditron_and_biomistral() -> None:
    presets = {preset.name for preset in list_model_presets()}
    assert "meditron-7b" in presets
    assert "biomistral-7b" in presets


def test_meditron_preset_resolves_model_id() -> None:
    preset = get_model_preset("meditron-7b")
    assert preset.model_id == "meditron:7b"
    assert preset.prompt_version == "extraction-v2-meditron"


def test_biomistral_preset_resolves_model_id() -> None:
    preset = get_model_preset("biomistral-7b")
    assert preset.model_id == "biomistral:7b"
    assert "BioMistral" in preset.huggingface_repo


def test_preset_overrides_stub_defaults() -> None:
    settings = Settings(
        secret_key="test-secret-key-at-least-32-characters-long",
        database_url="postgresql+psycopg://user:pass@localhost/db",
        llm_provider="stub",
        llm_model_id="stub-clinical-v1",
        llm_model_preset="meditron-7b",
    )
    resolved = resolve_llm_config(settings)
    assert resolved.preset_name == "meditron-7b"
    assert resolved.model_id == "meditron:7b"
    assert resolved.provider == "local"
    assert resolved.prompt_version == "extraction-v2-meditron"
