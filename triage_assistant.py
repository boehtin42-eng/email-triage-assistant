import email
import imaplib
import json
import re
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.message import Message
from io import BytesIO
from typing import Any, Optional

import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None


GEMINI_MODEL = "gemini-2.5-flash"


def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    if st is None:
        return default

    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default
    return str(value) if value is not None else default


def _email_config() -> dict[str, Any]:
    return {
        "host": get_secret("EMAIL_HOST"),
        "port": int(get_secret("EMAIL_PORT", "993") or "993"),
        "username": get_secret("EMAIL_USERNAME"),
        "password": get_secret("EMAIL_PASSWORD"),
        "mailbox": get_secret("EMAIL_MAILBOX", "INBOX") or "INBOX",
    }


def _require_values(config: dict[str, Any], required: list[str]) -> tuple[bool, str]:
    missing = [key for key in required if not config.get(key)]
    if missing:
        return False, f"Missing secrets: {', '.join(missing)}"
    return True, "OK"


def _connect_imap() -> imaplib.IMAP4_SSL:
    config = _email_config()
    ok, message = _require_values(config, ["host", "username", "password"])
    if not ok:
        raise ValueError(message)

    mail = imaplib.IMAP4_SSL(config["host"], config["port"])
    mail.login(config["username"], config["password"])
    status, _ = mail.select(config["mailbox"], readonly=True)
    if status != "OK":
        raise RuntimeError(f"Could not open mailbox: {config['mailbox']}")
    return mail


def test_email_connection() -> tuple[bool, str]:
    try:
        mail = _connect_imap()
        mail.close()
        mail.logout()
        return True, "Email connection works."
    except Exception as exc:
        return False, f"Email connection failed: {exc}"


def test_gemini_connection() -> tuple[bool, str]:
    if genai is None:
        return False, "google-generativeai package is not installed."

    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        return False, "Missing secret: GEMINI_API_KEY"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content("Reply with only: ok")
        if (response.text or "").strip():
            return True, "Gemini connection works."
        return False, "Gemini connection failed: empty response."
    except Exception as exc:
        return False, f"Gemini connection failed: {exc}"


def _decode_header(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_sender_address(from_header: str) -> str:
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).strip()
    return from_header.strip()


def _message_body(message: Message) -> str:
    if message.is_multipart():
        plain_text = ""
        html_text = ""
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition.lower():
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            if content_type == "text/plain" and not plain_text:
                plain_text = text
            elif content_type == "text/html" and not html_text:
                html_text = _strip_html(text)

        return _clean_body(plain_text or html_text)

    payload = message.get_payload(decode=True)
    if not payload:
        return ""
    charset = message.get_content_charset() or "utf-8"
    text = payload.decode(charset, errors="replace")
    if message.get_content_type() == "text/html":
        text = _strip_html(text)
    return _clean_body(text)


def _strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _clean_body(value: str) -> str:
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()[:8000]


def _format_imap_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


def fetch_unread_emails(
    limit: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict[str, str]]:
    mail = _connect_imap()
    try:
        criteria = ["UNSEEN", "UNDELETED"]
        if start_date is not None:
            criteria.extend(["SINCE", _format_imap_date(start_date)])
        if end_date is not None:
            criteria.extend(["BEFORE", _format_imap_date(end_date + timedelta(days=1))])

        status, data = mail.search(None, *criteria)
        if status != "OK" or not data or not data[0]:
            return []

        message_ids = list(reversed(data[0].split()))[:limit]
        emails: list[dict[str, str]] = []

        for message_id in message_ids:
            # BODY.PEEK[] reads the message without setting the Seen flag.
            status, msg_data = mail.fetch(message_id, "(BODY.PEEK[])")
            if status != "OK":
                continue

            raw_message = msg_data[0][1]
            parsed = email.message_from_bytes(raw_message)
            from_header = _decode_header(parsed.get("From"))

            emails.append(
                {
                    "message_id": message_id.decode("utf-8", errors="replace"),
                    "from": from_header,
                    "from_email": _extract_sender_address(from_header),
                    "subject": _decode_header(parsed.get("Subject")),
                    "date": _decode_header(parsed.get("Date")),
                    "body": _message_body(parsed),
                }
            )

        return emails
    finally:
        try:
            mail.close()
        except Exception:
            pass
        mail.logout()


def classify_emails(emails: list[dict[str, str]]) -> list[dict[str, str]]:
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or genai is None:
        return [_heuristic_triage(item) for item in emails]

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)
    results = []

    for item in emails:
        try:
            results.append(_gemini_triage(model, item))
        except Exception as exc:
            fallback = _heuristic_triage(item)
            fallback["processing_note"] = f"Gemini failed, heuristic used: {exc}"
            results.append(fallback)

    return results


def _gemini_triage(model: Any, item: dict[str, str]) -> dict[str, str]:
    prompt = {
        "from": item["from"],
        "subject": item["subject"],
        "body": item["body"][:6000],
    }

    response = model.generate_content(
        (
            "You triage business emails. Return only valid JSON with these keys: "
            "category, priority, summary, next_action, german_reply_draft. "
            "Do not claim that an email was sent.\n\n"
            f"Email:\n{json.dumps(prompt, ensure_ascii=False)}"
        ),
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )

    parsed = json.loads(_extract_json(response.text or "{}"))

    return _result_row(item, parsed, "Gemini")


def _extract_json(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    return content


def _heuristic_triage(item: dict[str, str]) -> dict[str, str]:
    subject = item["subject"].lower()
    body = item["body"].lower()
    text = f"{subject} {body}"

    if any(word in text for word in ["urgent", "asap", "dringend", "sofort"]):
        priority = "High"
    elif any(word in text for word in ["invoice", "rechnung", "payment", "zahlung"]):
        priority = "Medium"
    else:
        priority = "Normal"

    if any(word in text for word in ["invoice", "rechnung", "payment", "zahlung"]):
        category = "Billing"
    elif any(word in text for word in ["meeting", "termin", "appointment"]):
        category = "Scheduling"
    elif any(word in text for word in ["support", "problem", "issue", "hilfe"]):
        category = "Support"
    else:
        category = "General"

    parsed = {
        "category": category,
        "priority": priority,
        "summary": item["body"][:300] or item["subject"],
        "next_action": "Review the email and decide whether a human reply is needed.",
        "german_reply_draft": (
            "Guten Tag,\n\nvielen Dank fuer Ihre Nachricht. "
            "Wir pruefen Ihr Anliegen und melden uns zeitnah bei Ihnen.\n\n"
            "Mit freundlichen Gruessen"
        ),
    }
    return _result_row(item, parsed, "Heuristic")


def _result_row(item: dict[str, str], parsed: dict[str, Any], method: str) -> dict[str, str]:
    return {
        "date": item.get("date", ""),
        "from": item.get("from", ""),
        "from_email": item.get("from_email", ""),
        "subject": item.get("subject", ""),
        "category": str(parsed.get("category", "")),
        "priority": str(parsed.get("priority", "")),
        "summary": str(parsed.get("summary", "")),
        "next_action": str(parsed.get("next_action", "")),
        "german_reply_draft": str(parsed.get("german_reply_draft", "")),
        "method": method,
    }


def create_excel_bytes(rows: list[dict[str, str]]) -> bytes:
    output = BytesIO()
    dataframe = pd.DataFrame(rows)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Email Triage")
    return output.getvalue()
