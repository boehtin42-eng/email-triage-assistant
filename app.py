from datetime import date, timedelta

import pandas as pd
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


TABLE_COLUMNS = [
    "date",
    "from_name",
    "from_email",
    "subject",
    "category",
    "priority",
    "review_status",
    "german_reply_draft",
    "method",
    "reason",
]


TABLE_COLUMN_CONFIG = {
    "date": st.column_config.TextColumn("Date", width="small"),
    "from_name": st.column_config.TextColumn("From name", width="medium"),
    "from_email": st.column_config.TextColumn("From email", width="medium"),
    "subject": st.column_config.TextColumn("Subject", width="large"),
    "category": st.column_config.TextColumn("Category", width="small"),
    "priority": st.column_config.TextColumn("Priority", width="small"),
    "review_status": st.column_config.TextColumn("Review status", width="medium"),
    "german_reply_draft": st.column_config.TextColumn("German Reply Draft", width="large"),
    "method": st.column_config.TextColumn("Method", width="small"),
    "reason": st.column_config.TextColumn("Reason", width="large"),
}


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


def normalize_result_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = []
    for row in rows:
        clean = {column: str(row.get(column, "") or "") for column in TABLE_COLUMNS}
        normalized.append(clean)
    return normalized


def is_focus_email(row: dict[str, str]) -> bool:
    priority = row.get("priority", "").lower()
    category = row.get("category", "").lower()
    review_status = row.get("review_status", "").lower()
    return (
        priority in {"high", "unsure"}
        or category == "unsure"
        or review_status == "needs manual review"
    )


def render_email_table(title: str, rows: list[dict[str, str]], key_prefix: str) -> None:
    st.markdown(f"#### {title}")
    if not rows:
        st.info("No emails in this view.")
        return

    dataframe = pd.DataFrame(rows, columns=TABLE_COLUMNS)
    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
        column_order=TABLE_COLUMNS,
        column_config=TABLE_COLUMN_CONFIG,
    )

    options = []
    for index, row in enumerate(rows):
        label = f"{row.get('priority', '')} | {row.get('from_name', '')} | {row.get('subject', '')}"
        options.append((index, label[:180]))

    selected_index = st.selectbox(
        "Choose an email to copy/use its German reply draft",
        options=[option[0] for option in options],
        format_func=lambda index: dict(options).get(index, ""),
        key=f"{key_prefix}_draft_select",
    )
    selected = rows[selected_index]
    st.text_area(
        "German Reply Draft",
        value=selected.get("german_reply_draft", ""),
        height=220,
        key=f"{key_prefix}_draft_text",
    )


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
    normalized_results = normalize_result_rows(results)
    focus_results = [row for row in normalized_results if is_focus_email(row)]
    low_priority = [row for row in normalized_results if row.get("priority", "").lower() == "low"]
    archive_candidates = [
        row for row in normalized_results if row.get("review_status", "").lower() == "archive candidate"
    ]
    deletion_review = [
        row for row in normalized_results if row.get("review_status", "").lower() == "review for deletion"
    ]

    st.subheader("Action Dashboard")
    st.caption("Default view focuses on high priority, unsure, and manual-review emails first.")

    focus_tab, all_tab, low_tab, archive_tab, delete_tab = st.tabs(
        [
            f"Focus ({len(focus_results)})",
            f"All ({len(normalized_results)})",
            f"Low priority ({len(low_priority)})",
            f"Archive candidates ({len(archive_candidates)})",
            f"Review for deletion ({len(deletion_review)})",
        ]
    )

    with focus_tab:
        render_email_table("High priority / Unsure / Needs manual review", focus_results, "focus")
    with all_tab:
        render_email_table("All unread emails in this run", normalized_results, "all")
    with low_tab:
        render_email_table("Low priority", low_priority, "low")
    with archive_tab:
        render_email_table("Archive candidates", archive_candidates, "archive")
    with delete_tab:
        render_email_table("Review for deletion", deletion_review, "delete")

    excel_bytes = create_excel_bytes(normalized_results)
    st.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name="email_triage_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
