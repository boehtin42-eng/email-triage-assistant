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
- Optional Google Sheets storage

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

For local CSV storage, no API key is required.

For Google Sheets storage, add Streamlit secrets:

```toml
GOOGLE_SHEET_ID = "your-google-sheet-id"
GOOGLE_SERVICE_ACCOUNT_JSON = '''
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
'''
```

Share the Google Sheet with the service account `client_email` as Editor.

Use triple single quotes (`'''`) for `GOOGLE_SERVICE_ACCOUNT_JSON`. Triple double quotes can turn `\n`
inside `private_key` into real line breaks and make the JSON invalid.

## Storage note

If Google Sheets secrets are configured, the app stores leads in the `Leads` worksheet.

If Google Sheets secrets are missing, the app falls back to `data/leads.csv`. On Streamlit Cloud, local file storage can reset when the app restarts or redeploys.
