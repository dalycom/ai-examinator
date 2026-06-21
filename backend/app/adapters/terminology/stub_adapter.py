"""Stub terminology adapter using public sample codes (no licensed datasets)."""

from app.adapters.terminology.port import TerminologyPort

ICD10_STUB = [
    {"code": "R51", "label": "Headache"},
    {"code": "R05", "label": "Cough"},
    {"code": "J06.9", "label": "Acute upper respiratory infection, unspecified"},
    {"code": "I10", "label": "Essential (primary) hypertension"},
    {"code": "E11.9", "label": "Type 2 diabetes mellitus without complications"},
]

RXNORM_STUB = [
    {"code": "161", "label": "Acetaminophen"},
    {"code": "5640", "label": "Ibuprofen"},
    {"code": "6809", "label": "Metformin"},
    {"code": "29046", "label": "Lisinopril"},
    {"code": "83367", "label": "Atorvastatin"},
]


class StubTerminologyAdapter:
    def lookup_icd10(self, query: str, *, limit: int = 10) -> list[dict[str, str]]:
        needle = query.lower()
        matches = [item for item in ICD10_STUB if needle in item["label"].lower() or needle in item["code"].lower()]
        return matches[:limit]

    def lookup_rxnorm(self, query: str, *, limit: int = 10) -> list[dict[str, str]]:
        needle = query.lower()
        matches = [item for item in RXNORM_STUB if needle in item["label"].lower() or needle in item["code"]]
        return matches[:limit]


def get_terminology_adapter() -> TerminologyPort:
    return StubTerminologyAdapter()
