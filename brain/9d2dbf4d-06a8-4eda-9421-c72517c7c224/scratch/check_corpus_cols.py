from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("--- address_clean_corpus ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'address_clean_corpus'"))
    print(", ".join([r[0] for r in res]))
