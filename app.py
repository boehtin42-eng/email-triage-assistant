from datetime import date, timedelta

import streamlit as st

from triage_assistant import (
    classify_emails,
    create_excel_bytes,
    fetch_unread_emails,
    get_secret,
    test_email_connection,
    test_gemini_connection,
)


st.set_page_config(page_title="Email Triage Assistant", layout="wide")


def require_password() -> bool:
    app_password = get_secret("APP_PASSWORD")
    if not app_password:
        st.error("APP_PASSWORD is missing from Streamlit Secrets.")
        return False

    if st.session_state.get("authenticated"):
        return True

    st.title("Email Triage Assistant")
    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        if password == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False


if not require_password():
    st.stop()


st.title("Email Triage Assistant")
st.caption(
    "Read-only triage for unread emails. This app does not send, delete, mark as read, "
    "or update any external CRM."
)

with st.sidebar:
    st.header("Safety")
    st.write("- Reads unread emails only")
    st.write("- Does not send emails")
    st.write("- Does not delete emails")
    st.write("- Does not mark emails as read")

    limit = st.number_input("Email limit", min_value=1, max_value=50, value=10, step=1)
    use_date_filter = st.checkbox("Filter by date")
    start_date = None
    end_date = None

    if use_date_filter:
        today = date.today()
        start_date = st.date_input("Start date", value=today - timedelta(days=7))
        end_date = st.date_input("End date", value=today)

        if start_date > end_date:
            st.error("Start date must be before or equal to End date.")


st.subheader("Connection Tests")
col1, col2 = st.columns(2)

with col1:
    if st.button("Test Email"):
        ok, message = test_email_connection()
        st.success(message) if ok else st.error(message)

with col2:
    if st.button("Test Gemini"):
        ok, message = test_gemini_connection()
        st.success(message) if ok else st.error(message)


st.subheader("Unread Email Triage")
if st.button("Read Unread Emails and Create Draft Suggestions", type="primary"):
    if use_date_filter and start_date > end_date:
        st.error("Please fix the date range first.")
        st.stop()

    with st.spinner("Reading unread emails safely..."):
        emails = fetch_unread_emails(
            limit=int(limit),
            start_date=start_date if use_date_filter else None,
            end_date=end_date if use_date_filter else None,
        )

    if not emails:
        st.info("No unread emails found.")
        st.session_state["triage_results"] = []
    else:
        with st.spinner("Classifying emails and preparing draft suggestions..."):
            st.session_state["triage_results"] = classify_emails(emails)


results = st.session_state.get("triage_results", [])
if results:
    st.dataframe(results, use_container_width=True, hide_index=True)

    excel_bytes = create_excel_bytes(results)
    st.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name="email_triage_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
