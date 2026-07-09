# Internal Knowledge Base Chatbot

Upload company documents and ask questions. The app searches the uploaded files and answers from the matching source snippets.

## Features

- Upload PDF, DOCX, TXT, MD, CSV, XLSX files
- Search uploaded documents during the current session
- Ask questions
- Optional Gemini answer generation
- Source snippets shown for review

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
```

If `GEMINI_API_KEY` is missing, the app still works as a document search tool and shows relevant source snippets.

## Safety note

The bot should answer only from uploaded company documents. If the uploaded documents do not contain the answer, it should say the answer is not available in the uploaded documents.
