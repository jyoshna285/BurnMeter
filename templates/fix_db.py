import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE users ADD COLUMN email TEXT;")
    print("✅ 'email' column added successfully.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Error: {e}")

conn.commit()
conn.close()
