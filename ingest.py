import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from pdf2image import convert_from_path
import pytesseract

# Define the path to your PDF
pdf_path = "data/cate_handbook.pdf"

# Check if the file exists
if not os.path.isfile(pdf_path):
    raise FileNotFoundError(f"The file {pdf_path} does not exist.")

# Attempt to load the PDF
# Attempt to load the PDF
loader = PyPDFLoader(pdf_path)
documents = loader.load()

# If no usable text is extracted, perform OCR
if not any(doc.page_content.strip() for doc in documents):
    print("No usable text found in PDF. Performing OCR...")
    images = convert_from_path(pdf_path)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image)
    documents = [Document(page_content=text)]

# Split the text into chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = text_splitter.split_documents(documents)

# Check if there are valid chunks
if not docs:
    raise ValueError("No valid chunks to embed. PDF might be scanned images or empty.")

# Initialize the OpenAI Embeddings
embedding = OpenAIEmbeddings()

# Create the FAISS vector store
vectorstore = FAISS.from_documents(docs, embedding)

# Save the vector store to disk
vectorstore.save_local("faiss_index")
