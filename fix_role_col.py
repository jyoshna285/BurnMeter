import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';")
    conn.commit()
    print("✅ 'role' column added with default='user'.")
except sqlite3.OperationalError as e:
    print("⚠️ Already exists or failed:", e)

conn.close()
