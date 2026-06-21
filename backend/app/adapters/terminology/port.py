from typing import Protocol


class TerminologyPort(Protocol):
    def lookup_icd10(self, query: str, *, limit: int = 10) -> list[dict[str, str]]: ...

    def lookup_rxnorm(self, query: str, *, limit: int = 10) -> list[dict[str, str]]: ...
