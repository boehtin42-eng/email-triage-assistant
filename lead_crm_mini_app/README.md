# Lead CRM Mini App

Simple Streamlit CRM for tracking leads, follow-ups, next actions, notes, and exports.

## Features

- Add leads
- Track status
- Track follow-up date
- Track next action
- Notes
- Search and filters
- Due today and overdue dashboard
- Editable lead table
- Excel and CSV export

## Local run

```bash
cd lead_crm_mini_app
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

Use:

```text
Main file path: lead_crm_mini_app/app.py
```

No API key is required for this MVP.

## Storage note

This MVP stores data in `data/leads.csv`. On Streamlit Cloud, local file storage can reset when the app restarts or redeploys. For production use, connect Google Sheets, Airtable, Supabase, or another database.
