import logging

from src import pdf_audit


def test_active_pdf_audit_passes_generated_answer_to_judge(monkeypatch):
    captured = {}
    context = pdf_audit.replace_active_pdf("policy.pdf", "Reference text", 1)

    def fake_generate(user_prompt):
        captured["prompt"] = user_prompt
        return "Generated answer"

    def fake_audit(answer, reference_text):
        captured["answer"] = answer
        captured["reference_text"] = reference_text
        return pdf_audit.PdfAuditResult(0.92, "pass", "Answer is supported.")

    monkeypatch.setattr(pdf_audit, "generate_unconstrained_response", fake_generate)
    monkeypatch.setattr(pdf_audit, "audit_against_pdf", fake_audit)

    result = pdf_audit.audit_active_pdf_prompt("What is the policy?")

    assert captured == {
        "prompt": "What is the policy?",
        "answer": "Generated answer",
        "reference_text": context.text,
    }
    assert result["unconstrained_response"] == "Generated answer"
    assert result["score"] == 0.92


def test_unconstrained_generation_never_returns_empty_string(monkeypatch, caplog):
    class EmptyMessage:
        content = ""

    class EmptyChoice:
        message = EmptyMessage()

    class EmptyResponse:
        choices = [EmptyChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            return EmptyResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(pdf_audit, "get_groq_client", lambda: FakeClient())

    with caplog.at_level(logging.WARNING, logger="src.pdf_audit"):
        assert pdf_audit.generate_unconstrained_response("prompt")

    assert "Groq unconstrained generation returned empty content" in caplog.text


def test_unconstrained_generation_logs_groq_errors(monkeypatch, caplog):
    class BrokenCompletions:
        def create(self, **kwargs):
            raise RuntimeError("Groq exploded")

    class BrokenChat:
        completions = BrokenCompletions()

    class BrokenClient:
        chat = BrokenChat()

    monkeypatch.setattr(pdf_audit, "get_groq_client", lambda: BrokenClient())

    with caplog.at_level(logging.ERROR, logger="src.pdf_audit"):
        result = pdf_audit.generate_unconstrained_response("prompt")

    assert result == "Unable to generate an unconstrained response: Groq exploded"
    assert "Groq unconstrained generation failed" in caplog.text
