import re
from typing import Any, Optional

from src.models.schemas import TierResult, TierStatus

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"
)


def check(text: str, context: Optional[dict[str, Any]] = None) -> TierResult:
    matches = []
    if EMAIL_RE.search(text):
        matches.append("email address")
    if PHONE_RE.search(text):
        matches.append("phone number")

    if matches:
        return TierResult(
            status=TierStatus.fail,
            score=0.95,
            reason=f"Potential PII detected: {', '.join(matches)}.",
        )

    return TierResult(
        status=TierStatus.pass_,
        score=0.95,
        reason="No obvious email addresses or phone numbers detected.",
    )
