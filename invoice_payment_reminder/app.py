import html
import re
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_FILE = DATA_DIR / "invoices.csv"
EXPENSE_FILE = DATA_DIR / "expenses.csv"

INVOICE_COLUMNS = [
    "invoice_no",
    "customer_name",
    "customer_email",
    "amount",
    "currency",
    "invoice_date",
    "due_date",
    "status",
    "last_reminder_date",
    "notes",
]

DISPLAY_COLUMNS = [
    "invoice_no",
    "customer_name",
    "customer_email",
    "amount",
    "currency",
    "invoice_date",
    "due_date",
    "status",
    "days_overdue",
    "payment_state",
    "reminder_draft",
    "notes",
]

STATUSES = ["Unpaid", "Paid", "Partially paid", "Disputed", "Cancelled"]
CURRENCIES = ["EUR", "USD", "GBP", "THB", "MMK", "Other"]
EXPENSE_COLUMNS = [
    "type_of_service",
    "vendor",
    "date",
    "amount",
    "currency",
    "paid_from",
    "invoice",
    "notes",
]
PAID_FROM_OPTIONS = ["Business bank", "Credit card", "PayPal", "Cash", "Personal account", "Other"]


st.set_page_config(page_title="Invoice & Payment Reminder Tool", layout="wide")


def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        pd.DataFrame(columns=INVOICE_COLUMNS).to_csv(DATA_FILE, index=False)
    if not EXPENSE_FILE.exists():
        pd.DataFrame(columns=EXPENSE_COLUMNS).to_csv(EXPENSE_FILE, index=False)


def normalize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe.columns = [str(column).strip().lower().replace(" ", "_") for column in dataframe.columns]

    aliases = {
        "invoice": "invoice_no",
        "invoice_number": "invoice_no",
        "client": "customer_name",
        "customer": "customer_name",
        "name": "customer_name",
        "email": "customer_email",
        "client_email": "customer_email",
        "total": "amount",
        "balance": "amount",
        "date": "invoice_date",
        "issued_date": "invoice_date",
        "payment_status": "status",
    }
    dataframe = dataframe.rename(columns={key: value for key, value in aliases.items() if key in dataframe.columns})

    for column in INVOICE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""

    dataframe = dataframe[INVOICE_COLUMNS].fillna("")
    dataframe["status"] = dataframe["status"].replace("", "Unpaid")
    dataframe["currency"] = dataframe["currency"].replace("", "EUR")
    return dataframe


def load_invoices() -> pd.DataFrame:
    ensure_data_file()
    dataframe = pd.read_csv(DATA_FILE, dtype=str).fillna("")
    return normalize_columns(dataframe)


def save_invoices(dataframe: pd.DataFrame) -> None:
    ensure_data_file()
    normalize_columns(dataframe).to_csv(DATA_FILE, index=False)


def clear_invoices() -> None:
    save_invoices(pd.DataFrame(columns=INVOICE_COLUMNS))


def load_expenses() -> pd.DataFrame:
    ensure_data_file()
    dataframe = pd.read_csv(EXPENSE_FILE, dtype=str).fillna("")
    for column in EXPENSE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""
    return dataframe[EXPENSE_COLUMNS]


def save_expenses(dataframe: pd.DataFrame) -> None:
    ensure_data_file()
    dataframe = dataframe.copy().fillna("")
    for column in EXPENSE_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = ""
    dataframe[EXPENSE_COLUMNS].to_csv(EXPENSE_FILE, index=False)


def clear_expenses() -> None:
    save_expenses(pd.DataFrame(columns=EXPENSE_COLUMNS))


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


def parse_amount(value: str) -> float:
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_invoice_amount(value: str) -> str:
    text = str(value).replace(",", "")
    matches = re.findall(r"(?:total|amount due|betrag|summe|balance)\D{0,20}(\d+(?:\.\d{2})?)", text, re.IGNORECASE)
    if matches:
        return matches[-1]
    generic_matches = re.findall(r"\b\d{1,6}\.\d{2}\b", text)
    return generic_matches[-1] if generic_matches else ""


def extract_text_from_expense_file(uploaded_file) -> str:
    file_name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()
    if file_name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def detect_currency(text: str) -> str:
    if "€" in text or re.search(r"\bEUR\b", text, re.IGNORECASE):
        return "EUR"
    if "$" in text or re.search(r"\bUSD\b", text, re.IGNORECASE):
        return "USD"
    if "£" in text or re.search(r"\bGBP\b", text, re.IGNORECASE):
        return "GBP"
    if re.search(r"\bTHB\b", text, re.IGNORECASE):
        return "THB"
    return "EUR"


def guess_vendor(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    skip_words = ("invoice", "rechnung", "receipt", "tax invoice")
    for line in lines[:8]:
        if not any(word in line.lower() for word in skip_words) and len(line) <= 80:
            return line
    return lines[0] if lines else ""


def extract_expense_fields(text: str) -> Dict[str, str]:
    clean = re.sub(r"[ \t]+", " ", text)
    invoice_no = first_match(r"(?:invoice\s*(?:no|number|#)?|rechnung\s*(?:nr|nummer)?)\s*[:#-]?\s*([A-Z0-9-]+)", clean)
    invoice_date = first_match(r"(?:invoice date|date|datum)\s*[:#-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})", clean)
    service = first_match(r"(?:service|description|leistung|item)\s*[:#-]?\s*(.+)", clean)
    paid_from = first_match(r"(?:paid from|payment method|paid by)\s*[:#-]?\s*(.+)", clean)
    amount = parse_invoice_amount(clean)

    return {
        "type_of_service": service[:120],
        "vendor": guess_vendor(clean),
        "date": invoice_date,
        "amount": amount,
        "currency": detect_currency(clean),
        "paid_from": paid_from[:80],
        "invoice": invoice_no,
        "notes": "Extracted from uploaded invoice. Please review before saving.",
    }


def format_amount(value) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def payment_state(row: pd.Series) -> str:
    status = str(row.get("status", "")).strip()
    due_date = parse_date(str(row.get("due_date", "")))
    today = date.today()

    if status == "Paid":
        return "Paid"
    if status in {"Cancelled", "Disputed"}:
        return status
    if due_date is None:
        return "Missing due date"
    if due_date < today:
        return "Overdue"
    if due_date == today:
        return "Due today"
    return "Upcoming"


def days_overdue(row: pd.Series) -> int:
    due_date = parse_date(str(row.get("due_date", "")))
    if due_date is None or payment_state(row) != "Overdue":
        return 0
    return (date.today() - due_date).days


def reminder_draft(row: pd.Series, tone: str, language: str) -> str:
    state = payment_state(row)
    customer = str(row.get("customer_name", "")).strip() or "there"
    invoice_no = str(row.get("invoice_no", "")).strip() or "your invoice"
    amount = parse_amount(str(row.get("amount", "")))
    currency = str(row.get("currency", "")).strip() or "EUR"
    due = str(row.get("due_date", "")).strip() or "the due date"
    amount_text = f"{amount:,.2f} {currency}" if amount else f"the outstanding amount in {currency}"

    if language == "German":
        if state == "Paid":
            return "Keine Zahlungserinnerung erforderlich. Diese Rechnung ist als bezahlt markiert."
        if state == "Disputed":
            return "Kein automatischer Erinnerungstext. Diese Rechnung ist strittig und sollte manuell geprüft werden."
        if state == "Cancelled":
            return "Keine Zahlungserinnerung erforderlich. Diese Rechnung wurde storniert."
        if state == "Missing due date":
            return "Bitte ergänzen Sie zuerst ein Fälligkeitsdatum, bevor eine Zahlungserinnerung gesendet wird."

        greeting = f"Sehr geehrte/r {customer},"
        if tone == "Firm":
            closing = "Bitte veranlassen Sie die Zahlung so bald wie möglich oder informieren Sie uns, falls es ein Problem gibt."
        else:
            closing = "Könnten Sie dies bitte prüfen und uns kurz mitteilen, wann die Zahlung veranlasst wird?"

        if state == "Overdue":
            delay = days_overdue(row)
            return (
                f"{greeting}\n\n"
                f"dies ist eine Erinnerung daran, dass die Rechnung {invoice_no} über {amount_text} "
                f"am {due} fällig war und nun seit {delay} Tag(en) überfällig ist.\n\n"
                f"{closing}\n\n"
                "Vielen Dank."
            )

        if state == "Due today":
            return (
                f"{greeting}\n\n"
                f"dies ist eine freundliche Erinnerung daran, dass die Rechnung {invoice_no} "
                f"über {amount_text} heute ({due}) fällig ist.\n\n"
                f"{closing}\n\n"
                "Vielen Dank."
            )

        return (
            f"{greeting}\n\n"
            f"dies ist eine freundliche Erinnerung daran, dass die Rechnung {invoice_no} "
            f"über {amount_text} am {due} fällig ist.\n\n"
            f"{closing}\n\n"
            "Vielen Dank."
        )

    if state == "Paid":
        return "No reminder needed. This invoice is marked as paid."
    if state == "Disputed":
        return "No automatic reminder draft. This invoice is disputed and should be reviewed manually."
    if state == "Cancelled":
        return "No reminder needed. This invoice is cancelled."
    if state == "Missing due date":
        return "Please add a due date before sending a payment reminder."

    if tone == "Firm":
        greeting = f"Dear {customer},"
        closing = "Please arrange payment as soon as possible or let us know if there is an issue."
    else:
        greeting = f"Hi {customer},"
        closing = "Could you please check this and let us know when payment will be arranged?"

    if state == "Overdue":
        delay = days_overdue(row)
        return (
            f"{greeting}\n\n"
            f"This is a reminder that invoice {invoice_no} for {amount_text} was due on {due} "
            f"and is now {delay} day(s) overdue.\n\n"
            f"{closing}\n\n"
            "Thank you."
        )

    if state == "Due today":
        return (
            f"{greeting}\n\n"
            f"This is a friendly reminder that invoice {invoice_no} for {amount_text} is due today ({due}).\n\n"
            f"{closing}\n\n"
            "Thank you."
        )

    return (
        f"{greeting}\n\n"
        f"This is a friendly reminder that invoice {invoice_no} for {amount_text} is due on {due}.\n\n"
        f"{closing}\n\n"
        "Thank you."
    )


def enrich_invoices(dataframe: pd.DataFrame, tone: str, language: str) -> pd.DataFrame:
    dataframe = normalize_columns(dataframe)
    dataframe["payment_state"] = dataframe.apply(payment_state, axis=1)
    dataframe["days_overdue"] = dataframe.apply(days_overdue, axis=1)
    dataframe["amount_number"] = pd.to_numeric(dataframe["amount"].apply(parse_amount), errors="coerce").fillna(0.0)
    dataframe["reminder_draft"] = dataframe.apply(lambda row: reminder_draft(row, tone, language), axis=1)
    return dataframe


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file, dtype=str).fillna("")
    return pd.read_excel(uploaded_file, dtype=str).fillna("")


def to_excel(dataframe: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Invoices")
    return output.getvalue()


def render_copy_button(text: str, label: str, key: str) -> None:
    escaped_text = html.escape(text)
    escaped_label = html.escape(label)
    components.html(
        f"""
        <textarea id="copy-source-{key}" style="position:absolute; left:-9999px;">{escaped_text}</textarea>
        <button
            onclick="
                const source = document.getElementById('copy-source-{key}');
                navigator.clipboard.writeText(source.value);
                this.innerText='Copied';
                setTimeout(() => this.innerText='{escaped_label}', 1200);
            "
            style="
                background:#ff4b4b;
                color:white;
                border:0;
                border-radius:8px;
                padding:10px 14px;
                font-weight:700;
                cursor:pointer;
            "
        >
            {escaped_label}
        </button>
        """,
        height=48,
    )


def apply_filters(
    dataframe: pd.DataFrame,
    search_query: str,
    state_filter: List[str],
    status_filter: List[str],
) -> pd.DataFrame:
    filtered = dataframe.copy()

    if search_query:
        query = search_query.lower()
        searchable_columns = ["invoice_no", "customer_name", "customer_email", "notes"]
        mask = filtered[searchable_columns].astype(str).apply(
            lambda column: column.str.lower().str.contains(query, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    if state_filter:
        filtered = filtered[filtered["payment_state"].isin(state_filter)]

    if status_filter:
        filtered = filtered[filtered["status"].isin(status_filter)]

    return filtered


def build_sample_data() -> pd.DataFrame:
    today = date.today()
    rows = [
        {
            "invoice_no": "INV-1001",
            "customer_name": "Maria Keller",
            "customer_email": "maria@example.com",
            "amount": "850",
            "currency": "EUR",
            "invoice_date": today.replace(day=1).isoformat(),
            "due_date": today.isoformat(),
            "status": "Unpaid",
            "last_reminder_date": "",
            "notes": "Monthly cleaning service",
        },
        {
            "invoice_no": "INV-1002",
            "customer_name": "Bright Office GmbH",
            "customer_email": "accounts@example.com",
            "amount": "1250",
            "currency": "EUR",
            "invoice_date": today.replace(day=1).isoformat(),
            "due_date": "2026-07-01",
            "status": "Unpaid",
            "last_reminder_date": "",
            "notes": "Overdue test invoice",
        },
        {
            "invoice_no": "INV-1003",
            "customer_name": "Oakar Studio",
            "customer_email": "paid@example.com",
            "amount": "420",
            "currency": "EUR",
            "invoice_date": today.isoformat(),
            "due_date": today.isoformat(),
            "status": "Paid",
            "last_reminder_date": "",
            "notes": "Paid example",
        },
    ]
    return pd.DataFrame(rows, columns=INVOICE_COLUMNS)


with st.sidebar:
    st.header("Upload invoices")
    uploaded_file = st.file_uploader("CSV or Excel", type=["csv", "xlsx", "xls"])

    if uploaded_file:
        if st.button("Import uploaded file", type="primary"):
            uploaded_dataframe = normalize_columns(read_uploaded_file(uploaded_file))
            save_invoices(uploaded_dataframe)
            st.success("Uploaded invoices imported.")
            st.rerun()

    if st.button("Load sample invoices"):
        save_invoices(build_sample_data())
        st.success("Sample invoices loaded.")
        st.rerun()

    if st.button("Clear all data"):
        clear_invoices()
        st.success("All invoice data cleared.")
        st.rerun()

    st.header("Filters")
    search_query = st.text_input("Search", placeholder="invoice, customer, email...")
    state_filter = st.multiselect(
        "Payment state",
        ["Overdue", "Due today", "Upcoming", "Missing due date", "Paid", "Disputed", "Cancelled"],
        default=["Overdue", "Due today"],
    )
    status_filter = st.multiselect("Status", STATUSES)
    tone = st.selectbox("Reminder tone", ["Friendly", "Firm"], index=0)
    reminder_language = st.selectbox("Reminder language", ["English", "German"], index=0)

    st.header("Export")


st.title("Invoice & Payment Reminder Tool")
st.caption("Upload invoices, track due dates, find overdue payments, and create reminder drafts.")

invoices = load_invoices()
enriched = enrich_invoices(invoices, tone, reminder_language)

total_unpaid = enriched[enriched["status"].isin(["Unpaid", "Partially paid"])]["amount_number"].sum()
overdue_amount = enriched[enriched["payment_state"] == "Overdue"]["amount_number"].sum()

metric_cols = st.columns(5)
metric_cols[0].metric("Total invoices", len(enriched))
metric_cols[1].metric("Overdue", int((enriched["payment_state"] == "Overdue").sum()))
metric_cols[2].metric("Due today", int((enriched["payment_state"] == "Due today").sum()))
metric_cols[3].metric("Unpaid amount", format_amount(total_unpaid))
metric_cols[4].metric("Overdue amount", format_amount(overdue_amount))

tab_focus, tab_all, tab_add, tab_extract, tab_expenses = st.tabs(
    ["Action dashboard", "All invoices", "Add invoice", "Expense extractor", "Expenses"]
)

filtered = apply_filters(enriched, search_query, state_filter, status_filter)

with tab_focus:
    st.subheader("Invoices needing attention")
    action_rows = filtered[filtered["payment_state"].isin(["Overdue", "Due today", "Missing due date"])]
    if action_rows.empty:
        st.info("No urgent invoices found.")
    else:
        edited_action_rows = st.data_editor(
            action_rows[DISPLAY_COLUMNS],
            use_container_width=True,
            hide_index=True,
            disabled=["days_overdue", "payment_state", "reminder_draft"],
            key="action_invoice_editor",
        )
        st.download_button(
            "Download action list Excel",
            data=to_excel(edited_action_rows),
            file_name="invoice_action_list.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.subheader("Reminder drafts")
        for _, row in action_rows.iterrows():
            with st.expander(f"{row['invoice_no']} - {row['customer_name']} - {row['payment_state']}"):
                st.text_area("Draft", row["reminder_draft"], height=180, key=f"draft_{row['invoice_no']}")
                render_copy_button(row["reminder_draft"], "Copy reminder draft", f"copy_{row['invoice_no']}")
                st.caption("Copy this draft and send it manually after review.")

with tab_all:
    st.subheader("All invoice records")
    edited = st.data_editor(
        filtered[DISPLAY_COLUMNS],
        use_container_width=True,
        hide_index=True,
        disabled=["days_overdue", "payment_state", "reminder_draft"],
        key="all_invoice_editor",
    )

    if st.button("Save visible table changes"):
        editable = edited.drop(columns=["days_overdue", "payment_state", "reminder_draft"], errors="ignore")
        existing = load_invoices()
        for _, changed_row in editable.iterrows():
            invoice_no = str(changed_row.get("invoice_no", ""))
            if not invoice_no:
                continue
            mask = existing["invoice_no"] == invoice_no
            if mask.any():
                for column in INVOICE_COLUMNS:
                    if column in changed_row:
                        existing.loc[mask, column] = changed_row.get(column, "")
        save_invoices(existing)
        st.success("Invoice changes saved.")
        st.rerun()

    st.download_button(
        "Download Excel",
        data=to_excel(enriched[DISPLAY_COLUMNS]),
        file_name="invoice_payment_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button(
        "Download CSV",
        data=enriched[DISPLAY_COLUMNS].to_csv(index=False).encode("utf-8"),
        file_name="invoice_payment_dashboard.csv",
        mime="text/csv",
    )

with tab_add:
    st.subheader("Add invoice")
    with st.form("add_invoice_form"):
        col1, col2 = st.columns(2)
        with col1:
            invoice_no = st.text_input("Invoice number")
            customer_name = st.text_input("Customer name")
            customer_email = st.text_input("Customer email")
            amount = st.number_input("Amount", min_value=0.0, step=10.0)
            currency = st.selectbox("Currency", CURRENCIES)
        with col2:
            invoice_date = st.date_input("Invoice date", value=date.today())
            due_date = st.date_input("Due date", value=date.today())
            status = st.selectbox("Status", STATUSES)
            last_reminder_date = st.date_input("Last reminder date", value=None)
            notes = st.text_area("Notes")

        submitted = st.form_submit_button("Add invoice", type="primary")

    if submitted:
        new_row: Dict[str, str] = {
            "invoice_no": invoice_no.strip(),
            "customer_name": customer_name.strip(),
            "customer_email": customer_email.strip(),
            "amount": str(amount),
            "currency": currency,
            "invoice_date": invoice_date.isoformat(),
            "due_date": due_date.isoformat(),
            "status": status,
            "last_reminder_date": last_reminder_date.isoformat() if last_reminder_date else "",
            "notes": notes.strip(),
        }

        if not new_row["invoice_no"] or not new_row["customer_name"]:
            st.error("Invoice number and customer name are required.")
        else:
            current = load_invoices()
            current = pd.concat([pd.DataFrame([new_row]), current], ignore_index=True)
            save_invoices(current)
            st.success("Invoice added.")
            st.rerun()

with tab_extract:
    st.subheader("Upload business expense invoice")
    st.caption("Upload a PDF or TXT invoice. The app extracts likely fields, then you review and save them.")
    expense_file = st.file_uploader("Expense invoice PDF or TXT", type=["pdf", "txt"], key="expense_invoice_upload")

    extracted = {
        "type_of_service": "",
        "vendor": "",
        "date": "",
        "amount": "",
        "currency": "EUR",
        "paid_from": "",
        "invoice": "",
        "notes": "",
    }

    if expense_file:
        try:
            extracted_text = extract_text_from_expense_file(expense_file)
            extracted.update(extract_expense_fields(extracted_text))
            with st.expander("Extracted raw text preview"):
                st.text_area("Raw text", extracted_text[:5000], height=220, disabled=True)
        except Exception as exc:
            st.error(f"Could not extract text from this file: {exc}")

    with st.form("expense_extract_form"):
        col1, col2 = st.columns(2)
        with col1:
            type_of_service = st.text_input("Type of service", value=extracted["type_of_service"])
            vendor = st.text_input("Vendor", value=extracted["vendor"])
            expense_date = st.text_input("Date", value=extracted["date"], placeholder="YYYY-MM-DD")
            amount = st.text_input("Amount", value=extracted["amount"])
        with col2:
            currency = st.selectbox(
                "Currency",
                CURRENCIES,
                index=CURRENCIES.index(extracted["currency"]) if extracted["currency"] in CURRENCIES else 0,
            )
            paid_from = st.selectbox(
                "Paid From",
                PAID_FROM_OPTIONS,
                index=PAID_FROM_OPTIONS.index(extracted["paid_from"])
                if extracted["paid_from"] in PAID_FROM_OPTIONS
                else 0,
            )
            invoice = st.text_input("Invoice", value=extracted["invoice"])
            notes = st.text_area("Notes", value=extracted["notes"])

        save_expense = st.form_submit_button("Save expense", type="primary")

    if save_expense:
        if not vendor or not amount:
            st.error("Vendor and amount are required before saving.")
        else:
            expenses = load_expenses()
            row = {
                "type_of_service": type_of_service.strip(),
                "vendor": vendor.strip(),
                "date": expense_date.strip(),
                "amount": amount.strip(),
                "currency": currency,
                "paid_from": paid_from,
                "invoice": invoice.strip(),
                "notes": notes.strip(),
            }
            expenses = pd.concat([pd.DataFrame([row]), expenses], ignore_index=True)
            save_expenses(expenses)
            st.success("Expense saved.")
            st.rerun()

with tab_expenses:
    st.subheader("Business expenses")
    expenses = load_expenses()
    if expenses.empty:
        st.info("No expenses saved yet.")
    else:
        edited_expenses = st.data_editor(expenses, use_container_width=True, hide_index=True, key="expense_editor")
        if st.button("Save expense table changes"):
            save_expenses(edited_expenses)
            st.success("Expense changes saved.")
            st.rerun()

        st.download_button(
            "Download expenses Excel",
            data=to_excel(edited_expenses),
            file_name="business_expenses.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            "Download expenses CSV",
            data=edited_expenses.to_csv(index=False).encode("utf-8"),
            file_name="business_expenses.csv",
            mime="text/csv",
        )

    if st.button("Clear expenses"):
        clear_expenses()
        st.success("All expenses cleared.")
        st.rerun()
