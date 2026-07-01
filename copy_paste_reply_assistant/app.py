import json
import os
from typing import Optional

import google.generativeai as genai
import streamlit as st
import streamlit.components.v1 as components


MODEL_NAME = "gemini-2.5-flash"


st.set_page_config(page_title="Copy-Paste Reply Assistant", layout="wide")


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    try:
        value = st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        value = os.environ.get(name, default)
    return str(value) if value is not None else default


def build_prompt(
    incoming_message: str,
    sender_type: str,
    platform: str,
    tone: str,
    language: str,
    reply_length: str,
    extra_context: str,
    style_examples: str,
) -> str:
    return f"""
You are writing a reply on behalf of the user.

Goal:
Write a natural, useful reply that the user can copy and paste into {platform}.

Sender type:
{sender_type}

Tone:
{tone}

Reply language:
{language}

Reply length:
{reply_length}

Extra context about the situation:
{extra_context or "None"}

User's writing style examples:
{style_examples or "None"}

Rules:
- Return only the reply text.
- Do not add labels, explanations, markdown headings, or quotation marks.
- Be natural and human.
- Be polite and professional when the sender is a customer or stranger.
- Be warm and casual when the sender is a friend.
- If important information is missing, ask one short clarifying question.
- Do not promise actions the user has not confirmed.
- Do not mention that you are an AI.

Incoming message:
{incoming_message}
""".strip()


def generate_reply(
    incoming_message: str,
    sender_type: str,
    platform: str,
    tone: str,
    language: str,
    reply_length: str,
    extra_context: str,
    style_examples: str,
) -> str:
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from Streamlit Secrets or environment variables.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    prompt = build_prompt(
        incoming_message=incoming_message,
        sender_type=sender_type,
        platform=platform,
        tone=tone,
        language=language,
        reply_length=reply_length,
        extra_context=extra_context,
        style_examples=style_examples,
    )
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.5,
            "max_output_tokens": 500,
        },
    )
    return (response.text or "").strip()


def render_copy_button(text: str, key: str) -> None:
    safe_text = json.dumps(text)
    components.html(
        f"""
        <button
            id="{key}"
            style="
                background:#ff4b4b;
                border:0;
                border-radius:8px;
                color:white;
                cursor:pointer;
                font:600 14px system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                padding:10px 14px;
            "
        >
            Copy Reply
        </button>
        <span id="{key}-status" style="margin-left:10px;color:#8b949e;font:14px system-ui;"></span>
        <script>
            const button = document.getElementById("{key}");
            const status = document.getElementById("{key}-status");
            button.addEventListener("click", async () => {{
                try {{
                    await navigator.clipboard.writeText({safe_text});
                    status.textContent = "Copied";
                }} catch (error) {{
                    status.textContent = "Copy failed. Select the text manually.";
                }}
                setTimeout(() => {{
                    status.textContent = "";
                }}, 2500);
            }});
        </script>
        """,
        height=48,
    )


st.title("Copy-Paste Reply Assistant")
st.caption(
    "Paste a Facebook, WhatsApp, or Instagram message. The app creates a reply draft. "
    "It does not send messages automatically."
)

with st.sidebar:
    st.header("Reply Settings")
    platform = st.selectbox("Platform", ["Facebook Messenger", "WhatsApp", "Instagram DM", "Other"])
    sender_type = st.selectbox("Sender type", ["Customer", "Friend", "Stranger", "Lead", "Colleague"])
    tone = st.selectbox(
        "Tone",
        [
            "Friendly and professional",
            "Short and direct",
            "Warm and casual",
            "Polite and formal",
            "Apologetic and helpful",
        ],
    )
    language = st.selectbox("Reply language", ["English", "German", "Burmese", "Thai"])
    reply_length = st.selectbox("Reply length", ["Short", "Medium", "Detailed"])

    st.header("Safety")
    st.write("- Draft only")
    st.write("- No auto-send")
    st.write("- You review before sending")


incoming_message = st.text_area(
    "Incoming message",
    height=180,
    placeholder="Paste the message you received here...",
)

extra_context = st.text_area(
    "Extra context (optional)",
    height=100,
    placeholder="Example: customer asked about price, delivery is available tomorrow, be polite...",
)

style_examples = st.text_area(
    "Your style examples (optional)",
    height=100,
    placeholder="Paste 1-3 example replies you like. The app will imitate the style lightly.",
)

col1, col2 = st.columns([1, 3])
with col1:
    generate = st.button("Generate Reply", type="primary")
with col2:
    st.write("")

if generate:
    if not incoming_message.strip():
        st.error("Please paste an incoming message first.")
    else:
        with st.spinner("Writing reply draft..."):
            try:
                st.session_state["reply_draft"] = generate_reply(
                    incoming_message=incoming_message.strip(),
                    sender_type=sender_type,
                    platform=platform,
                    tone=tone,
                    language=language,
                    reply_length=reply_length,
                    extra_context=extra_context.strip(),
                    style_examples=style_examples.strip(),
                )
            except Exception as exc:
                st.error(f"Could not generate reply: {exc}")


reply_draft = st.session_state.get("reply_draft", "")
if reply_draft:
    st.subheader("Reply Draft")
    st.text_area("Edit before copying", value=reply_draft, height=220, key="reply_draft_editor")
    render_copy_button(st.session_state.get("reply_draft_editor", reply_draft), "copy_reply")

    st.info("After copying, paste the reply into Facebook Messenger, WhatsApp, or Instagram and send manually.")
