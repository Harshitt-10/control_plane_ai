from enum import Enum

from pydantic import BaseModel, Field, confloat


class TierStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    not_applicable = "not_applicable"


class DecisionAction(str, Enum):
    allow = "allow"
    flag = "flag"
    block = "block"


class EvalRequest(BaseModel):
    user_prompt: str = Field(..., description="The original user prompt")
    ai_response: str = Field(..., description="The AI-generated response being evaluated")
    use_case: str = Field(..., description="The intended use case or policy profile")


class TierResult(BaseModel):
    status: TierStatus = Field(..., description="Outcome of the tier evaluation")
    score: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence or severity score from 0 to 1")
    reason: str = Field(..., description="Human-readable explanation for the tier result")


class FinalDecision(BaseModel):
    action: DecisionAction = Field(..., description="Final gateway action")
    final_confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Overall confidence in the final decision"
    )


class ScoringResult(BaseModel):
    """Structured output from the confidence scoring engine."""
    final_confidence: confloat(ge=0.0, le=1.0) = Field(
        ..., description="Combined confidence score after capping for coverage gaps"
    )
    coverage_complete: bool = Field(
        ..., description="True if all tiers returned a pass/fail verdict (no not_applicable)"
    )
    explanation: str = Field(
        ..., description="Human-readable summary of how the score was derived"
    )
