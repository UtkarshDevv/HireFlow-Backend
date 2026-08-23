import sqlite3

conn = sqlite3.connect("ai_jobs.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r["name"] for r in cur.fetchall()]
print("Tables:", tables)
print()

# Row counts per table
for t in tables:
    cur.execute(f"SELECT COUNT(*) as n FROM [{t}]")
    n = cur.fetchone()["n"]
    print(f"  {t}: {n} rows")

print()

# Show profiles sample
cur.execute("SELECT id, contact FROM profiles LIMIT 3")
rows = cur.fetchall()
if rows:
    print("--- profiles ---")
    for r in rows:
        print(f"  id={r['id'][:8]}...  contact={r['contact'][:60]}")

# Show jobs sample
cur.execute("SELECT id, company, title, match_score FROM jobs LIMIT 5")
rows = cur.fetchall()
if rows:
    print("--- jobs ---")
    for r in rows:
        print(f"  {r['company']} | {r['title']} | score={r['match_score']}")

# Show applications sample
cur.execute("SELECT id, status, applied_at FROM applications LIMIT 5")
rows = cur.fetchall()
if rows:
    print("--- applications ---")
    for r in rows:
        print(f"  id={r['id'][:8]}... status={r['status']} applied={r['applied_at']}")

conn.close()
