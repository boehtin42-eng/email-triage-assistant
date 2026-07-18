from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_FILE = DATA_DIR / "projects.csv"

PROJECT_COLUMNS = [
    "id",
    "created_at",
    "project_name",
    "customer",
    "assigned_person",
    "status",
    "priority",
    "start_date",
    "deadline",
    "next_action",
    "last_update",
    "notes",
]

DISPLAY_COLUMNS = [
    "project_name",
    "customer",
    "assigned_person",
    "status",
    "priority",
    "deadline",
    "days_left",
    "deadline_state",
    "next_action",
    "last_update",
    "notes",
]

STATUSES = ["Not started", "In progress", "Waiting", "Blocked", "Completed", "Cancelled"]
PRIORITIES = ["High", "Medium", "Low"]
DEADLINE_VIEWS = ["All", "Overdue", "Due today", "Due this week", "No deadline"]


st.set_page_config(page_title="Job / Project Tracker", layout="wide")

if "deadline_view" not in st.session_state:
    st.session_state["deadline_view"] = "All"
if "status_filter" not in st.session_state:
    st.session_state["status_filter"] = []


def set_quick_filter(deadline_value: str = "All", statuses: Optional[List[str]] = None) -> None:
    st.session_state["deadline_view"] = deadline_value
    st.session_state["status_filter"] = statuses or []


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        pd.DataFrame(columns=PROJECT_COLUMNS).to_csv(DATA_FILE, index=False)


def normalize_projects(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe.columns = [str(column).strip().lower().replace(" ", "_") for column in dataframe.columns]

    aliases = {
        "name": "project_name",
        "project": "project_name",
        "client": "customer",
        "owner": "assigned_person",
        "assignee": "assigned_person",
        "person": "assigned_person",
        "due_date": "deadline",
        "due": "deadline",
        "action": "next_action",
        "next_step": "next_action",
        "comment": "notes",
    }
    dataframe = dataframe.rename(columns={key: value for key, value in aliases.items() if key in dataframe.columns})

    for column in PROJECT_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe = dataframe[PROJECT_COLUMNS].fillna("")
    dataframe["id"] = dataframe["id"].replace("", pd.NA)
    dataframe["id"] = dataframe["id"].fillna(pd.Series([str(uuid4()) for _ in range(len(dataframe))]))
    dataframe["created_at"] = dataframe["created_at"].replace("", datetime.now().strftime("%Y-%m-%d %H:%M"))
    dataframe["status"] = dataframe["status"].replace("", "Not started")
    dataframe["priority"] = dataframe["priority"].replace("", "Medium")
    return dataframe.fillna("")


def load_projects() -> pd.DataFrame:
    ensure_data_file()
    dataframe = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    return normalize_projects(dataframe)


def save_projects(dataframe: pd.DataFrame) -> None:
    ensure_data_file()
    normalize_projects(dataframe).to_csv(DATA_FILE, index=False)


def clear_projects() -> None:
    save_projects(pd.DataFrame(columns=PROJECT_COLUMNS))


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def days_left(value: str) -> str:
    deadline = parse_date(value)
    if not deadline:
        return ""
    return str((deadline - date.today()).days)


def deadline_state(value: str, status: str) -> str:
    if status in {"Completed", "Cancelled"}:
        return status

    deadline = parse_date(value)
    if not deadline:
        return "No deadline"

    today = date.today()
    if deadline < today:
        return "Overdue"
    if deadline == today:
        return "Due today"
    if deadline <= today + timedelta(days=7):
        return "Due this week"
    return "Upcoming"


def enrich_projects(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = normalize_projects(dataframe)
    dataframe["days_left"] = dataframe["deadline"].apply(days_left)
    dataframe["deadline_state"] = dataframe.apply(
        lambda row: deadline_state(str(row["deadline"]), str(row["status"])),
        axis=1,
    )
    return dataframe


def apply_filters(
    dataframe: pd.DataFrame,
    search_query: str,
    status_filter: List[str],
    priority_filter: List[str],
    deadline_view: str,
) -> pd.DataFrame:
    filtered = dataframe.copy()

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    if priority_filter:
        filtered = filtered[filtered["priority"].isin(priority_filter)]

    if deadline_view != "All":
        filtered = filtered[filtered["deadline_state"] == deadline_view]

    if search_query.strip():
        query = search_query.strip().lower()
        searchable = filtered[DISPLAY_COLUMNS].astype(str).agg(" ".join, axis=1).str.lower()
        filtered = filtered[searchable.str.contains(query, regex=False)]

    state_order = {"Overdue": 0, "Due today": 1, "Due this week": 2, "Blocked": 3}
    priority_order = {"High": 0, "Medium": 1, "Low": 2}
    filtered = filtered.copy()
    filtered["_state_order"] = filtered["deadline_state"].map(state_order).fillna(9)
    filtered["_priority_order"] = filtered["priority"].map(priority_order).fillna(9)
    return filtered.sort_values(["_state_order", "_priority_order", "deadline"]).drop(
        columns=["_state_order", "_priority_order"],
        errors="ignore",
    )


def dataframe_to_excel(dataframe: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Projects")
    return output.getvalue()


def reminder_recipients(row: pd.Series) -> str:
    assigned = str(row.get("assigned_person", "")).strip()
    customer = str(row.get("customer", "")).strip()
    if assigned and customer:
        return f"{assigned} / {customer}"
    return assigned or customer or "Team"


def reminder_subject(row: pd.Series) -> str:
    state = str(row.get("deadline_state", ""))
    project = str(row.get("project_name", "Project"))
    if state == "Overdue":
        return f"Reminder: {project} is overdue"
    if state == "Due today":
        return f"Reminder: {project} is due today"
    if state == "Due this week":
        return f"Reminder: {project} is due this week"
    if str(row.get("status", "")) == "Blocked":
        return f"Reminder: {project} is blocked"
    return f"Reminder: {project} needs follow-up"


def reminder_message(row: pd.Series, tone: str) -> str:
    project = str(row.get("project_name", "the project"))
    customer = str(row.get("customer", ""))
    assigned = str(row.get("assigned_person", ""))
    state = str(row.get("deadline_state", ""))
    deadline = str(row.get("deadline", ""))
    next_action = str(row.get("next_action", "")).strip() or "Please confirm the next action."
    notes = str(row.get("notes", "")).strip()

    greeting = "Hi"
    if tone == "Direct":
        opening = f"Quick reminder about {project}."
    elif tone == "Polite":
        opening = f"I wanted to gently follow up on {project}."
    else:
        opening = f"Just a friendly reminder about {project}."

    lines = [
        f"{greeting} {assigned or 'team'},",
        "",
        opening,
    ]
    if customer:
        lines.append(f"Customer: {customer}")
    if deadline:
        lines.append(f"Deadline: {deadline} ({state})")
    lines.extend(["", f"Next action: {next_action}"])
    if notes:
        lines.extend(["", f"Notes: {notes}"])
    lines.extend(["", "Please update the project status when this is handled."])
    return "\n".join(lines)


def build_digest(dataframe: pd.DataFrame) -> str:
    if dataframe.empty:
        return "No project reminders for today."

    lines = [f"Project reminder digest - {date.today().strftime('%Y-%m-%d')}", ""]
    for index, row in dataframe.reset_index(drop=True).iterrows():
        lines.extend(
            [
                f"{index + 1}. {row['project_name']} ({row['deadline_state']})",
                f"   Customer: {row['customer'] or '-'}",
                f"   Assigned: {row['assigned_person'] or '-'}",
                f"   Deadline: {row['deadline'] or '-'}",
                f"   Next action: {row['next_action'] or '-'}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def sample_projects() -> pd.DataFrame:
    today = date.today()
    rows = [
        {
            "id": str(uuid4()),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_name": "Website refresh",
            "customer": "Bright Office GmbH",
            "assigned_person": "Anna",
            "status": "In progress",
            "priority": "High",
            "start_date": str(today - timedelta(days=8)),
            "deadline": str(today + timedelta(days=2)),
            "next_action": "Send homepage draft for approval",
            "last_update": str(today),
            "notes": "Customer wants a cleaner mobile layout.",
        },
        {
            "id": str(uuid4()),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_name": "Monthly cleaning contract",
            "customer": "Maria Keller",
            "assigned_person": "Oakar",
            "status": "Waiting",
            "priority": "Medium",
            "start_date": str(today - timedelta(days=3)),
            "deadline": str(today),
            "next_action": "Confirm final service schedule",
            "last_update": str(today - timedelta(days=1)),
            "notes": "Waiting for customer confirmation.",
        },
        {
            "id": str(uuid4()),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "project_name": "Invoice automation setup",
            "customer": "Keller Project Team",
            "assigned_person": "Boe Htin",
            "status": "Blocked",
            "priority": "High",
            "start_date": str(today - timedelta(days=12)),
            "deadline": str(today - timedelta(days=1)),
            "next_action": "Ask customer for invoice sample files",
            "last_update": str(today - timedelta(days=2)),
            "notes": "Blocked until sample invoices are received.",
        },
    ]
    return pd.DataFrame(rows, columns=PROJECT_COLUMNS)


def import_uploaded_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".csv"):
        return normalize_projects(pd.read_csv(uploaded_file, dtype=str).fillna(""))
    return normalize_projects(pd.read_excel(uploaded_file, dtype=str).fillna(""))


with st.sidebar:
    st.header("Project data")
    uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
    if uploaded_file and st.button("Import uploaded file"):
        save_projects(import_uploaded_file(uploaded_file))
        st.success("Uploaded projects imported.")
        st.rerun()

    if st.button("Load sample projects"):
        save_projects(sample_projects())
        st.rerun()

    if st.button("Clear all data"):
        clear_projects()
        st.rerun()

    st.header("Filters")
    search = st.text_input("Search", placeholder="project, customer, person, note...")
    deadline_view = st.selectbox("Deadline view", DEADLINE_VIEWS, key="deadline_view")
    status_filter = st.multiselect("Status", STATUSES, key="status_filter")
    priority_filter = st.multiselect("Priority", PRIORITIES)

    st.header("Export")


projects = enrich_projects(load_projects())
filtered_projects = apply_filters(projects, search, status_filter, priority_filter, deadline_view)

st.title("Job / Project Tracker")
st.caption("Track customer projects, deadlines, status, assigned people, notes, and next actions.")

open_projects = projects[~projects["status"].isin(["Completed", "Cancelled"])]
metric_cols = st.columns(6)
with metric_cols[0]:
    st.metric("Total projects", len(projects))
    st.button(
        "Show all",
        key="show_all_projects",
        on_click=set_quick_filter,
        args=("All", []),
        width="stretch",
    )
with metric_cols[1]:
    st.metric("Open", len(open_projects))
    st.button(
        "Show open",
        key="show_open_projects",
        on_click=set_quick_filter,
        args=("All", ["Not started", "In progress", "Waiting", "Blocked"]),
        width="stretch",
    )
with metric_cols[2]:
    overdue_count = int((projects["deadline_state"] == "Overdue").sum())
    st.metric("Overdue", overdue_count)
    st.button(
        f"Show overdue ({overdue_count})",
        key="show_overdue_projects",
        on_click=set_quick_filter,
        args=("Overdue", []),
        width="stretch",
    )
with metric_cols[3]:
    due_today_count = int((projects["deadline_state"] == "Due today").sum())
    st.metric("Due today", due_today_count)
    st.button(
        f"Show due today ({due_today_count})",
        key="show_due_today_projects",
        on_click=set_quick_filter,
        args=("Due today", []),
        width="stretch",
    )
with metric_cols[4]:
    due_week_count = int((projects["deadline_state"] == "Due this week").sum())
    st.metric("Due this week", due_week_count)
    st.button(
        f"Show this week ({due_week_count})",
        key="show_due_week_projects",
        on_click=set_quick_filter,
        args=("Due this week", []),
        width="stretch",
    )
with metric_cols[5]:
    blocked_count = int((projects["status"] == "Blocked").sum())
    st.metric("Blocked", blocked_count)
    st.button(
        f"Show blocked ({blocked_count})",
        key="show_blocked_projects",
        on_click=set_quick_filter,
        args=("All", ["Blocked"]),
        width="stretch",
    )

active_status = ", ".join(status_filter) if status_filter else "All"
st.info(f"Showing {len(filtered_projects)} project(s). Deadline view: {deadline_view}. Status: {active_status}.")

tab_action, tab_reminders, tab_all, tab_add = st.tabs(
    ["Action dashboard", "Reminders", "All projects", "Add project"]
)

with tab_action:
    st.subheader("Projects needing attention")
    attention = filtered_projects[
        filtered_projects["deadline_state"].isin(["Overdue", "Due today", "Due this week"])
        | filtered_projects["status"].isin(["Blocked", "Waiting"])
        | filtered_projects["priority"].eq("High")
    ]
    if attention.empty:
        st.info("No urgent projects found.")
    else:
        st.dataframe(attention[DISPLAY_COLUMNS], width="stretch", hide_index=True)

    st.download_button(
        "Download action list Excel",
        data=dataframe_to_excel(attention[DISPLAY_COLUMNS]),
        file_name=f"project_action_list_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Next action cards")
    for _, row in attention.head(8).iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['project_name']}")
            st.caption(
                f"{row['customer']} | {row['assigned_person']} | {row['priority']} priority | "
                f"{row['deadline_state']}"
            )
            st.write(f"Next action: {row['next_action'] or 'No next action written yet.'}")
            st.write(f"Deadline: {row['deadline'] or 'No deadline'}")
            if row["notes"]:
                st.info(row["notes"])

with tab_reminders:
    st.subheader("Reminder drafts")
    reminder_candidates = filtered_projects[
        filtered_projects["deadline_state"].isin(["Overdue", "Due today", "Due this week"])
        | filtered_projects["status"].isin(["Blocked", "Waiting"])
    ]

    col1, col2 = st.columns(2)
    tone = col1.selectbox("Reminder tone", ["Friendly", "Polite", "Direct"])
    recipient_view = col2.selectbox("View", ["All reminder candidates", "Overdue only", "Blocked only"])

    if recipient_view == "Overdue only":
        reminder_candidates = reminder_candidates[reminder_candidates["deadline_state"] == "Overdue"]
    elif recipient_view == "Blocked only":
        reminder_candidates = reminder_candidates[reminder_candidates["status"] == "Blocked"]

    if reminder_candidates.empty:
        st.info("No reminder candidates found with the current filters.")
    else:
        st.dataframe(
            reminder_candidates[
                [
                    "project_name",
                    "customer",
                    "assigned_person",
                    "status",
                    "deadline",
                    "deadline_state",
                    "next_action",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

        options = reminder_candidates.index.tolist()
        selected_index = st.selectbox(
            "Choose a project for reminder draft",
            options,
            format_func=lambda index: (
                f"{reminder_candidates.loc[index, 'deadline_state']} | "
                f"{reminder_candidates.loc[index, 'project_name']} | "
                f"{reminder_recipients(reminder_candidates.loc[index])}"
            ),
        )
        selected_row = reminder_candidates.loc[selected_index]
        subject = reminder_subject(selected_row)
        message = reminder_message(selected_row, tone)

        st.text_input("Reminder subject", value=subject)
        st.text_area("Reminder message", value=message, height=260)

        digest = build_digest(reminder_candidates)
        st.download_button(
            "Download reminder digest TXT",
            data=digest.encode("utf-8"),
            file_name=f"project_reminder_digest_{date.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
        )

        st.info("This app creates reminder drafts only. It does not send messages automatically.")

with tab_all:
    st.subheader("Project table")
    editable = st.data_editor(
        filtered_projects[DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "status": st.column_config.SelectboxColumn("status", options=STATUSES),
            "priority": st.column_config.SelectboxColumn("priority", options=PRIORITIES),
            "deadline": st.column_config.TextColumn("deadline", help="Use YYYY-MM-DD"),
            "start_date": st.column_config.TextColumn("start_date", help="Use YYYY-MM-DD"),
        },
        key="project_table_editor",
    )
    if st.button("Save visible table changes"):
        original = projects.copy()
        visible_ids = filtered_projects["id"].tolist()
        edited = filtered_projects.copy()
        for column in DISPLAY_COLUMNS:
            edited[column] = editable[column].astype(str).fillna("") if column in editable else ""
        edited["id"] = visible_ids
        edited["created_at"] = filtered_projects["created_at"].tolist()
        edited["start_date"] = filtered_projects["start_date"].tolist()

        remaining = original[~original["id"].isin(visible_ids)]
        save_projects(pd.concat([edited[PROJECT_COLUMNS], remaining[PROJECT_COLUMNS]], ignore_index=True))
        st.success("Project table changes saved.")
        st.rerun()

    st.download_button(
        "Download all projects Excel",
        data=dataframe_to_excel(projects[DISPLAY_COLUMNS]),
        file_name=f"projects_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Download all projects CSV",
        data=projects[DISPLAY_COLUMNS].to_csv(index=False).encode("utf-8"),
        file_name=f"projects_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

with tab_add:
    st.subheader("Add a project")
    with st.form("add_project_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        project_name = col1.text_input("Project name")
        customer = col2.text_input("Customer")
        assigned_person = col1.text_input("Assigned person")
        status = col2.selectbox("Status", STATUSES, index=1)
        priority = col1.selectbox("Priority", PRIORITIES)
        start_date = col2.date_input("Start date", value=date.today())
        deadline = col1.date_input("Deadline", value=date.today() + timedelta(days=7))
        last_update = col2.date_input("Last update", value=date.today())
        next_action = st.text_input("Next action")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save project")
        if submitted:
            if not project_name.strip():
                st.error("Project name is required.")
            else:
                row = {
                    "id": str(uuid4()),
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "project_name": project_name.strip(),
                    "customer": customer.strip(),
                    "assigned_person": assigned_person.strip(),
                    "status": status,
                    "priority": priority,
                    "start_date": str(start_date),
                    "deadline": str(deadline),
                    "next_action": next_action.strip(),
                    "last_update": str(last_update),
                    "notes": notes.strip(),
                }
                save_projects(pd.concat([pd.DataFrame([row]), projects[PROJECT_COLUMNS]], ignore_index=True))
                st.success("Project saved.")
                st.rerun()
