from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from orchestrator import evaluate_request
from src.models.schemas import EvalRequest

app = FastAPI(title="ControlPlane")


def _dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@app.post("/api/evaluate")
async def api_evaluate(request: EvalRequest) -> dict[str, Any]:
    result = await evaluate_request(request)
    return {
        "decision": result["decision"],
        "overall_confidence": result["overall_confidence"],
        "tier_results": result["tier_results"],
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>ControlPlane Dashboard</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
        .wrap { max-width: 1100px; margin: 0 auto; padding: 32px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 20px; }
        textarea, input { width: 100%; box-sizing: border-box; margin-top: 8px; margin-bottom: 16px; padding: 12px; border-radius: 10px; border: 1px solid #475569; background: #0b1220; color: #e2e8f0; }
        button { background: #22c55e; color: #052e16; font-weight: 700; border: 0; padding: 12px 18px; border-radius: 10px; cursor: pointer; }
        pre { white-space: pre-wrap; word-break: break-word; background: #0b1220; padding: 16px; border-radius: 12px; border: 1px solid #334155; }
        .pill { display: inline-block; padding: 6px 10px; border-radius: 999px; background: #1e293b; margin-right: 8px; }
        h1, h2 { margin-top: 0; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
      </style>
    </head>
    <body>
      <div class="wrap">
        <h1>ControlPlane Dashboard</h1>
        <p>Submit an AI response for tier checks, scoring, and policy decisioning.</p>
        <div class="grid">
          <div class="card">
            <h2>Evaluate</h2>
            <form id="evalForm">
              <label>User Prompt</label>
              <textarea id="user_prompt" rows="4" placeholder="Enter the original prompt"></textarea>
              <label>AI Response</label>
              <textarea id="ai_response" rows="6" placeholder="Enter the AI response"></textarea>
              <label>Use Case</label>
              <input id="use_case" type="text" placeholder="customer_support_chatbot" />
              <button type="submit">Run Check</button>
            </form>
          </div>
          <div class="card">
            <h2>Results</h2>
            <div id="summary">
              <span class="pill">Action: -</span>
              <span class="pill">Confidence: -</span>
            </div>
            <h3>Tier Results</h3>
            <pre id="tierResults">No results yet.</pre>
          </div>
        </div>
      </div>
      <script>
        const form = document.getElementById("evalForm");
        const summary = document.getElementById("summary");
        const tierResults = document.getElementById("tierResults");

        form.addEventListener("submit", async (event) => {
          event.preventDefault();
          const payload = {
            user_prompt: document.getElementById("user_prompt").value,
            ai_response: document.getElementById("ai_response").value,
            use_case: document.getElementById("use_case").value,
          };

          const response = await fetch("/api/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });

          const data = await response.json();
          summary.innerHTML = `
            <span class="pill">Action: ${data.decision.action}</span>
            <span class="pill">Confidence: ${data.overall_confidence}</span>
          `;
          tierResults.textContent = JSON.stringify(data.tier_results, null, 2);
        });
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
