from enum import StrEnum


class ProductType(StrEnum):
    CORPORATE_OVERDRAFT = "CORPORATE_OVERDRAFT"
    WORKING_CAPITAL = "WORKING_CAPITAL"


class EngineKind(StrEnum):
    DETERMINISTIC = "DETERMINISTIC"
    LOCAL_LLM = "LOCAL_LLM"
    CLOUD_LLM = "CLOUD_LLM"


class QualityStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DEMO_ONLY = "DEMO_ONLY"
    REJECTED = "REJECTED"


class CriticVerdict(StrEnum):
    PASS = "PASS"
    REVISE = "REVISE"
    ESCALATE = "ESCALATE"
