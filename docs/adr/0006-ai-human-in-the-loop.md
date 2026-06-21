# ADR-0006: AI human-in-the-loop & immutable signed records

- **Status:** Accepted
- **Date:** 2026-06-20

## Context

AI Examinator is decision *support*, not a decision maker. Patient safety and compliance require that no AI output
ever becomes a medical fact without explicit clinician approval, and that signed records are tamper-evident.

## Decision

- **No auto-apply path exists.** AI outputs are persisted as suggestions with `status=pending` and full provenance.
- **Human-in-the-loop is mandatory:** a clinician must `approve | edit | reject` each suggestion (`ai:review`,
  doctor-only); every decision is audited with actor, timestamp, before/after, and reason.
- **Only approved (or doctor-edited-then-approved) content** may be incorporated into a clinical note.
- **Signing is separate, deliberate, and doctor-only** (`note:sign`). On signing, the note becomes **immutable**
  and is sealed with a `content_hash`; corrections are linked **addenda**, never edits.
- **Structural prohibitions:** no auto-sign, no auto-prescribe; all AI output is labeled `is_ai_generated`;
  uncertainty/red-flags are always shown; outputs are schema-validated and grounding-checked before display.

## Consequences

**Positive:** safety and legal defensibility by construction; clear provenance and accountability.
**Negative:** more clicks for clinicians; must design UX to make review fast and non-fatiguing.
**Follow-ups:** UX optimization for bulk review; evaluation of red-flag sensitivity; addendum workflow design.

## Alternatives considered

- Auto-accept high-confidence AI output (rejected: violates safety brief; risk of automation bias).
- Editable signed notes (rejected: breaks tamper-evidence; addenda chosen instead).
