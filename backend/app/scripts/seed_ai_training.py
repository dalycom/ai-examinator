"""Seed AI training artifacts: eval dataset, prompt versions, feature flags."""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.ai.eval_persistence import ensure_eval_dataset
from app.modules.ai.models import PromptVersion


PROMPT_VERSIONS: tuple[tuple[str, str, str], ...] = (
    ("clinical_extraction", "stub-extraction-v2", "prompts/stub-extraction-v2.txt"),
    ("clinical_extraction", "extraction-v2-meditron", "prompts/extraction-v2-meditron.txt"),
    ("clinical_extraction", "extraction-v2-biomistral", "prompts/extraction-v2-biomistral.txt"),
)


def seed_prompt_versions(db: Session) -> None:
    for key, version, template_ref in PROMPT_VERSIONS:
        existing = (
            db.query(PromptVersion)
            .filter(PromptVersion.key == key, PromptVersion.version == version)
            .one_or_none()
        )
        if existing is not None:
            continue
        db.add(
            PromptVersion(
                key=key,
                version=version,
                template_ref=template_ref,
                is_active=version == "stub-extraction-v2",
            )
        )
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        dataset = ensure_eval_dataset(db)
        db.commit()
        seed_prompt_versions(db)
        print(
            f"AI training seed completed: dataset={dataset.name} "
            f"({len(dataset.items)} cases), prompt_versions={len(PROMPT_VERSIONS)}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
