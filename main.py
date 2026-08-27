from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from orchestrator import evaluate_request
from src.models.schemas import EvalRequest
from src.chat_pipeline import chat_pipeline

app = FastAPI(title="ControlPlane")


def _dump_model(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user message to answer")
    use_case: str = Field(default="default", description="Policy profile for governance")
    policy_path: str = Field(default="config.yaml", description="Path to the policy config")
    retrieval_limit: int = Field(default=5, ge=1, le=10, description="Maximum facts to retrieve")
    context: Optional[dict[str, Any]] = Field(
        default=None, description="Optional extra runtime context"
    )


@app.post("/api/evaluate")
async def api_evaluate(request: EvalRequest) -> dict[str, Any]:
    result = await evaluate_request(request)
    return {
        "decision": result["decision"],
        "overall_confidence": result["overall_confidence"],
        "tier_results": result["tier_results"],
    }


@app.post("/api/chat")
async def api_chat(request: ChatRequest) -> dict[str, Any]:
    runtime_context = dict(request.context or {})
    runtime_context.update(
        {
            "use_case": request.use_case,
            "policy_path": request.policy_path,
            "retrieval_limit": request.retrieval_limit,
        }
    )

    result = chat_pipeline(request.message, runtime_context)
    decision = result["decision"]
    scoring_result = result["scoring"]
    tier_results = result["tier_results"]

    return {
        "reply": result["draft_response"],
        "evaluation": {
            "retrieved_facts": result["retrieved_facts"],
            "tier_results": _dump_model(tier_results) if hasattr(tier_results, "model_dump") else {
                key: _dump_model(value) if hasattr(value, "model_dump") else value
                for key, value in tier_results.items()
            },
            "scoring": _dump_model(scoring_result) if hasattr(scoring_result, "model_dump") else scoring_result,
            "decision": _dump_model(decision) if hasattr(decision, "model_dump") else decision,
        },
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
        :root {
          --bg: #08111f;
          --panel: rgba(15, 23, 42, 0.92);
          --panel-border: rgba(148, 163, 184, 0.18);
          --text: #e2e8f0;
          --muted: #94a3b8;
          --accent: #38bdf8;
          --accent-2: #22c55e;
          --danger: #f97316;
          --shadow: 0 24px 80px rgba(2, 6, 23, 0.35);
        }
        * { box-sizing: border-box; }
        body {
          font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          margin: 0;
          color: var(--text);
          background:
            radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 35%),
            radial-gradient(circle at top right, rgba(34, 197, 94, 0.14), transparent 30%),
            linear-gradient(180deg, #050b16 0%, var(--bg) 100%);
          min-height: 100vh;
        }
        .wrap { max-width: 1220px; margin: 0 auto; padding: 32px 24px 48px; }
        .hero {
          display: flex;
          justify-content: space-between;
          gap: 20px;
          align-items: end;
          margin-bottom: 22px;
        }
        .eyebrow { text-transform: uppercase; letter-spacing: 0.14em; color: var(--accent); font-size: 12px; margin-bottom: 10px; }
        .subtitle { color: var(--muted); margin: 10px 0 0; max-width: 72ch; }
        .tabs {
          display: inline-flex;
          gap: 8px;
          background: rgba(15, 23, 42, 0.62);
          border: 1px solid var(--panel-border);
          border-radius: 999px;
          padding: 6px;
          box-shadow: var(--shadow);
          margin: 22px 0;
        }
        .tab-btn {
          appearance: none;
          border: 0;
          border-radius: 999px;
          background: transparent;
          color: var(--muted);
          padding: 10px 16px;
          cursor: pointer;
          font-weight: 700;
        }
        .tab-btn.active { background: rgba(56, 189, 248, 0.16); color: #e0f2fe; }
        .panel {
          display: none;
          background: var(--panel);
          border: 1px solid var(--panel-border);
          border-radius: 22px;
          padding: 22px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(18px);
        }
        .panel.active { display: block; }
        .grid { display: grid; grid-template-columns: 1.02fr 0.98fr; gap: 20px; }
        .card {
          background: rgba(2, 6, 23, 0.34);
          border: 1px solid rgba(148, 163, 184, 0.12);
          border-radius: 18px;
          padding: 18px;
        }
        textarea, input {
          width: 100%;
          box-sizing: border-box;
          margin-top: 8px;
          margin-bottom: 16px;
          padding: 12px 14px;
          border-radius: 12px;
          border: 1px solid rgba(148, 163, 184, 0.2);
          background: rgba(2, 6, 23, 0.72);
          color: var(--text);
          outline: none;
        }
        textarea:focus, input:focus { border-color: rgba(56, 189, 248, 0.7); box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15); }
        button {
          background: linear-gradient(135deg, #38bdf8, #22c55e);
          color: #04111f;
          font-weight: 800;
          border: 0;
          padding: 12px 18px;
          border-radius: 12px;
          cursor: pointer;
        }
        button.secondary {
          background: rgba(148, 163, 184, 0.15);
          color: var(--text);
          border: 1px solid rgba(148, 163, 184, 0.18);
        }
        pre {
          white-space: pre-wrap;
          word-break: break-word;
          background: rgba(2, 6, 23, 0.76);
          padding: 16px;
          border-radius: 14px;
          border: 1px solid rgba(148, 163, 184, 0.16);
          overflow: auto;
        }
        .pill {
          display: inline-block;
          padding: 7px 11px;
          border-radius: 999px;
          background: rgba(30, 41, 59, 0.92);
          border: 1px solid rgba(148, 163, 184, 0.14);
          margin-right: 8px;
          margin-bottom: 8px;
        }
        .chat-shell {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 320px;
          gap: 18px;
          align-items: start;
        }
        .chat-window {
          min-height: 540px;
          max-height: 68vh;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 16px;
          background: rgba(2, 6, 23, 0.38);
          border-radius: 18px;
          border: 1px solid rgba(148, 163, 184, 0.12);
        }
        .message {
          max-width: 88%;
          padding: 12px 14px;
          border-radius: 16px;
          line-height: 1.5;
          position: relative;
          white-space: pre-wrap;
        }
        .message.user {
          margin-left: auto;
          background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(34, 197, 94, 0.18));
          border: 1px solid rgba(56, 189, 248, 0.2);
        }
        .message.ai {
          background: rgba(15, 23, 42, 0.9);
          border: 1px solid rgba(148, 163, 184, 0.14);
        }
        .message .meta {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          color: var(--muted);
          font-size: 12px;
          margin-bottom: 8px;
        }
        .chat-input {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          margin-top: 14px;
        }
        .sidebar {
          position: sticky;
          top: 16px;
        }
        details {
          background: rgba(2, 6, 23, 0.42);
          border: 1px solid rgba(148, 163, 184, 0.14);
          border-radius: 16px;
          padding: 12px 14px;
          margin-top: 10px;
        }
        summary { cursor: pointer; color: #dbeafe; font-weight: 700; }
        .badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px 10px;
          border-radius: 999px;
          font-weight: 800;
          font-size: 12px;
        }
        .badge.allow { background: rgba(34, 197, 94, 0.14); color: #86efac; border: 1px solid rgba(34, 197, 94, 0.22); }
        .badge.block { background: rgba(249, 115, 22, 0.14); color: #fdba74; border: 1px solid rgba(249, 115, 22, 0.22); }
        .badge.flag { background: rgba(234, 179, 8, 0.14); color: #fde68a; border: 1px solid rgba(234, 179, 8, 0.22); }
        .tier-item { padding: 10px 12px; border-radius: 12px; background: rgba(15, 23, 42, 0.74); margin-top: 10px; }
        .tier-item strong { display: block; margin-bottom: 4px; }
        .empty-state { color: var(--muted); padding: 16px; border: 1px dashed rgba(148, 163, 184, 0.24); border-radius: 14px; }
        .loading { opacity: 0.72; font-style: italic; }
        @media (max-width: 1024px) {
          .grid, .chat-shell { grid-template-columns: 1fr; }
          .sidebar { position: static; }
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <div>
            <div class="eyebrow">ControlPlane.ai</div>
            <h1>Evaluation Dashboard</h1>
            <p class="subtitle">Use the classic evaluator or switch to Live Chat to ground answers against internal knowledge and see the governance payload for each turn.</p>
          </div>
        </div>
        <div class="tabs">
          <button class="tab-btn active" data-tab="evaluatePanel">Evaluate</button>
          <button class="tab-btn" data-tab="chatPanel">Live Chat</button>
        </div>

        <section id="evaluatePanel" class="panel active">
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
        </section>

        <section id="chatPanel" class="panel">
          <div class="chat-shell">
            <div class="card">
              <h2>Live Chat</h2>
              <div id="chatWindow" class="chat-window">
                <div class="empty-state">Messages will appear here. Ask a question to start a grounded chat.</div>
              </div>
              <div class="chat-input">
                <textarea id="chatInput" rows="3" placeholder="Ask about remote work stipends, IT security rules, or the Mess Management System..."></textarea>
                <button id="sendChatBtn" type="button">Send</button>
              </div>
            </div>
            <div class="card sidebar">
              <h2>ControlPlane Badge</h2>
              <div id="chatBadge" class="badge flag">Waiting</div>
              <p class="subtitle" style="margin-top: 12px;">The latest message evaluation appears here with confidence, decision, and tier breakdown.</p>
              <details open>
                <summary>Latest evaluation</summary>
                <div id="chatEvaluation" style="margin-top: 12px;">
                  <div class="empty-state">No chat evaluated yet.</div>
                </div>
              </details>
            </div>
          </div>
        </section>
      </div>
      <script>
        const form = document.getElementById("evalForm");
        const summary = document.getElementById("summary");
        const tierResults = document.getElementById("tierResults");
        const tabButtons = document.querySelectorAll(".tab-btn");
        const panels = document.querySelectorAll(".panel");
        const chatWindow = document.getElementById("chatWindow");
        const chatInput = document.getElementById("chatInput");
        const sendChatBtn = document.getElementById("sendChatBtn");
        const chatBadge = document.getElementById("chatBadge");
        const chatEvaluation = document.getElementById("chatEvaluation");

        function setActiveTab(tabId) {
          tabButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabId));
          panels.forEach((panel) => panel.classList.toggle("active", panel.id === tabId));
        }

        tabButtons.forEach((btn) => {
          btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
        });

        function renderTierBreakdown(tierResultsData) {
          return Object.entries(tierResultsData || {}).map(([name, result]) => `
            <div class="tier-item">
              <strong>${name}</strong>
              <div>Status: ${result.status}</div>
              <div>Score: ${result.score}</div>
              <div>${result.reason}</div>
            </div>
          `).join("");
        }

        function getBadgeClass(action) {
          const normalized = (action || "").toLowerCase();
          if (normalized === "allow") return "allow";
          if (normalized === "block") return "block";
          return "flag";
        }

        function appendMessage(role, text, evaluationHtml = "") {
          if (chatWindow.querySelector(".empty-state")) {
            chatWindow.innerHTML = "";
          }
          const message = document.createElement("div");
          message.className = `message ${role}`;
          message.innerHTML = `
            <div class="meta">
              <span>${role === "user" ? "You" : "ControlPlane"}</span>
              <span>${new Date().toLocaleTimeString()}</span>
            </div>
            <div>${text}</div>
            ${evaluationHtml ? `<details><summary>Evaluation</summary>${evaluationHtml}</details>` : ""}
          `;
          chatWindow.appendChild(message);
          chatWindow.scrollTop = chatWindow.scrollHeight;
        }

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

        async function sendChat() {
          const message = chatInput.value.trim();
          if (!message) return;

          appendMessage("user", message);
          chatInput.value = "";
          sendChatBtn.disabled = true;
          sendChatBtn.textContent = "Sending...";

          const placeholder = document.createElement("div");
          placeholder.className = "message ai loading";
          placeholder.textContent = "Thinking with ControlPlane...";
          chatWindow.appendChild(placeholder);
          chatWindow.scrollTop = chatWindow.scrollHeight;

          try {
            const response = await fetch("/api/chat", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                message,
                use_case: document.getElementById("use_case").value || "default",
                policy_path: "config.yaml",
                retrieval_limit: 5,
                context: { user_prompt: message },
              }),
            });

            const data = await response.json();
            placeholder.remove();

            const evaluation = data.evaluation || {};
            const decision = evaluation.decision || {};
            const scoring = evaluation.scoring || {};
            const tierResultsData = evaluation.tier_results || {};
            const action = decision.action || "flag";
            const badgeClass = getBadgeClass(action);

            chatBadge.className = `badge ${badgeClass}`;
            chatBadge.textContent = `${action.toUpperCase()} | Confidence: ${scoring.final_confidence ?? scoring.confidence ?? "-"}`;

            chatEvaluation.innerHTML = `
              <div class="pill">Action: ${action}</div>
              <div class="pill">Confidence: ${scoring.final_confidence ?? scoring.confidence ?? "-"}</div>
              <div class="pill">Retrieved facts: ${(evaluation.retrieved_facts || []).length}</div>
              <div style="margin-top: 12px;">${renderTierBreakdown(tierResultsData)}</div>
            `;

            appendMessage("ai", data.reply, `
              <div class="pill">Action: ${action}</div>
              <div class="pill">Confidence: ${scoring.final_confidence ?? scoring.confidence ?? "-"}</div>
              <div style="margin-top: 12px;">${renderTierBreakdown(tierResultsData)}</div>
            `);
          } catch (error) {
            placeholder.remove();
            appendMessage("ai", `There was an error calling /api/chat: ${error}`);
          } finally {
            sendChatBtn.disabled = false;
            sendChatBtn.textContent = "Send";
          }
        }

        sendChatBtn.addEventListener("click", sendChat);
        chatInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendChat();
          }
        });
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
