# Daily Business AI News Digest

Streamlit dashboard for tracking business AI tools, ChatGPT/OpenAI/Codex updates, and process optimization news from built-in RSS and YouTube RSS feeds.

## What it does

- Loads built-in AI/business RSS feeds automatically when the app opens
- Loads built-in YouTube RSS feeds automatically
- Gives higher priority to ChatGPT, OpenAI, Codex, GPT, AI agents, and business workflow news
- Highlights automation, agents, customer support, sales, CRM, invoice, email, GPT, and Codex related items
- Shows action hints for business owners
- Supports optional extra RSS URLs
- Exports a CSV digest

## Run locally

```bash
streamlit run daily_ai_news_digest/app.py
```

## Optional YouTube RSS format

The app already includes default sources. Use this only when adding extra channels.

```text
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

## Notes

This app does not use a paid AI API. It scores RSS metadata only. If a feed blocks RSS requests or changes its URL, add a working RSS URL in the optional advanced source box.
