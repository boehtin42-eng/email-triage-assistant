from datetime import date, timedelta
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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


def is_no_reply_email(row: dict[str, str]) -> bool:
    text = f"{row.get('from_name', '')} {row.get('from_email', '')}".lower()
    return any(marker in text for marker in ["no-reply", "noreply", "donotreply", "do-not-reply"])


def is_newsletter_email(row: dict[str, str]) -> bool:
    text = " ".join(
        [
            row.get("from_name", ""),
            row.get("from_email", ""),
            row.get("subject", ""),
            row.get("category", ""),
            row.get("reason", ""),
        ]
    ).lower()
    markers = [
        "newsletter",
        "digest",
        "webinar",
        "promotion",
        "marketing",
        "unsubscribe",
        "sale",
        "offer",
        "notification",
        "linkedin",
        "manychat",
    ]
    return any(marker in text for marker in markers)


def matches_search(row: dict[str, str], query: str) -> bool:
    if not query:
        return True
    searchable = " ".join(str(row.get(column, "")) for column in TABLE_COLUMNS).lower()
    return query.lower() in searchable


def apply_quick_filters(
    rows: list[dict[str, str]],
    show_high_unsure_only: bool,
    hide_newsletters: bool,
    hide_no_reply: bool,
    search_query: str,
) -> list[dict[str, str]]:
    filtered = []
    for row in rows:
        if show_high_unsure_only and row.get("priority", "").lower() not in {"high", "unsure"}:
            continue
        if hide_newsletters and is_newsletter_email(row):
            continue
        if hide_no_reply and is_no_reply_email(row):
            continue
        if not matches_search(row, search_query):
            continue
        filtered.append(row)
    return filtered


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
    draft = selected.get("german_reply_draft", "")
    st.text_area(
        "German Reply Draft",
        value=draft,
        height=220,
        key=f"{key_prefix}_draft_text",
    )
    render_copy_button(draft, f"{key_prefix}_copy_button")


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
            Copy German Draft
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

    st.header("Quick Filters")
    show_high_unsure_only = st.checkbox("Show only High / Unsure")
    hide_newsletters = st.checkbox("Hide newsletters / marketing")
    hide_no_reply = st.checkbox("Hide no-reply emails")
    search_query = st.text_input("Search keyword", placeholder="sender, subject, category...")

    st.header("Optional Date Filter")
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
        if ok:
            st.success(message)
        else:
            st.error(message)

with col2:
    if st.button("Test Gemini"):
        ok, message = test_gemini_connection()
        if ok:
            st.success(message)
        else:
            st.error(message)


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
    filtered_results = apply_quick_filters(
        normalized_results,
        show_high_unsure_only=show_high_unsure_only,
        hide_newsletters=hide_newsletters,
        hide_no_reply=hide_no_reply,
        search_query=search_query,
    )
    focus_results = [row for row in filtered_results if is_focus_email(row)]
    low_priority = [row for row in filtered_results if row.get("priority", "").lower() == "low"]
    archive_candidates = [
        row for row in filtered_results if row.get("review_status", "").lower() == "archive candidate"
    ]
    deletion_review = [
        row for row in filtered_results if row.get("review_status", "").lower() == "review for deletion"
    ]

    st.subheader("Action Dashboard")
    st.caption("Default view focuses on high priority, unsure, and manual-review emails first.")

    focus_tab, all_tab, low_tab, archive_tab, delete_tab = st.tabs(
        [
            f"Focus ({len(focus_results)})",
            f"All ({len(filtered_results)})",
            f"Low priority ({len(low_priority)})",
            f"Archive candidates ({len(archive_candidates)})",
            f"Review for deletion ({len(deletion_review)})",
        ]
    )

    with focus_tab:
        render_email_table("High priority / Unsure / Needs manual review", focus_results, "focus")
    with all_tab:
        render_email_table("All unread emails matching current filters", filtered_results, "all")
    with low_tab:
        render_email_table("Low priority", low_priority, "low")
    with archive_tab:
        render_email_table("Archive candidates", archive_candidates, "archive")
    with delete_tab:
        render_email_table("Review for deletion", deletion_review, "delete")

    excel_bytes = create_excel_bytes(filtered_results)
    st.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name="email_triage_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
