import sqlite3
import json

conn = sqlite3.connect("ai_jobs.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== PROFILES ===")
cur.execute("SELECT id, experience, skills, projects FROM profiles")
for row in cur.fetchall():
    exp = json.loads(row["experience"]) if row["experience"] else []
    skills = json.loads(row["skills"]) if row["skills"] else []
    projects = json.loads(row["projects"]) if row["projects"] else []
    print(f"Profile ID: {row['id']}")
    print(f"  Experiences ({len(exp)}): {[e.get('company') for e in exp]}")
    print(f"  Skills ({len(skills)}): {[s.get('name') for s in skills]}")
    print(f"  Projects ({len(projects)}): {[p.get('name') for p in projects]}")

print("\n=== RESUMES ===")
cur.execute("SELECT id, content FROM resumes ORDER BY created_at DESC LIMIT 3")
for row in cur.fetchall():
    content = json.loads(row["content"]) if row["content"] else {}
    exp = content.get("experience", [])
    skills = content.get("skills", [])
    projects = content.get("projects", [])
    print(f"Resume ID: {row['id']}")
    print(f"  Experiences ({len(exp)}): {[e.get('company') for e in exp]}")
    print(f"  Skills ({len(skills)}): {[s.get('name') for s in skills]}")
    print(f"  Projects ({len(projects)}): {[p.get('name') for p in projects]}")

conn.close()
