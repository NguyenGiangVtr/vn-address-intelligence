from app.core.database import engine
from sqlalchemy import text

tables = ["prq.address_clean_corpus", "prq.address_cleansing_queue", "prq.ground_truth"]

with engine.connect() as conn:
    for table in tables:
        print(f"--- {table} ---")
        res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema || '.' || table_name = '{table}'"))
        cols = [r[0] for r in res.fetchall()]
        print(", ".join(cols))
