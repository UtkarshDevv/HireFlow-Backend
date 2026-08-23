import sqlite3
import json

conn = sqlite3.connect("ai_jobs.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- PROFILES DATA ---")
cur.execute("SELECT id, contact, experience, skills, projects FROM profiles")
for r in cur.fetchall():
    exp = json.loads(r["experience"]) if r["experience"] else []
    skills = json.loads(r["skills"]) if r["skills"] else []
    print(f"Profile ID: {r['id']}")
    print("Experience companies:")
    for e in exp:
        print("  -", e.get("company"), "|", e.get("title"))
    print("Skills:")
    for s in skills:
        print("  -", s.get("category"), ":", s.get("name"))

print("\n--- RESUMES CONTENT ---")
cur.execute("SELECT id, content FROM resumes ORDER BY created_at DESC LIMIT 2")
for r in cur.fetchall():
    content = json.loads(r["content"]) if r["content"] else {}
    exp = content.get("experience", [])
    skills = content.get("skills", [])
    print(f"Resume ID: {r['id']}")
    print("Experience companies:")
    for e in exp:
        print("  -", e.get("company"), "|", e.get("title"))
    print("Skills categories:")
    by_cat = {}
    for s in skills:
        by_cat.setdefault(s.get("category"), []).append(s.get("name"))
    for cat, names in by_cat.items():
        print(f"  - {cat}: {names}")

conn.close()
