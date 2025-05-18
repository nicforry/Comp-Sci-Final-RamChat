import imaplib

EMAIL = "ai_chatbot@cate.org"
PASSWORD = "C@teChatb0t!"
IMAP_SERVER = "outlook.office365.com"  # Try Gmail first if this fails

try:
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    print("✅ Login successful via Outlook IMAP")
    mail.logout()
except Exception as e:
    print("❌ Outlook IMAP login failed:", e)

