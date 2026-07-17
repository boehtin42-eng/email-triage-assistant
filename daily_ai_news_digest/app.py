from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import re
from typing import Dict, List, Optional

import feedparser
import pandas as pd
import streamlit as st


DEFAULT_FEEDS = [
    {
        "source": "OpenAI News",
        "type": "RSS",
        "url": "https://openai.com/news/rss.xml",
        "category": "ChatGPT / OpenAI / Codex",
    },
    {
        "source": "Google Blog",
        "type": "RSS",
        "url": "https://blog.google/feed/",
        "category": "AI / Google",
    },
    {
        "source": "VentureBeat AI",
        "type": "RSS",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "AI tools / business",
    },
    {
        "source": "TechCrunch AI",
        "type": "RSS",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "AI startups / tools",
    },
    {
        "source": "MIT Technology Review",
        "type": "RSS",
        "url": "https://www.technologyreview.com/feed/",
        "category": "AI trends",
    },
]

DEFAULT_YOUTUBE_FEEDS = [
    {
        "source": "Two Minute Papers",
        "type": "YouTube RSS",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg",
        "category": "AI research / trends",
    },
    {
        "source": "Google Developers",
        "type": "YouTube RSS",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "category": "AI / developer tools",
    },
]

TOP_PRIORITY_KEYWORDS = [
    "chatgpt",
    "openai",
    "codex",
    "gpt-",
    "gpt 5",
    "gpt-5",
    "gpt 4",
    "gpt-4",
    "model release",
    "agent mode",
    "ai agent",
    "developer tool",
    "coding agent",
]

BUSINESS_KEYWORDS = [
    "small business",
    "automation",
    "workflow",
    "productivity",
    "agent",
    "agents",
    "chatbot",
    "customer support",
    "sales",
    "marketing",
    "invoice",
    "email",
    "crm",
    "codex",
    "gpt",
    "ai tool",
    "tools",
    "process",
    "operations",
    "spreadsheet",
    "google workspace",
    "zapier",
    "make.com",
    "n8n",
]


st.set_page_config(page_title="Daily Business AI News Digest", layout="wide")


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except Exception:
        return None


def clean_text(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.replace("\n", " ").split())


def score_relevance(title: str, summary: str) -> int:
    text = f"{title} {summary}".lower()
    score = 0
    for keyword in TOP_PRIORITY_KEYWORDS:
        if keyword in text:
            score += 4
    for keyword in BUSINESS_KEYWORDS:
        if keyword in text:
            score += 2
    return score


def relevance_label(score: int) -> str:
    if score >= 8:
        return "High"
    if score >= 4:
        return "Medium"
    return "Low"


def priority_reason(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(keyword in text for keyword in ["chatgpt", "openai", "codex", "gpt-", "gpt 5", "gpt-5"]):
        return "ChatGPT / OpenAI / Codex"
    if any(keyword in text for keyword in ["automation", "workflow", "process", "agent", "chatbot"]):
        return "Business process automation"
    if any(keyword in text for keyword in ["sales", "marketing", "crm", "customer support"]):
        return "Sales / customer workflow"
    if any(keyword in text for keyword in ["invoice", "email", "spreadsheet", "google workspace"]):
        return "Admin time-saving"
    return "General AI business trend"


def action_hint(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if "chatgpt" in text or "openai" in text or "codex" in text or "gpt-" in text:
        return "Review first: this may affect ChatGPT, Codex, internal tools, or AI workflows."
    if "agent" in text or "chatbot" in text:
        return "Check if this can reduce support or admin replies."
    if "automation" in text or "workflow" in text or "process" in text:
        return "Look for a repeatable business process to automate."
    if "sales" in text or "crm" in text or "marketing" in text:
        return "Review for lead generation or customer follow-up ideas."
    if "email" in text or "invoice" in text:
        return "Review for admin time-saving use cases."
    if "codex" in text or "gpt" in text:
        return "Check if this can improve internal tool building."
    return "Skim and decide if it is relevant to current business workflows."


def source_rows_from_text(custom_sources: str) -> List[Dict[str, str]]:
    rows = []
    for line in custom_sources.splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        rows.append(
            {
                "source": "Custom feed",
                "type": "RSS / YouTube RSS",
                "url": url,
                "category": "Custom",
            }
        )
    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_feed(source: str, feed_type: str, url: str, category: str) -> List[Dict[str, str]]:
    parsed = feedparser.parse(url)
    items = []
    for entry in parsed.entries[:20]:
        title = clean_text(entry.get("title", ""))
        summary = clean_text(entry.get("summary", entry.get("description", "")))
        link = entry.get("link", "")
        published = parse_date(entry.get("published") or entry.get("updated"))
        published_text = published.strftime("%Y-%m-%d") if published else ""
        score = score_relevance(title, summary)
        items.append(
            {
                "date": published_text,
                "source": source,
                "type": feed_type,
                "category": category,
                "title": title,
                "summary": summary[:320],
                "relevance": relevance_label(score),
                "score": score,
                "priority_reason": priority_reason(title, summary),
                "action_hint": action_hint(title, summary),
                "link": link,
            }
        )
    return items


def fetch_all(feeds: List[Dict[str, str]]) -> pd.DataFrame:
    rows = []
    errors = []
    for feed in feeds:
        try:
            rows.extend(fetch_feed(feed["source"], feed["type"], feed["url"], feed["category"]))
        except Exception as exc:
            errors.append(f"{feed['source']}: {exc}")

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        dataframe = pd.DataFrame(
            columns=[
                "date",
                "source",
                "type",
                "category",
                "title",
                "summary",
                "relevance",
                "score",
                "priority_reason",
                "action_hint",
                "link",
            ]
        )
    return dataframe, errors


def apply_filters(
    dataframe: pd.DataFrame,
    search: str,
    relevance_filter: List[str],
    source_filter: List[str],
) -> pd.DataFrame:
    filtered = dataframe.copy()
    if search:
        query = search.lower()
        mask = filtered[["title", "summary", "action_hint", "source"]].astype(str).apply(
            lambda column: column.str.lower().str.contains(query, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    if relevance_filter:
        filtered = filtered[filtered["relevance"].isin(relevance_filter)]

    if source_filter:
        filtered = filtered[filtered["source"].isin(source_filter)]

    return filtered.sort_values(["score", "date"], ascending=[False, False])


with st.sidebar:
    st.header("Sources")
    st.success("Built-in AI/business news sources load automatically.")
    include_default_feeds = st.checkbox("Use built-in RSS feeds", value=True)
    include_youtube_feeds = st.checkbox("Use built-in YouTube feeds", value=True)

    with st.expander("Advanced: add extra RSS links"):
        custom_sources = st.text_area(
            "Optional extra RSS or YouTube RSS URLs",
            placeholder=(
                "One URL per line.\n"
                "Example:\n"
                "https://example.com/feed.xml"
            ),
            height=120,
            key="optional_custom_sources",
        )

    if st.button("Refresh feeds"):
        fetch_feed.clear()
        st.rerun()

    st.header("Filters")
    search = st.text_input("Search", placeholder="ChatGPT, Codex, automation, agent...")
    relevance_filter = st.multiselect("Relevance", ["High", "Medium", "Low"], default=["High", "Medium"])


feeds = []
if include_default_feeds:
    feeds.extend(DEFAULT_FEEDS)
if include_youtube_feeds:
    feeds.extend(DEFAULT_YOUTUBE_FEEDS)
feeds.extend(source_rows_from_text(custom_sources))

st.title("Daily Business AI News Digest")
st.caption("Open the app and it prioritizes business AI, ChatGPT, OpenAI, Codex, and process optimization news.")

if not feeds:
    st.warning("Turn on at least one built-in source or add an optional RSS source to start.")
    st.stop()

with st.spinner("Loading AI news sources..."):
    news, errors = fetch_all(feeds)

if errors:
    for error in errors:
        st.warning(error)

source_options = sorted(news["source"].dropna().unique().tolist()) if not news.empty else []
with st.sidebar:
    source_filter = st.multiselect("Source", source_options)

filtered_news = apply_filters(news, search, relevance_filter, source_filter)

metric_cols = st.columns(4)
metric_cols[0].metric("Total items", len(news))
metric_cols[1].metric("High relevance", int((news["relevance"] == "High").sum()))
metric_cols[2].metric("Medium relevance", int((news["relevance"] == "Medium").sum()))
metric_cols[3].metric("Sources", len(source_options))

tab_focus, tab_all, tab_sources = st.tabs(["Priority digest", "All items", "Sources"])

with tab_focus:
    st.subheader("Business AI, ChatGPT, OpenAI, and Codex priority news")
    focus_rows = filtered_news[filtered_news["relevance"].isin(["High", "Medium"])].head(25)
    if focus_rows.empty:
        st.info("No relevant items found with the current filters.")
    else:
        for _, row in focus_rows.iterrows():
            with st.container(border=True):
                st.markdown(f"### [{row['title']}]({row['link']})")
                st.caption(
                    f"{row['date']} • {row['source']} • {row['priority_reason']} • "
                    f"{row['relevance']} relevance"
                )
                st.write(row["summary"])
                st.info(row["action_hint"])

with tab_all:
    st.subheader("All fetched items")
    display_columns = [
        "date",
        "source",
        "category",
        "priority_reason",
        "title",
        "relevance",
        "score",
        "action_hint",
        "link",
    ]
    st.dataframe(filtered_news[display_columns], use_container_width=True, hide_index=True)
    st.download_button(
        "Download digest CSV",
        data=filtered_news.to_csv(index=False).encode("utf-8"),
        file_name=f"business_ai_news_digest_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

with tab_sources:
    st.subheader("Active sources")
    st.dataframe(pd.DataFrame(feeds), use_container_width=True, hide_index=True)
    st.info(
        "The app already loads built-in sources. Extra RSS or YouTube RSS links are optional."
    )
