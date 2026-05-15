from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'address_clean_corpus'"))
    for r in res:
        print(r[0])
