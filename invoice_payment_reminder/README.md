# Invoice & Payment Reminder Tool

Small business invoice dashboard for checking unpaid, due today, and overdue invoices.

## What it does

- Upload CSV or Excel invoice lists
- Track paid, unpaid, partially paid, disputed, and cancelled invoices
- Detect overdue and due-today invoices
- Create manual payment reminder drafts
- Upload a PDF or TXT expense invoice and extract likely expense fields
- Save extracted business expenses for review and export
- Show paid/unpaid dashboard metrics
- Export action lists to Excel or CSV

## Required invoice columns

The app works best with these columns:

- invoice_no
- customer_name
- customer_email
- amount
- currency
- invoice_date
- due_date
- status
- last_reminder_date
- notes

Common alternatives like `invoice_number`, `customer`, `email`, `total`, and `payment_status` are also accepted.

## Run locally

```bash
streamlit run invoice_payment_reminder/app.py
```

## Safety note

The app does not send payment reminders automatically. It only creates drafts for manual review and copy/paste use.
Expense extraction is a helper, not an accounting approval step. Always review extracted fields before saving.
