import streamlit as st


st.title("Small Business Tools")
st.caption("One Streamlit app that groups the small-business tools in this workspace.")

st.info("Choose a tool from the sidebar.")

st.subheader("Available tools")
st.markdown(
    """
- Email Triage Assistant: classify unread emails and draft German replies.
- Lead CRM Mini App: track leads, follow-ups, notes, and next actions.
- Job / Project Tracker: track customer projects, deadlines, reminders, and next actions.
- Invoice & Payment Reminder: track invoices, overdue payments, and expense extraction.
- Knowledge Base Chatbot: answer questions from uploaded company documents.
- Daily AI News Digest: monitor business AI, ChatGPT, OpenAI, and Codex updates.
"""
)

st.warning(
    "This is a test multi-app shell. Some tools may still need their own Streamlit Secrets "
    "or setup before they work fully."
)
