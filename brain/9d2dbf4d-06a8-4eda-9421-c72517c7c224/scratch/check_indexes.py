from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("--- Province Indexes ---")
    res = conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'mat' AND tablename = 'province'")).fetchall()
    for r in res:
        print(r)
        
    print("\n--- District Indexes ---")
    res = conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'mat' AND tablename = 'district'")).fetchall()
    for r in res:
        print(r)
        
    print("\n--- Ward Indexes ---")
    res = conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'mat' AND tablename = 'ward'")).fetchall()
    for r in res:
        print(r)
