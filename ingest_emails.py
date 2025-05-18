import sqlite3
from dotenv import load_dotenv
import os
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_openai import OpenAIEmbeddings

# ==== Load environment variables ====
load_dotenv()

# ==== Load email data from SQLite ====
db_path = "emails.db"  # Your SQLite database file

if not os.path.isfile(db_path):
    raise FileNotFoundError(f"Database file {db_path} not found.")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ✅ Fetch subject, body, and date fields
cursor.execute("SELECT subject, body, date FROM emails")
rows = cursor.fetchall()
conn.close()

if not rows:
    raise ValueError("No emails found in database!")

# ==== Create Documents with metadata ====
documents = []
for subject, body, date_str in rows:
    content = f"Subject: {subject}\n\n{body}"
    metadata = {"date": date_str}  # ✅ Store email date as metadata
    documents.append(Document(page_content=content, metadata=metadata))

# ==== Split into chunks ====
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

if not docs:
    raise ValueError("No valid document chunks created.")

# ==== Embed and save to FAISS ====
embedding = OpenAIEmbeddings()

vectorstore = FAISS.from_documents(docs, embedding)

vectorstore.save_local("faiss_index")  # ✅ Save to faiss_index folder
print("✅ Vectorstore created and saved from emails with metadata!")
