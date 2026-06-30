"""
pages.chatbot
=============
AI Sourcing Chatbot tab. The conversation engine lives in
``services.chatbot_service``; this page owns layout, chat history, and
input handling only.

Dependencies
------------
* ``services.chatbot_service`` — Gemini-backed Q&A with JD grounding
* ``core.helpers``             — gemini_keys for the availability hint
"""

from __future__ import annotations

import streamlit as st

from core.helpers import gemini_keys as _gemini_keys
from services import chatbot_service


def render() -> None:
    """Render the chatbot page."""

    st.markdown("""
    <div class="page-header">
      <div class="page-header-pill">💬 &nbsp; AI Recruiting Assistant</div>
      <h1>Ask Anything About <span class="glow">Your Pipeline</span></h1>
      <p>Grounded on your JD + scored candidates · Powered by Gemini</p>
    </div>""", unsafe_allow_html=True)

    if not _gemini_key():
        st.warning("⚠ Add your Gemini API key in the sidebar to enable the chatbot.")
    else:
        # Context for Gemini
        jd = st.session_state.jd_data or {}
        candidates_context = []
        if st.session_state.scored_df is not None:
            scored = st.session_state.scored_df
            name_col = st.session_state.name_col_detected
            for _, row in scored.head(20).iterrows():
                rec = {k: v for k, v in row.items() if not str(v) in ("nan","None") and pd.notna(v)}
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
            with st.spinner("Thinking…"):
                try:
                    from services.provider_factory import get_provider
                    provider = get_provider("gemini", _gemini_keys())
                    reply = provider.chat(
                        user_msg,
                        context=context,
                        history=st.session_state.chat_history[:-1],
                    )
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
            st.rerun()


