import sqlite3
import streamlit as st
from pathlib import Path
import openai
import warnings

# ─── Configuration & Auth Setup ────────────────────────────────────────────────
openai.api_key  = "AIzaSyATVECCexY0051rl7BJ1awvClXGHsTltes"
openai.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
warnings.filterwarnings("ignore", category=UserWarning)

# Streamlit’s built-in OAuth (assumes you have .streamlit/secrets.toml set up)
st.set_page_config(page_title="RamChat – Cate", layout="wide")

if not st.user.is_logged_in:
    st.header("🔒 RamChat is private.")
    st.subheader("Please log in with your Cate School Google account.")
    st.button("Log in with Google", on_click=st.login)
    st.stop()

email = st.user.email.lower()
if not email.endswith("@cate.org"):
    st.error("Access denied: please sign in with your @cate.org account.")
    st.button("Log out", on_click=st.logout)
    st.stop()

st.sidebar.success(f"Signed in as {st.user.name}")

# ─── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_latest_emails(limit: int = 1000):
    db = Path("emails.db")
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT date, sender, subject, body FROM emails "
        "ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        f"Date: {d} | From: {s} | Subject: {sub}\n"
        + (b[:500] + "…" if len(b)>500 else b)
        for d, s, sub, b in rows
    ]

@st.cache_data
def load_handbook_text():
    txt = Path("data/handbook.txt")
    if not txt.exists():
        return "[Handbook text not found]"
    return txt.read_text(encoding="utf-8")

def build_system_context():
    handbook = load_handbook_text()
    emails   = load_latest_emails(1000)
    return "\n\n".join([
        "You are RamChat, an AI assistant for Cate School.",
        "Use the Student Handbook for policy questions:", handbook,
        "You have access to the 1000 most recent emails (invisible unless asked):",
        "\n\n".join(emails),
        "Quote emails when citing sources. In addition, omit all duplicate emails. For example, if a user asks to see the last 10 emails, show only 10 unique emails.",
        "Be concise and accurate, and ALWAYS CITE YOUR SOURCES."
    ])

# ─── Chat handler ────────────────────────────────────────────────────────────────
def get_response(query: str, history: list[tuple[str,str]]) -> str:
    msgs = [{"role": "system",    "content": build_system_context()}]
    for q,a in history:
        msgs += [
            {"role": "user",      "content": q},
            {"role": "assistant", "content": a}
        ]
    msgs.append({"role": "user", "content": query})

    resp = openai.ChatCompletion.create(
        model="gemini-2.0-flash",
        messages=msgs,
        temperature=1,
        max_tokens=102400
    )
    ch = resp.choices[0]
    text = getattr(ch.message, "content", None) or getattr(ch, "text", "")
    if ch.finish_reason == "length":
        text += "\n\n*Note: response truncated.*"
    return text

# ─── Streamlit UI ───────────────────────────────────────────────────────────────
st.title("RamChat – Cate School Assistant")

if "history" not in st.session_state:
    st.session_state.history = []

# Render conversation
for q,a in st.session_state.history:
    st.chat_message("user").markdown(q)
    st.chat_message("assistant").markdown(a)

# User input
query = st.chat_input("Ask about the handbook or your emails…")
if query:
    st.chat_message("user").markdown(query)
    # ← spinner here
    with st.spinner("Thinking..."):
        answer = get_response(query, st.session_state.history)
    st.chat_message("assistant").markdown(answer)
    st.session_state.history.append((query, answer))

# Logout option
st.sidebar.markdown("---")
if st.sidebar.button("Log out"):
    st.logout()
