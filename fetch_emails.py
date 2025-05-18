import imaplib
import email
from email.header import decode_header
import sqlite3
import os
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdfplumber
from datetime import datetime

# ==== CONFIG ====
EMAIL = "ai_chatbot@cate.org"
PASSWORD = "athk onqx iihk dpcb"  # your app password
IMAP_SERVER = "imap.gmail.com"
MAILBOX = "inbox"
DB_FILE = "emails.db"
ATTACHMENT_DIR = "attachments"
MAX_EMAILS = 100000000

# ==== LOGIN ====
try:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    print("✅ Logged into Gmail")
except Exception as e:
    print("❌ Login failed:", e)
    exit()

# ==== DB SETUP ====
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        sender TEXT,
        date TEXT,
        body TEXT,
        attachments TEXT
    )
""")
conn.commit()

# ==== FETCH EMAILS ====
mail.select(MAILBOX)
status, messages = mail.search(None, "ALL")
email_ids = messages[0].split()
if MAX_EMAILS:
    email_ids = email_ids[-MAX_EMAILS:]

for i in email_ids:
    res, msg_data = mail.fetch(i, "(RFC822)")
    for response in msg_data:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])

            # SUBJECT
            subject_raw = msg["Subject"]
            subject, encoding = decode_header(subject_raw or "")[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or "utf-8", errors="ignore")

            # SENDER
            sender = msg.get("From") or "(Unknown Sender)"

            # DATE
            raw_date = msg.get("Date")
            try:
                date_parsed = email.utils.parsedate_to_datetime(raw_date)
                date_str = date_parsed.strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = raw_date or "(Unknown Date)"

            # BODY
            body = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    disposition = str(part.get("Content-Disposition") or "")

                    # Plain text email content
                    if content_type == "text/plain" and "attachment" not in disposition:
                        try:
                            body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        except:
                            pass

                    # ==== Images (both attachments and inline) ====
                    if part.get_content_maintype() == 'image':
                        filename = part.get_filename()
                        if not filename:
                            # Inline images sometimes have no filename
                            filename = f"inline_image_{email_ids.index(i)}.png"

                        print(f"📷 Found image: {filename}")

                        if not os.path.exists(ATTACHMENT_DIR):
                            os.makedirs(ATTACHMENT_DIR)

                        filepath = os.path.join(ATTACHMENT_DIR, filename)
                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        attachments.append(filepath)

                        # === OCR on Image ===
                        try:
                            img = Image.open(filepath).convert("L")  # Grayscale
                            img = img.filter(ImageFilter.SHARPEN)
                            img = ImageEnhance.Contrast(img).enhance(5)
                            img = img.point(lambda p: p > 180 and 255)  # Strong threshold

                            # Resize larger
                            base_width = 1800
                            w_percent = base_width / float(img.size[0])
                            h_size = int(float(img.size[1]) * w_percent)
                            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

                            # OCR
                            custom_config = r'--oem 3 --psm 6'
                            text = pytesseract.image_to_string(img, config=custom_config)

                            print(f"🔎 OCR output for {filename}:")
                            print(repr(text.strip()))

                            if text.strip():
                                body += f"\n\n[OCR from {filename}]\n{text.strip()}"
                            else:
                                print(f"⚠️ No text found in {filename}")

                        except Exception as e:
                            print(f"❌ OCR failed for {filename}: {e}")

                    # ==== PDF Attachments ====
                    elif "attachment" in disposition:
                        filename = part.get_filename()
                        if filename and filename.lower().endswith(".pdf"):
                            decoded_name, enc = decode_header(filename)[0]
                            decoded_name = decoded_name.decode(enc or "utf-8", errors="ignore") if isinstance(decoded_name, bytes) else decoded_name
                            filepath = os.path.join(ATTACHMENT_DIR, decoded_name)

                            if not os.path.exists(ATTACHMENT_DIR):
                                os.makedirs(ATTACHMENT_DIR)
                            with open(filepath, "wb") as f:
                                f.write(part.get_payload(decode=True))
                            attachments.append(filepath)

                            print(f"📄 Found PDF: {decoded_name}")

                            try:
                                with pdfplumber.open(filepath) as pdf:
                                    pdf_text = "".join((page.extract_text() or "") for page in pdf.pages)
                                if pdf_text.strip():
                                    body += f"\n\n[PDF Text from {decoded_name}]\n{pdf_text.strip()}"
                                else:
                                    print(f"⚠️ No text extracted from {decoded_name}")
                            except Exception as e:
                                print(f"❌ PDF extract failed for {decoded_name}: {e}")
            else:
                try:
                    body += msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                except:
                    pass

            # === SAVE TO DB ===
            cursor.execute("""
                INSERT INTO emails (subject, sender, date, body, attachments)
                VALUES (?, ?, ?, ?, ?)
            """, (subject, sender, date_str, body, ";".join(attachments)))

conn.commit()
conn.close()
mail.logout()
print("✅ All emails with OCR saved to emails.db")
