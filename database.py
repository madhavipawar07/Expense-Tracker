import sqlite3

# Connect to database (creates file if not exists)
conn = sqlite3.connect("app.db")

# Create cursor
cursor = conn.cursor()

# ---------------- USERS TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

# ---------------- EXPENSES TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    amount INTEGER,
    category TEXT,
    date TEXT
)
""")

# Add the date column if the table already exists without it
cursor.execute("PRAGMA table_info(expenses)")
columns = [row[1] for row in cursor.fetchall()]
if "date" not in columns:
    cursor.execute("ALTER TABLE expenses ADD COLUMN date TEXT")

# Save changes
conn.commit()
conn.close()

print("Database and tables created successfully!")
