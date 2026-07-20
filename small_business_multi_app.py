import streamlit as st


pages = [
    st.Page("multi_app_home.py", title="Home", icon="🏠", url_path="home", default=True),
    st.Page("app.py", title="Email Triage Assistant", icon="📧", url_path="email-triage"),
    st.Page("lead_crm_mini_app/app.py", title="Lead CRM Mini App", icon="📇", url_path="lead-crm"),
    st.Page("job_project_tracker/app.py", title="Job / Project Tracker", icon="📋", url_path="project-tracker"),
    st.Page(
        "invoice_payment_reminder/app.py",
        title="Invoice & Payment Reminder",
        icon="💶",
        url_path="invoice-reminder",
    ),
    st.Page(
        "knowledge_base_chatbot/app.py",
        title="Knowledge Base Chatbot",
        icon="📚",
        url_path="knowledge-base",
    ),
    st.Page(
        "daily_ai_news_digest/app.py",
        title="Daily AI News Digest",
        icon="📰",
        url_path="ai-news",
    ),
]


navigation = st.navigation(
    {
        "Home": pages[:1],
        "Core tools": pages[1:5],
        "AI assistants": pages[5:],
    }
)
navigation.run()
