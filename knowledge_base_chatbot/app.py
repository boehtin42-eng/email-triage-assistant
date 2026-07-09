import io
import html
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from docx import Document
from pypdf import PdfReader

try:
    import google.generativeai as genai
except ImportError:
    genai = None


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MAX_CONTEXT_CHUNKS = 5
ANSWER_LANGUAGES = {
    "Burmese": {
        "instruction": "Always answer in Burmese/Myanmar language.",
        "audience": "Burmese-speaking staff member",
    },
    "English": {
        "instruction": "Always answer in clear English.",
        "audience": "English-speaking staff member",
    },
    "German": {
        "instruction": "Always answer in clear German.",
        "audience": "German-speaking staff member",
    },
}


st.set_page_config(page_title="Knowledge Base Chatbot", layout="wide")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def get_secret(name: str) -> Optional[str]:
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return str(value) if value else None


def clean_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(file) -> str:
    reader = PdfReader(file)
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[Page {index}]\n{page_text}")
    return "\n\n".join(pages)


def extract_docx(file) -> str:
    document = Document(file)
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    table_rows = []
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                table_rows.append(" | ".join(cells))
    return "\n".join(paragraphs + table_rows)


def extract_spreadsheet(file, file_name: str) -> str:
    if file_name.lower().endswith(".csv"):
        dataframe = pd.read_csv(file, dtype=str).fillna("")
        return dataframe.to_csv(index=False)

    sheets = pd.read_excel(file, sheet_name=None, dtype=str)
    parts = []
    for sheet_name, dataframe in sheets.items():
        dataframe = dataframe.fillna("")
        parts.append(f"[Sheet: {sheet_name}]\n{dataframe.to_csv(index=False)}")
    return "\n\n".join(parts)


def extract_text(uploaded_file) -> str:
    file_name = uploaded_file.name
    extension = file_name.lower().rsplit(".", 1)[-1]
    data = uploaded_file.getvalue()

    if extension == "pdf":
        return clean_text(extract_pdf(io.BytesIO(data)))
    if extension == "docx":
        return clean_text(extract_docx(io.BytesIO(data)))
    if extension in {"xlsx", "xls", "csv"}:
        return clean_text(extract_spreadsheet(io.BytesIO(data), file_name))
    if extension in {"txt", "md"}:
        return clean_text(data.decode("utf-8", errors="ignore"))

    raise ValueError(f"Unsupported file type: {extension}")


def chunk_text(source: str, text: str) -> List[Dict[str, str]]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"source": source, "text": chunk})
        if end == len(text):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def render_copy_button(text: str, button_label: str = "Copy answer") -> None:
    escaped_text = html.escape(text)
    escaped_label = html.escape(button_label)
    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText(document.getElementById('copy-text').innerText);
                     this.innerText='Copied';"
            style="
                background:#ff4b4b;
                color:white;
                border:none;
                border-radius:6px;
                padding:0.55rem 0.8rem;
                font-weight:600;
                cursor:pointer;
            "
        >
            {escaped_label}
        </button>
        <pre id="copy-text" style="display:none;">{escaped_text}</pre>
        """,
        height=48,
    )


def tokenize(text: str) -> List[str]:
    return re.findall(r"[\w]+", text.lower())


def score_chunk(question_tokens: List[str], chunk: Dict[str, str]) -> int:
    chunk_text_lower = chunk["text"].lower()
    score = 0
    for token in question_tokens:
        if len(token) < 3:
            continue
        score += chunk_text_lower.count(token)
    return score


def find_relevant_chunks(question: str, chunks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    question_tokens = tokenize(question)
    scored: List[Tuple[int, Dict[str, str]]] = []
    for chunk in chunks:
        score = score_chunk(question_tokens, chunk)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:MAX_CONTEXT_CHUNKS]]


def build_prompt(question: str, relevant_chunks: List[Dict[str, str]], answer_language: str) -> str:
    context = "\n\n".join(
        f"Source: {chunk['source']}\nContent:\n{chunk['text']}" for chunk in relevant_chunks
    )
    language_config = ANSWER_LANGUAGES[answer_language]
    return f"""
You are a company knowledge base assistant.
Answer only from the provided company documents.
If the documents do not contain the answer, say that the answer is not available in the uploaded documents.
{language_config["instruction"]}
Keep the answer clear, short, and practical for a {language_config["audience"]}.
Mention the source file names used.
Keep product names, company names, prices, dates, and source file names exactly as written in the documents.

Question:
{question}

Company document context:
{context}
""".strip()


def answer_with_gemini(
    question: str,
    relevant_chunks: List[Dict[str, str]],
    answer_language: str,
) -> Tuple[str, str]:
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key or genai is None:
        return "", "No Gemini API key found."

    model_name = get_secret("GEMINI_MODEL") or "gemini-2.5-flash"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(build_prompt(question, relevant_chunks, answer_language))
        return (response.text or "").strip(), ""
    except Exception as exc:
        return "", f"Gemini answer generation failed: {exc}"


def render_source_chunks(chunks: List[Dict[str, str]]) -> None:
    st.subheader("Source snippets")
    for index, chunk in enumerate(chunks, start=1):
        with st.expander(f"{index}. {chunk['source']}"):
            st.write(chunk["text"])


def render_uploaded_docs_summary(uploaded_files, chunks: List[Dict[str, str]]) -> None:
    st.subheader("Uploaded documents")
    chunk_counts: Dict[str, int] = {}
    for chunk in chunks:
        chunk_counts[chunk["source"]] = chunk_counts.get(chunk["source"], 0) + 1

    rows = []
    for uploaded_file in uploaded_files:
        rows.append(
            {
                "File": uploaded_file.name,
                "Size KB": round(len(uploaded_file.getvalue()) / 1024, 1),
                "Chunks": chunk_counts.get(uploaded_file.name, 0),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_chat_history() -> None:
    if not st.session_state.chat_history:
        return

    st.subheader("Chat history")
    if st.button("Clear chat history"):
        st.session_state.chat_history = []
        st.rerun()

    for index, item in enumerate(reversed(st.session_state.chat_history), start=1):
        with st.expander(f"{index}. {item['question']}"):
            st.caption(f"Language: {item['language']} | Sources: {', '.join(item['sources'])}")
            st.write(item["answer"])
            render_copy_button(item["answer"], "Copy this answer")


st.title("Internal Knowledge Base Chatbot")
st.caption("Upload company docs, ask questions, and get answers grounded in the uploaded files.")

with st.sidebar:
    st.header("Upload Docs")
    uploaded_files = st.file_uploader(
        "PDF, DOCX, TXT, MD, CSV, XLSX",
        type=["pdf", "docx", "txt", "md", "csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )
    answer_language = st.selectbox(
        "Answer language",
        list(ANSWER_LANGUAGES.keys()),
        index=0,
    )
    st.info("The app does not train a model. It searches the uploaded docs during this session.")

all_chunks: List[Dict[str, str]] = []
extraction_errors = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            text = extract_text(uploaded_file)
            all_chunks.extend(chunk_text(uploaded_file.name, text))
        except Exception as exc:
            extraction_errors.append(f"{uploaded_file.name}: {exc}")

if extraction_errors:
    for error in extraction_errors:
        st.error(error)

if not all_chunks:
    st.warning("Upload at least one company document to start.")
    st.stop()

st.success(f"Loaded {len(uploaded_files)} file(s) and created {len(all_chunks)} searchable text chunk(s).")
render_uploaded_docs_summary(uploaded_files, all_chunks)

question = st.text_input(
    "Ask a question",
    placeholder="Example: What is our cancellation policy?",
)

if st.button("Ask", type="primary"):
    if not question.strip():
        st.error("Please enter a question.")
        st.stop()

    relevant_chunks = find_relevant_chunks(question, all_chunks)
    if not relevant_chunks:
        st.warning("No relevant text found in the uploaded documents.")
        st.stop()

    with st.spinner("Searching documents and preparing answer..."):
        answer, answer_error = answer_with_gemini(question, relevant_chunks, answer_language)

    st.subheader("Answer")
    if answer:
        st.write(answer)
        render_copy_button(answer)
        st.session_state.chat_history.append(
            {
                "question": question.strip(),
                "answer": answer,
                "language": answer_language,
                "sources": sorted({chunk["source"] for chunk in relevant_chunks}),
            }
        )
    else:
        st.warning(answer_error)
        st.info("The app is showing the most relevant source snippets instead.")

    render_source_chunks(relevant_chunks)

render_chat_history()
