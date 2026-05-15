from app.core.database import engine
from sqlalchemy import text

table = "mat.ward_mapping"

with engine.connect() as conn:
    print(f"--- {table} ---")
    res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema || '.' || table_name = '{table}'"))
    cols = [r[0] for r in res.fetchall()]
    print(", ".join(cols))
