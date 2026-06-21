# ADR-0003: Provider-agnostic AI (both self-hosted & cloud, default self-hosted)

- **Status:** Accepted
- **Date:** 2026-06-20
- **Decision input:** Stakeholder selected "build both paths, config-switchable, default to self-hosted".

## Context

PHI (audio, transcripts) is highly sensitive and likely subject to UAE PDPL data-residency and processor
constraints. We must avoid coupling to a single AI vendor, while allowing cloud providers where a BAA/DPA permits.

## Decision

Define **ports** for `SpeechToTextPort`, `DiarizationPort`, `LanguageDetectionPort`, `TranslationPort`,
`MedicalNlpPort`, `LlmPort`, `ObjectStoragePort`, and `TerminologyPort`. Ship **both** self-hosted and cloud
adapters, selected via configuration + feature flags. **Default to self-hosted** so PHI stays in-boundary.
Cloud/external PHI processing is disabled unless `AI_ALLOW_EXTERNAL_PHI=true` **and** a recorded BAA/DPA exists.

## Consequences

**Positive:** vendor independence; privacy-by-default; easy A/B and fallback; testable via fakes.
**Negative:** more adapters to maintain; self-hosted models require runtime/ops (GPU) for good quality.
**Follow-ups:** select default self-hosted models (e.g. Whisper for STT; a configurable local LLM endpoint);
benchmark Gulf-Arabic STT; document provider matrix; gate cloud paths in governance.

## Alternatives considered

- Single cloud provider (rejected: lock-in + PHI residency risk).
- Self-hosted only (rejected: stakeholder wants optional cloud; some capabilities/quality may need it later).
