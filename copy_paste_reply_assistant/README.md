# Copy-Paste Reply Assistant

This Streamlit app helps write reply drafts for Facebook Messenger, WhatsApp, Instagram DM, and similar personal or business messages.

It is intentionally not an auto-reply bot. The user copies an incoming message into the app, generates a reply draft, reviews it, copies it, and sends it manually.

## Why this approach

Personal Facebook, WhatsApp, and Instagram accounts do not provide a safe official API for automatic bot replies. This copy-paste workflow avoids account risk while still saving writing time.

## Features

- Paste incoming message
- Choose platform
- Choose sender type: Customer, Friend, Stranger, Lead, Colleague
- Choose tone
- Choose reply language
- Choose reply length
- Optional extra context
- Optional writing style examples
- AI reply draft
- Copy Reply button
- No automatic sending

## Streamlit Secrets

Add this in Streamlit Cloud secrets:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
```

## Local run

```bash
cd copy_paste_reply_assistant
pip install -r requirements.txt
export GEMINI_API_KEY="your-gemini-api-key"
streamlit run app.py
```

## Deploy

If deploying from the main repository, set:

```text
Root directory: copy_paste_reply_assistant
Main file path: app.py
```
