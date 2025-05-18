import os
import sqlite3
import streamlit as st
from pathlib import Path
import openai
import warnings
import subprocess
import threading
import time

# ─── Configuration ───────────────────────────────────────────────────────────────

# Embedded Gemini API key (no billing attached)
openai.api_key  = "AIzaSyATVECCexY0051rl7BJ1awvClXGHsTltes"
openai.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"

# Silence harmless warnings
warnings.filterwarnings("ignore", category=UserWarning)

# ─── Background email fetch loop ────────────────────────────────────────────────

def fetch_emails_periodically(interval_seconds: int = 300):
    """
    Every `interval_seconds`, re-run fetch_emails.py to pull
    the latest emails into emails.db (with deduplication in fetch_emails.py).
    """
    while True:
        try:
            subprocess.run(
                ["python", "fetch_emails.py"],
                cwd=os.getcwd(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except Exception:
            pass
        time.sleep(interval_seconds)

# Start the background thread (daemon so it won't block exit)
threading.Thread(target=fetch_emails_periodically, args=(300,), daemon=True).start()

# ─── Caching layers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_latest_emails(limit: int = 200):
    """
    Fetch the most recent `limit` unique emails from the local SQLite store.
    Cached for 5 minutes so we automatically see DB updates.
    """
    db = Path("emails.db")
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        """
        SELECT date, sender, subject, body
          FROM emails
         ORDER BY date DESC
         LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    snippets = []
    for date, sender, subj, body in rows:
        snippet = (
            f"Date: {date} | From: {sender} | Subject: {subj}\n"
            + (body[:500] + "…" if len(body) > 500 else body)
        )
        snippets.append(snippet)
    return snippets

@st.cache_data
def load_handbook_text():
    """
    Load the student handbook from a pre-extracted .txt file.
    """
    txt_path = Path("data/handbook.txt")
    if not txt_path.exists():
        return "[Student Handbook text not found – please create data/handbook.txt]"
    try:
        return txt_path.read_text(encoding="utf-8")
    except Exception as e:
        st.error(f"❌ Unable to read handbook text: {e}")
        return "[Error loading handbook text]"

def build_system_context():
    handbook = load_handbook_text()
    emails   = load_latest_emails(200)
    return "\n\n".join([
        "You are RamChat, an AI assistant for Cate School students.",
        "Use the following Student Handbook to answer policy questions:",
        handbook,
        "You also have access to the 200 most recent emails (do NOT display them unless asked):",
        "\n\n".join(emails),
        "Only quote email contents when the user explicitly requests them.",
        "Be concise and accurate, and ALWAYS CITE YOUR SOURCES."
    ])

# ─── Gemini chat call with conversational memory ────────────────────────────────

def get_response(user_query: str, history: list[tuple[str,str]]) -> str:
    system_msg = {"role": "system", "content": build_system_context()}
    messages = [system_msg]

    # Replay prior turns for in-session memory
    for q, a in history:
        messages.append({"role": "user",      "content": q})
        messages.append({"role": "assistant", "content": a})

    # New user turn
    messages.append({"role": "user", "content": user_query})

    resp = openai.ChatCompletion.create(
        model="gemini-2.5-flash-preview-04-17",
        messages=messages,
        temperature=0.2,
        top_p=0.9,
        max_tokens=10240,
    )

    choice = resp.choices[0]
    finish = getattr(choice, "finish_reason", None)

    if hasattr(choice, "message") and getattr(choice.message, "content", None):
        answer = choice.message.content
    elif hasattr(choice, "text") and choice.text:
        answer = choice.text
    else:
        answer = "😕 Sorry, I didn’t get a valid reply from the model."

    if finish == "length":
        answer += "\n\n*Note: response was truncated by max_tokens.*"

    return answer

# ─── Streamlit UI ───────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="RamChat", layout="wide")
    st.title("RamChat – Cate School Assistant")

    if "history" not in st.session_state:
        st.session_state.history = []  # list of (user, assistant) pairs

    # Render past conversation
    for q, a in st.session_state.history:
        st.chat_message("user").markdown(q)
        st.chat_message("assistant").markdown(a)

    # New user input
    query = st.chat_input("Ask me about the handbook, your emails, or anything Cate-related…")
    if query:
        st.chat_message("user").markdown(query)
        with st.spinner("Thinking…"):
            answer = get_response(query, st.session_state.history)
        st.chat_message("assistant").markdown(answer)
        st.session_state.history.append((query, answer))

if __name__ == "__main__":
    main()
