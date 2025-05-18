import sqlite3

conn = sqlite3.connect("emails.db")
cursor = conn.cursor()
cursor.execute("SELECT id, subject, sender FROM emails ORDER BY id DESC LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row[0]}\nSubject: {row[1]}\nFrom: {row[2]}\n{'-'*40}")

conn.close()
