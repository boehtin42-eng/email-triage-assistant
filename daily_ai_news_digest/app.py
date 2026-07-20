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

if "relevance_filter" not in st.session_state:
    st.session_state["relevance_filter"] = ["High", "Medium"]
if "topic_filter" not in st.session_state:
    st.session_state["topic_filter"] = "All"


def set_relevance_filter(values: List[str]) -> None:
    st.session_state["relevance_filter"] = values


def set_filters(relevance_values: List[str], topic_value: str) -> None:
    st.session_state["relevance_filter"] = relevance_values
    st.session_state["topic_filter"] = topic_value


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
    if is_openai_codex_news(title, summary):
        return "ChatGPT / OpenAI / Codex"
    if any(keyword in text for keyword in ["automation", "workflow", "process", "agent", "chatbot"]):
        return "Business process automation"
    if any(keyword in text for keyword in ["sales", "marketing", "crm", "customer support"]):
        return "Sales / customer workflow"
    if any(keyword in text for keyword in ["invoice", "email", "spreadsheet", "google workspace"]):
        return "Admin time-saving"
    return "General AI business trend"


def is_openai_codex_news(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(
        keyword in text
        for keyword in [
            "chatgpt",
            "openai",
            "codex",
            "gpt-",
            "gpt 5",
            "gpt-5",
            "gpt 4",
            "gpt-4",
        ]
    )


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


def short_information(title: str, summary: str) -> str:
    text = clean_text(summary)
    if text:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        compact = " ".join(sentence for sentence in sentences[:2] if sentence).strip()
        if compact:
            return compact[:260]
    return f"Quick update: {title}"


def practical_tip(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if is_openai_codex_news(title, summary):
        return "Check whether this can improve how you write, research, build internal tools, or automate repetitive admin work."
    if "agent" in text or "chatbot" in text:
        return "Use this as an idea for customer replies, internal FAQ support, or lead follow-up automation."
    if "automation" in text or "workflow" in text or "process" in text:
        return "Look for one repeated manual task in the business and test a small automation around it."
    if "sales" in text or "crm" in text or "marketing" in text:
        return "Compare this with your current lead or customer follow-up process."
    if "invoice" in text or "email" in text or "spreadsheet" in text:
        return "Test whether this can reduce manual copy-paste, tracking, or reporting work."
    return "Save this only if it connects to a current business process or tool decision."


def exact_steps(title: str, summary: str) -> List[str]:
    text = f"{title} {summary}".lower()
    if is_openai_codex_news(title, summary):
        return [
            "Open the article or video and check what changed.",
            "Write down one business task it could improve, for example email replies, reporting, research, or internal tools.",
            "Test it with one small workflow before changing the main process.",
        ]
    if "agent" in text or "chatbot" in text:
        return [
            "Pick one repeated question customers or staff ask often.",
            "Create a short FAQ or sample answers for that topic.",
            "Test a draft-only chatbot first, then review answers before using it with real users.",
        ]
    if "automation" in text or "workflow" in text or "process" in text:
        return [
            "Choose one repetitive task that happens every week.",
            "Map the trigger, input, action, and output.",
            "Build a small Make.com, n8n, or Streamlit test before automating the full workflow.",
        ]
    if "sales" in text or "crm" in text or "marketing" in text:
        return [
            "Check if the idea helps collect leads, reply faster, or follow up better.",
            "Test it with 5-10 sample leads or messages.",
            "Keep the result only if it saves time or improves response quality.",
        ]
    if "invoice" in text or "email" in text or "spreadsheet" in text:
        return [
            "Compare the idea with the current manual admin process.",
            "Test it using sample invoices, emails, or spreadsheet rows.",
            "Use it only after checking that important data is not lost or changed incorrectly.",
        ]
    return [
        "Skim the article title and short information.",
        "Decide if it connects to a current business problem.",
        "If yes, save it as an idea to test later.",
    ]


def why_it_matters(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if is_openai_codex_news(title, summary):
        return "Useful because ChatGPT/OpenAI/Codex changes can improve internal tools, drafting, research, or automation workflows."
    if "agent" in text or "chatbot" in text:
        return "Useful because agents or chatbots may reduce time spent on replies, support, and admin tasks."
    if "automation" in text or "workflow" in text or "process" in text:
        return "Useful because it may reveal a repeatable business process that can be automated."
    if "sales" in text or "crm" in text or "marketing" in text:
        return "Useful because it may improve lead handling, follow-ups, or customer communication."
    if "invoice" in text or "email" in text or "spreadsheet" in text:
        return "Useful because it may reduce manual office work around invoices, emails, and reports."
    return "Useful as a quick signal for AI trends that may become relevant to business operations."


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
                "is_openai_codex": is_openai_codex_news(title, summary),
                "priority_reason": priority_reason(title, summary),
                "action_hint": action_hint(title, summary),
                "why_it_matters": why_it_matters(title, summary),
                "short_information": short_information(title, summary),
                "practical_tip": practical_tip(title, summary),
                "exact_steps": exact_steps(title, summary),
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
                "is_openai_codex",
                "priority_reason",
                "action_hint",
                "why_it_matters",
                "short_information",
                "practical_tip",
                "exact_steps",
                "link",
            ]
        )
    return dataframe, errors


def apply_filters(
    dataframe: pd.DataFrame,
    search: str,
    relevance_filter: List[str],
    source_filter: List[str],
    topic_filter: str,
) -> pd.DataFrame:
    filtered = dataframe.copy()
    if search:
        query = search.lower()
        mask = filtered[
            ["title", "summary", "action_hint", "short_information", "practical_tip", "source"]
        ].astype(str).apply(
            lambda column: column.str.lower().str.contains(query, na=False)
        ).any(axis=1)
        filtered = filtered[mask]

    if relevance_filter:
        filtered = filtered[filtered["relevance"].isin(relevance_filter)]

    if source_filter:
        filtered = filtered[filtered["source"].isin(source_filter)]

    if topic_filter == "ChatGPT / OpenAI / Codex only":
        filtered = filtered[filtered["is_openai_codex"]]

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
    relevance_filter = st.multiselect("Relevance", ["High", "Medium", "Low"], key="relevance_filter")


feeds = []
if include_default_feeds:
    feeds.extend(DEFAULT_FEEDS)
if include_youtube_feeds:
    feeds.extend(DEFAULT_YOUTUBE_FEEDS)
feeds.extend(source_rows_from_text(custom_sources))

st.title("Daily Business AI News Digest")
st.caption(
    "Open the app and get short business AI updates, practical tips, and exact next steps."
)

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

topic_filter = st.session_state["topic_filter"]
filtered_news = apply_filters(news, search, relevance_filter, source_filter, topic_filter)

total_count = len(news)
high_count = int((news["relevance"] == "High").sum())
medium_count = int((news["relevance"] == "Medium").sum())
openai_codex_count = int(news["is_openai_codex"].sum()) if "is_openai_codex" in news else 0
shown_count = len(filtered_news)
active_relevance = ", ".join(relevance_filter) if relevance_filter else "All"

metric_cols = st.columns(6)
with metric_cols[0]:
    st.metric("Total items", total_count)
    st.button(
        "Show all news",
        key="filter_all",
        on_click=set_filters,
        args=([], "All"),
        use_container_width=True,
    )
with metric_cols[1]:
    st.metric("Showing now", shown_count)
    st.caption(f"{active_relevance} • {topic_filter}")
with metric_cols[2]:
    st.metric("High relevance", high_count)
    st.button(
        f"Show high only ({high_count})",
        key="filter_high",
        on_click=set_filters,
        args=(["High"], "All"),
        use_container_width=True,
    )
with metric_cols[3]:
    st.metric("OpenAI/Codex", openai_codex_count)
    st.button(
        "ChatGPT / OpenAI / Codex only",
        key="filter_openai_codex",
        on_click=set_filters,
        args=([], "ChatGPT / OpenAI / Codex only"),
        use_container_width=True,
    )
with metric_cols[4]:
    st.metric("Medium relevance", medium_count)
    st.button(
        f"Show medium only ({medium_count})",
        key="filter_medium",
        on_click=set_filters,
        args=(["Medium"], "All"),
        use_container_width=True,
    )
with metric_cols[5]:
    st.metric("Sources", len(source_options))

st.info(f"Showing {shown_count} item(s). Relevance: {active_relevance}. Topic: {topic_filter}.")

tab_focus, tab_all, tab_sources = st.tabs(["Priority digest", "All items", "Sources"])

with tab_focus:
    if topic_filter == "ChatGPT / OpenAI / Codex only":
        st.subheader("ChatGPT / OpenAI / Codex news only")
    elif relevance_filter == ["High"]:
        st.subheader("High relevance news only")
    elif relevance_filter == ["Medium"]:
        st.subheader("Medium relevance news only")
    elif not relevance_filter:
        st.subheader("All AI/business news")
    else:
        st.subheader("Business AI, ChatGPT, OpenAI, and Codex priority news")
    focus_rows = filtered_news.head(25)
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
                st.write(row["short_information"])
                st.success(f"Why it matters for small business: {row['why_it_matters']}")
                st.info(f"Tip: {row['practical_tip']}")
                with st.expander("Exact steps to use this"):
                    for index, step in enumerate(row["exact_steps"], start=1):
                        st.write(f"{index}. {step}")

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
        "short_information",
        "practical_tip",
        "why_it_matters",
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
