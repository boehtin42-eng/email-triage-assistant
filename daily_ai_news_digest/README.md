# Daily Business AI News Digest

Streamlit dashboard for tracking AI tools, business automation ideas, and process optimization news from RSS feeds.

## What it does

- Reads RSS feeds and YouTube RSS feeds
- Scores each item for small-business relevance
- Highlights automation, agents, customer support, sales, CRM, invoice, email, GPT, and Codex related items
- Shows action hints for business owners
- Supports custom RSS URLs
- Exports a CSV digest

## Run locally

```bash
streamlit run daily_ai_news_digest/app.py
```

## YouTube RSS format

```text
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

## Notes

This app does not use a paid AI API. It summarizes RSS metadata only. If a feed blocks RSS requests or changes its URL, replace it with a working RSS URL in the sidebar.
