from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print(conn.execute(text("SELECT COUNT(*) FROM prq.address_clean_corpus")).fetchone()[0])
