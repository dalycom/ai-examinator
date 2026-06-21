# ADR-0005: Localization & RTL strategy (EN/AR/FR)

- **Status:** Accepted
- **Date:** 2026-06-20

## Context

The platform must fully support English, Arabic (with RTL), and French across UI, documentation, transcription,
summaries, notifications, and reports. Arabic RTL is a first-class requirement, not an afterthought.

## Decision

- **Frontend:** Next.js App Router with a `[locale]` route segment; **next-intl** for message catalogs
  (`messages/{en,ar,fr}.json`). Direction (`dir=rtl|ltr`) derived from locale at the layout root.
- **Styling:** Tailwind with **logical CSS properties** (e.g. `ms-*`/`me-*`, `start/end`) so layouts mirror
  automatically; components from shadcn/ui adapted for RTL.
- **Backend:** locale negotiation via `Accept-Language`; localized error messages and report rendering; all
  user-facing strings are keys, never hardcoded.
- **Data:** locale-aware formatting for dates/numbers; store canonical data, format at the edge.
- **Reports:** generated per-locale with correct RTL layout for Arabic.
- **Testing:** missing-translation detection in CI; E2E run includes Arabic/RTL; a11y checks per locale.

## Consequences

**Positive:** true tri-lingual parity; maintainable message catalogs; correct RTL by construction.
**Negative:** discipline required to avoid hardcoded strings and physical CSS; translation upkeep.
**Follow-ups:** translation workflow/ownership; medical-terminology localization quality is part of AI evaluation.

## Alternatives considered

- Single-language now, i18n later (rejected: RTL retrofits are costly and error-prone).
- Physical CSS with per-direction overrides (rejected: brittle vs logical properties).
