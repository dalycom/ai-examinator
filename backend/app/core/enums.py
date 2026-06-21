from enum import StrEnum


class AppEnv(StrEnum):
    LOCAL = "local"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


class Locale(StrEnum):
    EN = "en"
    AR = "ar"
    FR = "fr"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    PHI = "phi"
    SENSITIVE_PHI = "sensitive_phi"
