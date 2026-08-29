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
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;500;600;700&display=swap');
        :root { 
            --ink:#e2e8f0; --muted:#94a3b8; --line:rgba(255,255,255,0.08); 
            --blue:#38bdf8; --violet:#818cf8; --surface:rgba(15, 23, 42, 0.6); 
            --bg:#020617; --field:rgba(2, 6, 23, 0.4); --field-focus:rgba(2, 6, 23, 0.6); 
            --card:rgba(15, 23, 42, 0.6); --app-bg:rgba(15, 23, 42, 0.4); --nav-bg:rgba(2, 6, 23, 0.3); 
            --panel-bg:rgba(2, 6, 23, 0.5); --panel-border:rgba(255,255,255,0.05);
            --tier-bg:rgba(2, 6, 23, 0.4); --tier-border:rgba(255,255,255,0.03); 
            --pill-bg:rgba(14, 165, 233, 0.2); --pill-border:rgba(14, 165, 233, 0.3); --pill-text:#e0f2fe;
            --sug-bg:rgba(30, 27, 75, 0.4); --sug-border:rgba(129,140,248,0.2); --sug-text:#a5b4fc; --sug-hover-bg:rgba(129,140,248,0.15); --sug-hover-text:#fff;
            --ai-msg-bg:rgba(30, 41, 59, 0.7); --ai-msg-border:rgba(255,255,255,0.05); --ai-msg-text:#e2e8f0;
            --details-bg:rgba(0,0,0,0.2); --details-border:rgba(255,255,255,0.03);
            --tab-bg:rgba(15, 23, 42, 0.4); --tab-hover:rgba(255,255,255,0.05);
        }
        * { box-sizing:border-box; }
        body { margin:0; min-height:100vh; font-family:'Inter', sans-serif; color:var(--ink); background:var(--bg); background-image: radial-gradient(circle at 15% 50%, rgba(56, 189, 248, 0.08), transparent 25%), radial-gradient(circle at 85% 30%, rgba(129, 140, 248, 0.08), transparent 25%); background-attachment: fixed; }
        body[data-theme="light"] { 
            --ink:#172033; --muted:#475569; --line:rgba(15, 23, 42, 0.1); 
            --surface:rgba(255, 255, 255, 0.72); --bg:#f8fafc; --field:#fff; --field-focus:#fff; 
            --card:rgba(255, 255, 255, 0.9); --app-bg:rgba(255, 255, 255, 0.85); --nav-bg:rgba(255, 255, 255, 0.6); 
            --panel-bg:rgba(241, 245, 249, 0.8); --panel-border:rgba(15, 23, 42, 0.08);
            --tier-bg:#fff; --tier-border:rgba(15, 23, 42, 0.06); 
            --pill-bg:rgba(14, 165, 233, 0.1); --pill-border:rgba(14, 165, 233, 0.2); --pill-text:#0284c7;
            --sug-bg:#fff; --sug-border:rgba(129,140,248,0.3); --sug-text:#4f46e5; --sug-hover-bg:rgba(129,140,248,0.1); --sug-hover-text:#4338ca;
            --ai-msg-bg:#f1f5f9; --ai-msg-border:rgba(15, 23, 42, 0.05); --ai-msg-text:#1e293b;
            --details-bg:rgba(15, 23, 42, 0.03); --details-border:rgba(15, 23, 42, 0.05);
            --tab-bg:rgba(255, 255, 255, 0.6); --tab-hover:rgba(255, 255, 255, 0.9);
            background-image: radial-gradient(circle at 15% 50%, rgba(14, 165, 233, 0.12), transparent 25%), radial-gradient(circle at 85% 30%, rgba(129, 140, 248, 0.12), transparent 25%); 
        }
        button,textarea,input { font:inherit; transition: all 0.2s ease; }
        .app { max-width:1500px; min-height:calc(100vh - 44px); margin:22px auto; display:grid; grid-template-columns:220px minmax(0,1fr); overflow:hidden; background:var(--app-bg); backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px); border:1px solid var(--line); border-radius:24px; box-shadow:0 24px 80px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.1); }
        .side-nav { min-height:100%; display:flex; flex-direction:column; padding:32px 20px; border-right:1px solid var(--line); background:var(--nav-bg); position:relative; overflow:hidden; }
        .brand { display:flex; align-items:center; gap:12px; padding:0 8px 40px; color:var(--ink); font-family:'Outfit', sans-serif; font-weight:800; font-size:15px; letter-spacing:.05em; text-transform:uppercase; background:linear-gradient(135deg, #38bdf8, #818cf8); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
        .brand-mark { width:20px; height:20px; position:relative; display:block; } .brand-mark i { position:absolute; width:10px; height:10px; border-radius:50%; background:linear-gradient(135deg,#38bdf8,#818cf8); box-shadow: 0 0 10px rgba(56, 189, 248, 0.5); } .brand-mark i:first-child { left:0; bottom:0; } .brand-mark i:nth-child(2) { left:6px; top:0; } .brand-mark i:last-child { right:0; bottom:0; }
        .nav-btn { border:0; background:transparent; color:var(--muted); display:flex; align-items:center; gap:14px; width:100%; padding:14px 16px; border-radius:12px; text-align:left; cursor:pointer; font-size:13px; font-weight:500; margin:4px 0; }
        .nav-btn:hover { background:var(--tab-hover); color:var(--ink); }
        .nav-btn svg { width:18px; height:18px; stroke:currentColor; fill:none; stroke-width:2; opacity:0.8; } .nav-btn.active { background:rgba(56, 189, 248, 0.1); color:#0284c7; font-weight:600; border:1px solid rgba(56, 189, 248, 0.2); box-shadow:inset 0 0 12px rgba(56, 189, 248, 0.05); } body[data-theme="dark"] .nav-btn.active { color:#38bdf8; } .nav-btn.chat-active { background:rgba(129, 140, 248, 0.1); color:#4f46e5; border:1px solid rgba(129, 140, 248, 0.2); } body[data-theme="dark"] .nav-btn.chat-active { color:#818cf8; }
        .nav-footer { margin:auto 14px 10px; z-index:1; color:var(--muted); font-size:11px; line-height:1.6; } .sparkle { font-size:18px; color:#38bdf8; display:block; margin-bottom:8px; text-shadow: 0 0 10px rgba(56,189,248,0.4); }
        .workspace { padding:40px; min-width:0; position:relative; z-index:1; }
        .header-row { display:flex; justify-content:space-between; align-items:flex-start; gap:24px; margin-bottom:32px; }
        .page-head { margin:0; } .eyebrow { color:#38bdf8; font-family:'Outfit', sans-serif; font-size:11px; font-weight:800; letter-spacing:.2em; text-transform:uppercase; margin-bottom:12px; display:flex; align-items:center; } .eyebrow span { margin-right:8px; font-size:14px; text-shadow:0 0 8px rgba(56,189,248,0.5); } h1 { font-family:'Outfit', sans-serif; font-size:32px; font-weight:600; margin:0 0 12px; color:var(--ink); letter-spacing:-.02em; } .subtitle { color:var(--muted); font-size:14px; line-height:1.6; margin:0; max-width:650px; font-weight:400; }
        .theme-toggle { flex:0 0 auto; display:inline-flex; align-items:center; gap:10px; border:1px solid var(--line); border-radius:999px; color:var(--ink); background:var(--surface); padding:10px 16px; cursor:pointer; font-size:13px; font-weight:700; box-shadow:0 12px 30px rgba(0,0,0,0.12); }
        .theme-toggle:hover { border-color:rgba(56,189,248,0.45); transform:translateY(-1px); }
        .tabs { display:flex; gap:12px; margin:0 0 32px; } .tab-btn { display:flex; align-items:center; gap:10px; border:1px solid var(--line); background:var(--tab-bg); color:var(--muted); padding:12px 24px; border-radius:99px; font-size:13px; font-weight:600; cursor:pointer; backdrop-filter:blur(8px); } .tab-btn:hover { background:var(--tab-hover); color:var(--ink); } .tab-btn.active { color:var(--ink); border:1px solid rgba(56,189,248,0.3); background:linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(14, 165, 233, 0.1)); box-shadow:0 0 20px rgba(56,189,248,0.1); } .tab-btn svg { width:18px; height:18px; fill:none; stroke:currentColor; stroke-width:2; }
        .panel { display:none; animation:fadeIn 0.4s ease; } .panel.active { display:block; } @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
        .card { background:var(--card); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); border:1px solid var(--line); border-radius:20px; box-shadow:0 8px 32px rgba(0,0,0,0.16); padding:32px; position:relative; overflow:hidden; } .card::before { content:''; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent); } .card h2 { font-family:'Outfit', sans-serif; font-size:18px; font-weight:600; color:var(--ink); margin:0 0 24px; display:flex; align-items:center; gap:12px; } .section-icon { color:#38bdf8; background:rgba(56, 189, 248, 0.1); border:1px solid rgba(56, 189, 248, 0.2); width:32px; height:32px; border-radius:10px; display:grid; place-items:center; box-shadow:inset 0 0 10px rgba(56,189,248,0.1); }
        label { display:block; color:var(--ink); font-size:13px; font-weight:500; margin:20px 0 10px; } textarea,input { width:100%; outline:none; padding:16px 20px; border:1px solid var(--line); border-radius:12px; color:var(--ink); background:var(--field); font-size:14px; resize:vertical; transition:all 0.2s; scrollbar-width:none; -ms-overflow-style:none; } textarea::-webkit-scrollbar,input::-webkit-scrollbar { width:0; height:0; display:none; } textarea::placeholder,input::placeholder { color:var(--muted); } textarea:focus,input:focus { border-color:rgba(56,189,248,0.5); background:var(--field-focus); box-shadow:0 0 0 4px rgba(56, 189, 248, 0.1); } textarea { min-height:100px; }
        .run-btn,.send-btn { border:0; color:#fff; cursor:pointer; font-size:14px; font-weight:600; border-radius:99px; padding:14px 28px; background:linear-gradient(135deg, #0ea5e9, #38bdf8); box-shadow:0 10px 20px -10px rgba(56,189,248,0.5); display:inline-flex; align-items:center; gap:8px; transition:all 0.2s; } .run-btn:hover,.send-btn:hover { transform:translateY(-2px); box-shadow:0 14px 24px -10px rgba(56,189,248,0.6); } .run-btn:active,.send-btn:active { transform:translateY(0); } .run-btn { margin-top:24px; } .send-btn { padding:12px 24px; background:linear-gradient(135deg, #6366f1, #818cf8); box-shadow:0 10px 20px -10px rgba(129,140,248,0.5); border-radius:12px; } button:disabled { opacity:.5; cursor:not-allowed; transform:none !important; }
        .eval-layout { max-width:100%; display:grid; grid-template-columns:1fr 1fr; gap:24px; align-items:start; } .results-card { margin-top:0; max-width:100%; } .pills { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:24px; } .pill { color:var(--pill-text); background:var(--pill-bg); border:1px solid var(--pill-border); border-radius:99px; padding:8px 16px; font-size:13px; font-weight:500; display:flex; align-items:center; gap:8px; box-shadow:inset 0 0 10px rgba(14,165,233,0.1); } .pill:nth-child(2) { color:#15803d; background:rgba(34, 197, 94, 0.15); border-color:rgba(34, 197, 94, 0.3); box-shadow:inset 0 0 10px rgba(34,197,94,0.1); } body[data-theme="dark"] .pill:nth-child(2) { color:#dcfce7; } h3 { font-family:'Outfit', sans-serif; font-size:15px; margin:24px 0 12px; color:var(--ink); font-weight:500; } pre,.empty-state { margin:0; padding:24px; color:var(--muted); background:var(--panel-bg); border:1px solid var(--panel-border); border-radius:12px; font-size:13px; font-family:'JetBrains Mono', monospace; line-height:1.6; white-space:pre-wrap; word-break:break-word; } .empty-state { text-align:center; min-height:120px; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:12px; }
        .chat-card { min-height:600px; display:flex; flex-direction:column; padding:24px 32px; } .chat-window { height:400px; max-height:60vh; flex:none; display:flex; flex-direction:column; gap:20px; overflow-y:auto; padding:10px 10px 24px 0; scroll-behavior:smooth; scrollbar-width:none; -ms-overflow-style:none; } .chat-window::-webkit-scrollbar { width:0; height:0; display:none; }
        .chat-empty { margin:auto; text-align:center; max-width:420px; } .chat-empty .chat-orb { width:64px; height:64px; margin:0 auto 20px; display:grid; place-items:center; border-radius:50%; background:linear-gradient(135deg, rgba(129,140,248,0.2), rgba(99,102,241,0.1)); border:1px solid rgba(129,140,248,0.3); color:#818cf8; font-size:24px; box-shadow:0 0 30px rgba(129,140,248,0.2), inset 0 0 15px rgba(129,140,248,0.2); } .chat-empty h3 { font-family:'Outfit', sans-serif; font-size:20px; margin:0 0 12px; color:var(--ink); } .suggestions { display:flex; flex-wrap:wrap; justify-content:center; gap:12px; margin-top:40px; } .suggestions button { border:1px solid var(--sug-border); color:var(--sug-text); background:var(--sug-bg); border-radius:99px; padding:12px 20px; cursor:pointer; font-size:13px; transition:all 0.2s; backdrop-filter:blur(4px); } .suggestions button:hover { background:var(--sug-hover-bg); color:var(--sug-hover-text); transform:translateY(-2px); }
        .chat-input { display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:16px; border:1px solid var(--line); border-radius:16px; padding:10px 10px 10px 16px; background:var(--field-focus); box-shadow:0 8px 24px rgba(0,0,0,0.14); margin-top:auto; transition:border-color 0.2s; } .chat-input:focus-within { border-color:rgba(129,140,248,0.4); } .chat-input textarea { border:0; padding:10px 0; margin:0; min-height:44px; height:44px; background:transparent; resize:none; box-shadow:none; font-size:14px; line-height:1.5; overflow:hidden; } .chat-input textarea:focus { box-shadow:none; } .attach { color:var(--muted); font-size:18px; cursor:pointer; transition:color 0.2s; } .attach:hover { color:var(--ink); }
        .message { max-width:85%; padding:16px 20px; font-size:14px; line-height:1.6; border-radius:16px; white-space:pre-wrap; box-shadow:0 4px 12px rgba(0,0,0,0.1); } .message.user { align-self:flex-end; color:#fff; background:linear-gradient(135deg, #38bdf8, #0284c7); border-bottom-right-radius:4px; } .message.ai { align-self:flex-start; background:var(--ai-msg-bg); border:1px solid var(--ai-msg-border); color:var(--ai-msg-text); border-bottom-left-radius:4px; } .message .meta { font-size:11px; color:rgba(255,255,255,0.6); margin-bottom:8px; display:flex; justify-content:space-between; gap:16px; font-weight:500; text-transform:uppercase; letter-spacing:0.05em; } .message.ai .meta { color:var(--muted); } details { margin-top:16px; font-size:13px; background:var(--details-bg); border-radius:8px; padding:12px; border:1px solid var(--details-border); } summary { cursor:pointer; font-weight:600; color:#38bdf8; display:flex; align-items:center; gap:8px; } summary::-webkit-details-marker { display:none; } summary::before { content:'►'; font-size:10px; transition:transform 0.2s; } details[open] summary::before { transform:rotate(90deg); }
        .badge-card { margin-top:0; max-width:100%; display:flex; flex-direction:column; gap:16px; padding:24px; } .badge-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; } .badge { display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:99px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; } .badge::before { content:''; display:block; width:6px; height:6px; border-radius:50%; } .badge.allow { color:#10b981; background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.2); } .badge.allow::before { background:#10b981; box-shadow:0 0 8px #10b981; } .badge.block { color:#ef4444; background:rgba(239, 68, 68, 0.1); border:1px solid rgba(239, 68, 68, 0.2); } .badge.block::before { background:#ef4444; box-shadow:0 0 8px #ef4444; } .badge.flag { color:#f59e0b; background:rgba(245, 158, 11, 0.1); border:1px solid rgba(245, 158, 11, 0.2); } .badge.flag::before { background:#f59e0b; box-shadow:0 0 8px #f59e0b; } .tier-container { display:flex; flex-direction:column; gap:8px; } .tier-item { padding:12px 16px; background:var(--tier-bg); border:1px solid var(--tier-border); border-radius:12px; color:var(--muted); font-size:12px; line-height:1.5; display:flex; flex-direction:column; gap:4px; } .tier-item strong { color:var(--ink); font-weight:600; font-family:'Outfit', sans-serif; font-size:13px; text-transform:capitalize; }
        @media (max-width:900px) { .app { grid-template-columns:1fr; margin:0; min-height:100vh; border-radius:0; border:none; } .side-nav { min-height:auto; padding:20px; border-right:none; border-bottom:1px solid var(--line); flex-direction:row; align-items:center; flex-wrap:wrap; gap:12px; } .brand { padding:0; margin-right:auto; } .nav-btn { width:auto; padding:10px 16px; margin:0; } .nav-footer { display:none; } .workspace { padding:24px; } .eval-layout, .results-card { max-width:100%; } }
      </style>
    </head>
    <body>
      <div class="app">
        <aside class="side-nav">
          <div class="brand"><span class="brand-mark"><i></i><i></i><i></i></span> CONTROLPLANE.AI</div>
          <button class="nav-btn active" data-tab="evaluatePanel"><svg viewBox="0 0 24 24"><path d="M4 19V5m0 14h16M8 15l3-3 3 2 5-6"/></svg>Evaluate</button>
          <button class="nav-btn" data-tab="chatPanel"><svg viewBox="0 0 24 24"><path d="M20 15a4 4 0 0 1-4 4H8l-4 3v-7a4 4 0 0 1-1-3V8a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4z"/></svg>Live Chat</button>
          <div class="nav-footer"><span class="sparkle">✣</span>Better evaluation.<br>More reliable AI.</div>
        </aside>
        <main class="workspace">
          <div class="header-row">
            <header class="page-head"><div id="pageEyebrow" class="eyebrow"><span>⌁</span> EVALUATE</div><h1 id="pageTitle">Evaluation Dashboard</h1><p id="pageDescription" class="subtitle">Use the classic evaluator or switch to Live Chat to ground answers against internal knowledge and see the governance payload for each turn.</p></header>
            <button id="themeToggle" class="theme-toggle" type="button" aria-label="Switch to light mode">Light mode</button>
          </div>
          <div class="tabs"><button class="tab-btn active" data-tab="evaluatePanel"><svg viewBox="0 0 24 24"><path d="M4 19V5m0 14h16M8 15l3-3 3 2 5-6"/></svg>Evaluate</button><button class="tab-btn" data-tab="chatPanel"><svg viewBox="0 0 24 24"><path d="M20 15a4 4 0 0 1-4 4H8l-4 3v-7a4 4 0 0 1-1-3V8a4 4 0 0 1 4-4h9a4 4 0 0 1 4 4z"/></svg>Live Chat</button></div>
          <section id="evaluatePanel" class="panel active"><div class="eval-layout"><div class="card">
              <h2><span class="section-icon">▣</span>Evaluate</h2>
              <form id="evalForm">
                <label>User Prompt</label>
                <textarea id="user_prompt" rows="4" placeholder="Enter the original prompt..."></textarea>
                <label>AI Response</label>
                <textarea id="ai_response" rows="5" placeholder="Enter the AI response..."></textarea>
                <label>Use Case</label>
                <input id="use_case" type="text" placeholder="customer_support_chatbot" />
                <button class="run-btn" type="submit">▶ &nbsp; Run Check</button>
              </form>
            </div><div class="card results-card">
              <h2><span class="section-icon">♜</span>Results</h2>
              <div id="summary" class="pills">
                <span class="pill">Action: -</span>
                <span class="pill">Confidence: -</span>
              </div>
              <h3>Tier Results</h3>
              <pre id="tierResults">✣  No results yet.\n\nRun an evaluation to see the results and tier breakdown.</pre>
            </div></div></section>
          <section id="chatPanel" class="panel"><div class="eval-layout"><div class="card chat-card">
              <div id="chatWindow" class="chat-window">
                <div class="chat-empty"><div class="chat-orb">◯</div><h3>Start a conversation</h3><p class="subtitle">Ask a question and get grounded responses with confidence and tier breakdown.</p><div class="suggestions"><button>What is our refund policy?</button><button>Explain the onboarding process.</button><button>How does pricing work?</button><button>Help with a technical issue.</button></div></div>
              </div>
              <div class="chat-input"><span class="attach">⌕</span><textarea id="chatInput" rows="1" placeholder="Ask about remote work stipends, IT security rules, or the Mess Management System..."></textarea><button class="send-btn" id="sendChatBtn" type="button">➤ &nbsp; Send</button>
              </div>
            </div><div class="card badge-card">
              <h2><span class="section-icon">⬟</span>ControlPlane Badge</h2>
              <div id="chatBadge" class="badge flag">Waiting</div>
              <p class="subtitle" style="margin-top:12px;">The latest message evaluation appears here with confidence, decision, and tier breakdown.</p>
              <details open>
                <summary>Latest evaluation</summary>
                <div id="chatEvaluation" style="margin-top: 12px;">
                  <div class="empty-state">No chat evaluated yet.</div>
                </div>
              </details>
            </div></div></section>
        </main>
      </div>
      <script>
        const form = document.getElementById("evalForm");
        const summary = document.getElementById("summary");
        const tierResults = document.getElementById("tierResults");
        const tabButtons = document.querySelectorAll(".tab-btn, .nav-btn");
        const panels = document.querySelectorAll(".panel");
        const chatWindow = document.getElementById("chatWindow");
        const chatInput = document.getElementById("chatInput");
        const sendChatBtn = document.getElementById("sendChatBtn");
        const chatBadge = document.getElementById("chatBadge");
        const chatEvaluation = document.getElementById("chatEvaluation");
        const pageEyebrow = document.getElementById("pageEyebrow");
        const pageTitle = document.getElementById("pageTitle");
        const pageDescription = document.getElementById("pageDescription");
        const themeToggle = document.getElementById("themeToggle");

        function applyTheme(theme) {
          document.body.dataset.theme = theme;
          localStorage.setItem("controlplane-theme", theme);
          const isLight = theme === "light";
          themeToggle.textContent = isLight ? "Dark mode" : "Light mode";
          themeToggle.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
        }

        applyTheme(localStorage.getItem("controlplane-theme") || "dark");
        themeToggle.addEventListener("click", () => {
          applyTheme(document.body.dataset.theme === "light" ? "dark" : "light");
        });

        function setActiveTab(tabId) {
          tabButtons.forEach((btn) => {
            const isActive = btn.dataset.tab === tabId;
            btn.classList.toggle("active", isActive);
            btn.setAttribute("aria-selected", isActive ? "true" : "false");
          });
          panels.forEach((panel) => {
            const isActive = panel.id === tabId;
            panel.classList.toggle("active", isActive);
            panel.style.display = isActive ? "block" : "none";
          });
          const isChat = tabId === "chatPanel";
          document.querySelectorAll(".side-nav .nav-btn").forEach((btn) => {
            btn.classList.toggle("chat-active", isChat && btn.dataset.tab === tabId);
          });
          pageEyebrow.innerHTML = isChat ? "<span>⌁</span> LIVE CHAT" : "<span>⌁</span> EVALUATE";
          pageTitle.textContent = isChat ? "Live Chat" : "Evaluation Dashboard";
          pageDescription.textContent = isChat
            ? "Messages will appear here. Ask a question to start a grounded chat."
            : "Use the classic evaluator or switch to Live Chat to ground answers against internal knowledge and see the governance payload for each turn.";
        }

        tabButtons.forEach((btn) => {
          btn.setAttribute("type", "button");
          btn.addEventListener("click", () => setActiveTab(btn.dataset.tab));
        });
        setActiveTab("evaluatePanel");

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
          if (chatWindow.querySelector(".chat-empty")) {
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
          requestAnimationFrame(() => {
            chatWindow.scrollTop = chatWindow.scrollHeight;
          });
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
          requestAnimationFrame(() => {
            chatWindow.scrollTop = chatWindow.scrollHeight;
          });

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
        document.querySelectorAll(".suggestions button").forEach((button) => {
          button.addEventListener("click", () => {
            chatInput.value = button.textContent;
            sendChat();
          });
        });
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
