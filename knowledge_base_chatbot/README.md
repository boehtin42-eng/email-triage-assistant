# Internal Knowledge Base Chatbot

Upload company documents or connect a Google Drive folder and ask questions. The app searches the selected documents and answers from the matching source snippets.

## Features

- Upload PDF, DOCX, TXT, MD, CSV, XLSX files
- Optional Google Drive folder source
- Supports Google Docs, Google Sheets, and Google Slides export from Drive
- Search uploaded documents during the current session
- Ask questions
- Optional Gemini answer generation
- Source snippets shown for review
- Answer language selector: Burmese, English, German
- Copy answer button
- Session chat history

## Local run

```bash
cd knowledge_base_chatbot
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Use this main file path:

```text
knowledge_base_chatbot/app.py
```

Optional secret:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-2.5-flash"
```

If `GEMINI_API_KEY` is missing, the app still works as a document search tool and shows relevant source snippets.

Optional Google Drive folder secrets:

```toml
GOOGLE_DRIVE_FOLDER_ID = "your-google-drive-folder-id"

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
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
'''
```

Share the Google Drive folder with the service account `client_email` as Viewer.

Use triple single quotes (`'''`) for `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Safety note

The bot should answer only from uploaded company documents. If the uploaded documents do not contain the answer, it should say the answer is not available in the uploaded documents.
