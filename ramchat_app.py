import streamlit as st
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.schema.runnable import RunnableConfig

# ==== Load environment variables ====
dotenv_path = Path(os.getcwd()) / ".env"
load_dotenv(dotenv_path)

# ==== Load vector store created with ingest_emails.py ====
embedding = OpenAIEmbeddings()

try:
    vectorstore = FAISS.load_local(
        "faiss_index",  # Make sure this matches your saved folder name
        embeddings=embedding,
        allow_dangerous_deserialization=True
    )
except Exception as e:
    st.error(f"Failed to load vector store: {e}")
    st.stop()

retriever = vectorstore.as_retriever()

# ==== Set up the chatbot chain with preloaded system message ====
current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
system_prompt = (
    f"You are RamChat, a helpful assistant trained on Cate School resources like the student handbook and email announcements. Prioritize the information from emails less than a week ago if describing a time-sensitive event, like dates of club meetings, the week ahead, or sporting events. For set schedules/time insensitive events like bus schedules, refer to the most recent email about the topic in addition to the student handbook if possible. If you don't have specific data for certain events a student is asking for, infer the schedule using past events and the student handbook."
    f"The current date and time is {current_time}. Always provide clear, accurate, and concise answers."
    f""
)

llm = ChatOpenAI(temperature=0.3)

qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

# ==== Streamlit UI ====
st.set_page_config(page_title="RamChat", page_icon="🐏")
st.title("🐏 RamChat: Ask Me About Cate School")

# Time-based greeting
hour = datetime.now().hour
if hour < 12:
    greeting = "Good morning!"
elif hour < 18:
    greeting = "Good afternoon!"
else:
    greeting = "Good evening!"
st.markdown(f"{greeting} I'm trained on the Cate School Student Handbook and school emails. Ask me anything about rules, events, or policies!")

# ==== Session state ====
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "source_history" not in st.session_state:
    st.session_state.source_history = []

# ==== Chat input ====
query = st.chat_input("Ask me a question...")

if query:
    with st.spinner("Thinking..."):
        full_context_query = {
            "question": f"The current date and time is {current_time}. User question: {query}",
            "chat_history": st.session_state.chat_history
}
        

        result = qa_chain.invoke(full_context_query, config=RunnableConfig(tags=["ramchat"]))

        answer = result.get("answer", "").strip()
        sources = result.get("source_documents", [])

        if not answer or answer.lower() in ["i don't know.", ""]:
            answer = "I'm sorry, I couldn't find anything related to that in the Cate resources."

        st.session_state.chat_history.append((query, answer))
        st.session_state.source_history.append(sources)

# ==== Display chat history ====
for idx in reversed(range(len(st.session_state.chat_history))):
    q, a = st.session_state.chat_history[idx]
    sources = st.session_state.source_history[idx]

    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        st.markdown(a)
        if sources:
            with st.expander("See sources"):
                for i, src in enumerate(sources, start=1):
                    st.markdown(f"**Source {i}:** {src.metadata.get('source', 'Unknown')}")
                    st.markdown(src.page_content[:500] + "...")
