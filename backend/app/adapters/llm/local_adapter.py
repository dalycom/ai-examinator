"""Self-hosted LLM adapter using OpenAI-compatible chat completions (Ollama, vLLM, etc.)."""

import json
import logging
from typing import Any

import httpx

from app.adapters.llm.port import LlmExtractionResult, LlmPort, TranscriptInput
from app.adapters.llm.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_user_prompt
from app.adapters.llm.response_parser import LlmResponseParseError, parse_extraction_response
from app.adapters.llm.settings_resolver import resolve_llm_config
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LocalLlmAdapter(LlmPort):
    """Calls a self-hosted OpenAI-compatible endpoint for clinical extraction."""

    def extract_clinical_information(
        self,
        *,
        transcript: list[TranscriptInput],
        locale: str = "en",
    ) -> LlmExtractionResult:
        settings = get_settings()
        llm = resolve_llm_config(settings)
        if not llm.endpoint_url:
            logger.warning("LLM_ENDPOINT_URL not configured — falling back to stub adapter")
            result = StubLlmAdapter().extract_clinical_information(transcript=transcript, locale=locale)
            return result

        transcript_payload = [
            {
                "segment_id": str(segment.segment_id),
                "speaker": segment.speaker,
                "text": segment.text,
            }
            for segment in transcript
        ]
        user_prompt = build_extraction_user_prompt(
            transcript_json=json.dumps(transcript_payload, ensure_ascii=False, indent=2),
            locale=locale,
        )
        request_body: dict[str, Any] = {
            "model": llm.model_id,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": llm.temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {"Content-Type": "application/json"}
        if llm.api_key:
            headers["Authorization"] = f"Bearer {llm.api_key}"

        endpoint = llm.endpoint_url.rstrip("/")
        if endpoint.endswith("/chat/completions"):
            url = endpoint
        elif endpoint.endswith("/v1"):
            url = f"{endpoint}/chat/completions"
        else:
            url = f"{endpoint}/v1/chat/completions"

        try:
            with httpx.Client(timeout=llm.timeout_seconds) as client:
                response = client.post(url, headers=headers, json=request_body)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            msg = f"Self-hosted LLM request failed: {exc}"
            raise RuntimeError(msg) from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            msg = "Self-hosted LLM returned an unexpected response shape"
            raise RuntimeError(msg) from exc

        parameters = {
            "locale": locale,
            "temperature": llm.temperature,
            "endpoint": url,
            "transcript_segments": len(transcript),
            "preset": llm.preset_name,
        }
        try:
            return parse_extraction_response(
                content,
                transcript=transcript,
                model_id=llm.model_id,
                provider="self_hosted",
                prompt_version=llm.prompt_version,
                parameters=parameters,
            )
        except LlmResponseParseError as exc:
            msg = f"Self-hosted LLM response failed validation: {exc}"
            raise RuntimeError(msg) from exc
