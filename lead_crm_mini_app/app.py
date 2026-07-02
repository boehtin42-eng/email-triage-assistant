import json
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials


DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "leads.csv"

STATUSES = ["New", "Contacted", "Interested", "Quoted", "Won", "Lost", "Follow-up later"]
SOURCES = ["Facebook", "Website", "Referral", "WhatsApp", "Instagram", "Email", "Walk-in", "Other"]
LEAD_COLUMNS = [
    "id",
    "created_at",
    "name",
    "phone",
    "email",
    "source",
    "interest",
    "status",
    "follow_up_date",
    "next_action",
    "notes",
]
DISPLAY_COLUMNS = [
    "created_at",
    "name",
    "phone",
    "email",
    "source",
    "interest",
    "status",
    "follow_up_date",
    "next_action",
    "notes",
]
UPDATE_COLUMNS = [column for column in LEAD_COLUMNS if column != "id"]
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


st.set_page_config(page_title="Lead CRM Mini App", layout="wide")


def get_secret(name: str) -> Optional[str]:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value) if value else None


def google_sheets_enabled() -> bool:
    return bool(get_secret("GOOGLE_SHEET_ID") and get_secret("GOOGLE_SERVICE_ACCOUNT_JSON"))


@st.cache_resource
def get_google_worksheet():
    sheet_id = get_secret("GOOGLE_SHEET_ID")
    service_account_json = get_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not sheet_id or not service_account_json:
        raise RuntimeError("Google Sheets secrets are missing.")

    service_account_info = json.loads(service_account_json)
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=GOOGLE_SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet("Leads")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Leads", rows=1000, cols=len(LEAD_COLUMNS))

    first_row = worksheet.row_values(1)
    if first_row != LEAD_COLUMNS:
        worksheet.clear()
        worksheet.append_row(LEAD_COLUMNS)
    return worksheet


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        pd.DataFrame(columns=LEAD_COLUMNS).to_csv(DATA_FILE, index=False)


def load_leads() -> pd.DataFrame:
    if google_sheets_enabled():
        worksheet = get_google_worksheet()
        rows = worksheet.get_all_records()
        dataframe = pd.DataFrame(rows, dtype=str)
        if dataframe.empty:
            dataframe = pd.DataFrame(columns=LEAD_COLUMNS)
        dataframe = dataframe.fillna("")
        for column in LEAD_COLUMNS:
            if column not in dataframe.columns:
                dataframe[column] = ""
        return dataframe[LEAD_COLUMNS]

    ensure_data_file()
    dataframe = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    for column in LEAD_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe[LEAD_COLUMNS]


def save_leads(dataframe: pd.DataFrame) -> None:
    dataframe = dataframe.copy()
    for column in LEAD_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe = dataframe[LEAD_COLUMNS].fillna("")
    if google_sheets_enabled():
        worksheet = get_google_worksheet()
        worksheet.clear()
        values = [LEAD_COLUMNS] + dataframe.values.tolist()
        worksheet.update(values)
        return

    ensure_data_file()
    dataframe.to_csv(DATA_FILE, index=False)


def add_lead(lead: Dict[str, str]) -> None:
    dataframe = load_leads()
    row = {
        "id": str(uuid4()),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        **lead,
    }
    dataframe = pd.concat([pd.DataFrame([row]), dataframe], ignore_index=True)
    save_leads(dataframe)


def parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def lead_bucket(row: pd.Series) -> str:
    follow_up = parse_date(str(row.get("follow_up_date", "")))
    status = str(row.get("status", ""))
    today = date.today()
    if status in {"Won", "Lost"}:
        return status
    if follow_up and follow_up < today:
        return "Overdue"
    if follow_up == today:
        return "Due today"
    if status == "New":
        return "New"
    return "Active"


def apply_filters(
    dataframe: pd.DataFrame,
    search_query: str,
    status_filter: List[str],
    source_filter: List[str],
    follow_up_view: str,
) -> pd.DataFrame:
    filtered = dataframe.copy()

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    if source_filter:
        filtered = filtered[filtered["source"].isin(source_filter)]

    if search_query.strip():
        query = search_query.strip().lower()
        searchable = filtered[DISPLAY_COLUMNS].astype(str).agg(" ".join, axis=1).str.lower()
        filtered = filtered[searchable.str.contains(query, regex=False)]

    if follow_up_view != "All":
        buckets = filtered.apply(lead_bucket, axis=1)
        filtered = filtered[buckets == follow_up_view]

    return filtered


def dataframe_to_excel(dataframe: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Leads")
    return output.getvalue()


def render_metrics(dataframe: pd.DataFrame) -> None:
    buckets = dataframe.apply(lead_bucket, axis=1) if not dataframe.empty else pd.Series(dtype=str)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total leads", len(dataframe))
    col2.metric("New", int((dataframe["status"] == "New").sum()) if not dataframe.empty else 0)
    col3.metric("Due today", int((buckets == "Due today").sum()))
    col4.metric("Overdue", int((buckets == "Overdue").sum()))
    col5.metric("Won", int((dataframe["status"] == "Won").sum()) if not dataframe.empty else 0)


def render_add_lead_form() -> None:
    with st.form("add_lead_form", clear_on_submit=True):
        st.subheader("Add Lead")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            source = st.selectbox("Source", SOURCES)
        with col2:
            interest = st.text_input("Interested product/service")
            status = st.selectbox("Status", STATUSES)
            follow_up_date = st.date_input("Follow-up date", value=date.today())
            next_action = st.text_input("Next action", placeholder="Call, send quote, follow up...")

        notes = st.text_area("Notes", height=100)
        submitted = st.form_submit_button("Add lead", type="primary")

    if submitted:
        if not name.strip() and not phone.strip() and not email.strip():
            st.error("Please add at least a name, phone, or email.")
            return

        add_lead(
            {
                "name": name.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "source": source,
                "interest": interest.strip(),
                "status": status,
                "follow_up_date": follow_up_date.strftime("%Y-%m-%d"),
                "next_action": next_action.strip(),
                "notes": notes.strip(),
            }
        )
        st.success("Lead added.")
        st.rerun()


def render_editable_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Lead Table")
    if dataframe.empty:
        st.info("No leads found.")
        return dataframe

    edited = st.data_editor(
        dataframe,
        hide_index=True,
        use_container_width=True,
        column_order=DISPLAY_COLUMNS,
        disabled=["created_at"],
        column_config={
            "created_at": st.column_config.TextColumn("Created"),
            "name": st.column_config.TextColumn("Name"),
            "phone": st.column_config.TextColumn("Phone"),
            "email": st.column_config.TextColumn("Email"),
            "source": st.column_config.SelectboxColumn("Source", options=SOURCES),
            "interest": st.column_config.TextColumn("Interest"),
            "status": st.column_config.SelectboxColumn("Status", options=STATUSES),
            "follow_up_date": st.column_config.TextColumn("Follow-up date"),
            "next_action": st.column_config.TextColumn("Next action"),
            "notes": st.column_config.TextColumn("Notes"),
        },
        key="lead_editor",
    )
    return edited


st.title("Lead CRM Mini App")
st.caption("Track leads, follow-ups, next actions, notes, and export to Excel.")

leads = load_leads()
render_metrics(leads)

with st.sidebar:
    st.header("Filters")
    search_query = st.text_input("Search", placeholder="name, phone, email, note...")
    status_filter = st.multiselect("Status", STATUSES)
    source_filter = st.multiselect("Source", SOURCES)
    follow_up_view = st.selectbox(
        "Follow-up view",
        ["All", "Due today", "Overdue", "New", "Active", "Won", "Lost"],
    )

    st.header("Export")
    filtered_preview = apply_filters(leads, search_query, status_filter, source_filter, follow_up_view)
    st.download_button(
        "Download Excel",
        data=dataframe_to_excel(filtered_preview[DISPLAY_COLUMNS]),
        file_name="leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Download CSV",
        data=filtered_preview[DISPLAY_COLUMNS].to_csv(index=False).encode("utf-8"),
        file_name="leads.csv",
        mime="text/csv",
    )

tab_dashboard, tab_add = st.tabs(["Dashboard", "Add lead"])

with tab_add:
    render_add_lead_form()

with tab_dashboard:
    filtered = apply_filters(leads, search_query, status_filter, source_filter, follow_up_view)
    due_today = filtered[filtered.apply(lead_bucket, axis=1) == "Due today"] if not filtered.empty else filtered
    overdue = filtered[filtered.apply(lead_bucket, axis=1) == "Overdue"] if not filtered.empty else filtered

    if not overdue.empty:
        st.error(f"{len(overdue)} overdue follow-up(s).")
        st.dataframe(overdue[DISPLAY_COLUMNS], use_container_width=True, hide_index=True)

    if not due_today.empty:
        st.warning(f"{len(due_today)} follow-up(s) due today.")
        st.dataframe(due_today[DISPLAY_COLUMNS], use_container_width=True, hide_index=True)

    edited_table = render_editable_table(filtered)
    if st.button("Save table changes", type="primary"):
        if filtered.empty:
            st.info("No changes to save.")
        else:
            all_leads = load_leads()
            all_leads = all_leads.set_index("id")
            edited_table = edited_table.set_index("id")
            for lead_id, row in edited_table.iterrows():
                all_leads.loc[lead_id, UPDATE_COLUMNS] = row[UPDATE_COLUMNS]
            save_leads(all_leads.reset_index())
            st.success("Changes saved.")
            st.rerun()
