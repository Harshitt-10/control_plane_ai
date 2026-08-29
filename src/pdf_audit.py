"""Persistent PDF context and reference-based hallucination auditing."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from threading import RLock

from src.engine.groq_client import get_groq_client


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ActivePdfContext:
    """The single active document for this backend process."""

    filename: str
    text: str
    page_count: int


@dataclass(frozen=True)
class PdfAuditResult:
    accuracy_score: float
    status: str
    reasoning_breakdown: str


_context_lock = RLock()
_active_pdf: ActivePdfContext | None = None


def replace_active_pdf(filename: str, text: str, page_count: int) -> ActivePdfContext:
    """Atomically replace the active PDF context for all later requests."""
    global _active_pdf
    context = ActivePdfContext(filename=filename, text=text, page_count=page_count)
    with _context_lock:
        _active_pdf = context
    return context


def get_active_pdf() -> ActivePdfContext | None:
    """Return a snapshot of the current active PDF context, if one exists."""
    with _context_lock:
        return _active_pdf


def generate_unconstrained_response(user_prompt: str) -> str:
    """Generate without injecting the active PDF or any retrieved document facts."""
    client = get_groq_client()
    if client is None:
        return "No LLM provider is configured, so I cannot generate a response."

    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly organized, professional AI assistant. "
                        "You must always structure your answers clearly using Markdown. "
                        "Use bullet points for lists, bold text for key terms, and keep "
                        "paragraphs short, concise, and highly readable. Never output a "
                        "long, unorganized wall of text."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        ai_answer = (completion.choices[0].message.content or "").strip()
        if ai_answer:
            return ai_answer
        logger.warning("Groq unconstrained generation returned empty content for prompt: %r", user_prompt)
        return "The unconstrained LLM generation completed but returned an empty response."
    except Exception as exc:
        logger.exception("Groq unconstrained generation failed for prompt: %r", user_prompt)
        return f"Unable to generate an unconstrained response: {exc}"


def generate_rag_response(user_prompt: str, pdf_text: str) -> str:
    """Generate a response strictly grounded in the supplied PDF text (RAG path)."""
    client = get_groq_client()
    if client is None:
        return "No LLM provider is configured; cannot generate a document-backed answer."

    # Truncate PDF text to stay comfortably within token budget
    truncated_pdf = pdf_text[:12000] if len(pdf_text) > 12000 else pdf_text

    try:
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_CHAT_MODEL", "llama3-8b-8192"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise document-grounded assistant. "
                        "Answer the user's question using ONLY the information in the provided document. "
                        "If the document does not contain enough information to answer, say so explicitly. "
                        "Structure your answer clearly using Markdown. Do not invent or assume any facts "
                        "not present in the document."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"DOCUMENT:\n{truncated_pdf}\n\n"
                        f"QUESTION:\n{user_prompt}"
                    ),
                },
            ],
            temperature=0.1,
        )
        answer = (completion.choices[0].message.content or "").strip()
        return answer if answer else "The document-grounded generation returned an empty response."
    except Exception as exc:
        logger.exception("Groq RAG generation failed for prompt: %r", user_prompt)
        return f"Unable to generate a document-backed answer: {exc}"


def _parse_judge_output(raw: str) -> PdfAuditResult | None:

    """Parse a judge JSON response, allowing Markdown code fences from tolerant models."""
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.S)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    try:
        score = max(0.0, min(1.0, float(payload["accuracy_score"])))
        status = str(payload["status"]).lower()
        if status not in {"pass", "fail"}:
            status = "pass" if score >= 0.7 else "fail"
        reasoning = str(payload["reasoning_breakdown"]).strip()
        return PdfAuditResult(score, status, reasoning)
    except (KeyError, TypeError, ValueError):
        return None


def audit_against_pdf(answer: str, reference_text: str) -> PdfAuditResult:
    """Use a second LLM call to grade an answer solely against a PDF reference."""
    client = get_groq_client()
    if client is None:
        return PdfAuditResult(
            accuracy_score=0.0,
            status="fail",
            reasoning_breakdown="No LLM provider is configured; the PDF-based audit could not run.",
        )

    prompt = f"""Compare the ANSWER with the PDF REFERENCE. Focus on whether the answer
correctly includes the primary fact found in the reference text. If it does, mark it pass
with a high score. Do not penalize the answer for adding helpful, accurate real-world context
or elaborations, such as abbreviations or governing bodies, as long as those additions do not
directly contradict the reference text. Mark the answer fail when it misses the primary fact,
materially contradicts the reference, or adds unsupported claims that change the meaning.
A response that appropriately says the reference does not provide enough information may pass.
Return JSON only, using this exact shape:
{{"accuracy_score": 0.0, "status": "pass" | "fail", "reasoning_breakdown": "brief explanation"}}

ANSWER:
{answer}

PDF REFERENCE:
{reference_text}"""
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_JUDGE_MODEL", os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-20b")),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are evaluating an AI's answer against a Reference Text. "
                        "If the AI's answer correctly contains the primary fact found in the "
                        "Reference Text, mark it as pass with a high score. Do not penalize "
                        "the AI for adding helpful, accurate real-world context or elaborations "
                        "(such as abbreviations or governing bodies) as long as those additions "
                        "do not directly contradict the Reference Text. Return valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = _parse_judge_output(raw)
        if parsed is not None:
            return parsed
        return PdfAuditResult(0.0, "fail", f"Judge returned an invalid audit result: {raw[:500]}")
    except Exception as exc:
        return PdfAuditResult(0.0, "fail", f"PDF-based judge evaluation failed: {exc}")


def audit_active_pdf_prompt(user_prompt: str) -> dict[str, object]:
    """Run the required generation-then-audit sequence against the active PDF."""
    context = get_active_pdf()
    if context is None:
        raise RuntimeError("No active PDF context")

    # Generate unconstrained answer (no document context injected)
    ai_answer = generate_unconstrained_response(user_prompt)
    # Generate RAG answer (strictly grounded in the PDF)
    rag_answer = generate_rag_response(user_prompt, context.text)
    # Grade the unconstrained answer against the PDF
    audit = audit_against_pdf(ai_answer, context.text)
    return {
        "unconstrained_response": ai_answer,
        "rag_answer": rag_answer,
        "score": audit.accuracy_score,
        "accuracy_score": audit.accuracy_score,
        "status": audit.status,
        "reasoning_breakdown": audit.reasoning_breakdown,
        "active_pdf": {"filename": context.filename, "page_count": context.page_count},
    }
