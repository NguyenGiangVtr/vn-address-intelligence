from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'idx_ward_lookup'"))
    print(res.fetchone()[0])
