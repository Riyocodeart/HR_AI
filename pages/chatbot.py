"""
pages.chatbot
=============
AI Sourcing Chatbot tab. Supports two engines:

  * Gemini (cloud)         — used when a Gemini API key is configured
  * Qwen 2.5 via Ollama    — fully local/offline fallback, no API key needed

This page owns layout, chat history, input handling, and engine selection.
The Gemini path still goes through ``services.provider_factory``; the local
path talks to a locally-running Ollama server directly over HTTP.

Dependencies
------------
* ``services.provider_factory`` — Gemini-backed Q&A with JD grounding
* ``core.helpers``               — gemini_keys() for the availability hint
* ``requests``                   — HTTP calls to the local Ollama server
* ``pandas``                     — filtering candidate rows for context
"""

from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st

from core.helpers import gemini_keys as _gemini_keys
from services import chatbot_service  # noqa: F401  (kept for parity with docstring / future use)

# ── Local LLM (Ollama) configuration ────────────────────────────────────────
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_HOST}/api/chat"
OLLAMA_DEFAULT_MODEL = "qwen2.5"
OLLAMA_TIMEOUT_SECONDS = 120


def _ollama_is_reachable() -> bool:
    """Cheap liveness check so we can show a helpful hint instead of a stack trace."""
    try:
        requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False


def _build_context_prompt(context: dict) -> str:
    """Serialise JD + candidate context into a compact system prompt.

    Local models have smaller context windows than Gemini in practice for
    this use case, so we cap the JSON size defensively rather than dumping
    the full candidate list unbounded.
    """
    jd_json = json.dumps(context.get("jd", {}), default=str)[:4000]
    candidates_json = json.dumps(context.get("candidates", []), default=str)[:6000]
    return (
        "You are NexRecruit AI, a recruiting assistant embedded in a candidate "
        "sourcing tool. Answer the user's question using ONLY the job "
        "description and candidate data below. Be concise and specific, and "
        "reference candidate names/ids when relevant. If the data doesn't "
        "contain the answer, say so plainly instead of guessing.\n\n"
        f"JOB DESCRIPTION:\n{jd_json}\n\n"
        f"CANDIDATES (top matches):\n{candidates_json}"
    )


def _chat_via_ollama(user_msg: str, context: dict, history: list[dict], model: str = OLLAMA_DEFAULT_MODEL) -> str:
    """Send a chat turn to a local Ollama server running Qwen 2.5 (or another
    pulled model). Raises requests.exceptions.RequestException on failure so
    the caller can surface a clear, actionable error."""
    messages = [{"role": "system", "content": _build_context_prompt(context)}]
    for m in history:
        role = "user" if m.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": m.get("content", "")})
    messages.append({"role": "user", "content": user_msg})

    resp = requests.post(
        OLLAMA_CHAT_URL,
        json={"model": model, "messages": messages, "stream": False},
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    data = resp.json()
    reply = (data.get("message") or {}).get("content", "").strip()
    return reply or "(The local model returned an empty response.)"


def _chat_via_gemini(user_msg: str, context: dict, history: list[dict]) -> str:
    from services.provider_factory import get_provider
    provider = get_provider("gemini", _gemini_keys())
    return provider.chat(user_msg, context=context, history=history)


def render() -> None:
    """Render the chatbot page."""

    st.markdown("""
    <div class="page-header">
      <div class="page-header-pill">💬 &nbsp; AI Recruiting Assistant</div>
      <h1>Ask Anything About <span class="glow">Your Pipeline</span></h1>
      <p>Grounded on your JD + scored candidates · Gemini or fully local Qwen 2.5</p>
    </div>""", unsafe_allow_html=True)

    has_gemini = bool(_gemini_keys())
    ollama_up = _ollama_is_reachable()

    # ── Engine selection ────────────────────────────────────────────────────
    engine_options = []
    if has_gemini:
        engine_options.append("Gemini (cloud)")
    engine_options.append("Qwen 2.5 (local, offline)")

    if "chat_engine" not in st.session_state:
        st.session_state.chat_engine = engine_options[0]

    if len(engine_options) > 1:
        st.session_state.chat_engine = st.radio(
            "AI engine",
            engine_options,
            index=engine_options.index(st.session_state.chat_engine) if st.session_state.chat_engine in engine_options else 0,
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        st.session_state.chat_engine = engine_options[0]

    use_local = st.session_state.chat_engine.startswith("Qwen")

    if not has_gemini and not ollama_up:
        st.warning(
            "⚠ No Gemini API key is configured, and no local Ollama server was "
            "found at `localhost:11434`. Either add a Gemini key in the "
            "sidebar, or start a local model with `ollama serve` and "
            f"`ollama pull {OLLAMA_DEFAULT_MODEL}`."
        )
        return

    if use_local and not ollama_up:
        st.warning(
            "⚠ Qwen 2.5 (local) is selected, but Ollama isn't reachable at "
            f"`{OLLAMA_HOST}`. Run `ollama serve` in a terminal, then "
            f"`ollama pull {OLLAMA_DEFAULT_MODEL}` if you haven't already."
        )
        return

    # Context for the model
    jd = st.session_state.jd_data or {}
    candidates_context = []
    if st.session_state.scored_df is not None:
        scored = st.session_state.scored_df
        for _, row in scored.head(20).iterrows():
            rec = {k: v for k, v in row.items() if str(v) not in ("nan", "None") and pd.notna(v)}
            candidates_context.append(rec)

    context = {"jd": jd, "candidates": candidates_context}

    # Display chat history
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="dark-card" style="text-align:center;padding:2rem">
          <div style="font-size:2rem;margin-bottom:0.5rem">💬</div>
          <div style="color:rgba(255,255,255,0.5);font-size:0.9rem">Ask me anything about the JD or candidates.</div>
          <div style="color:rgba(255,255,255,0.3);font-size:0.78rem;margin-top:0.75rem">
            Try: "Who is the best candidate and why?" · "Which candidates are missing Python?" · "Summarise the JD"
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="dark-card" style="min-height:300px;max-height:500px;overflow-y:auto">', unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                st.markdown(f'<div style="margin-bottom:0.3rem"><div class="chat-sender">You</div><div class="chat-bubble-user">{content}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="margin-bottom:0.3rem"><div class="chat-sender chat-sender-ai">NexRecruit AI</div><div class="chat-bubble-ai">{content}</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_input("Your question", placeholder="Who is the best candidate and why?", label_visibility="collapsed")
        send = st.form_submit_button("Send ➤", use_container_width=True)

    if send and user_msg.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        with st.spinner(f"Thinking… ({st.session_state.chat_engine})"):
            try:
                history_so_far = st.session_state.chat_history[:-1]
                if use_local:
                    reply = _chat_via_ollama(user_msg, context, history_so_far)
                else:
                    reply = _chat_via_gemini(user_msg, context, history_so_far)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            except requests.exceptions.RequestException as e:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Local model error: couldn't reach Ollama ({e}). Is `ollama serve` running?",
                })
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
        st.rerun()