from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    res = conn.execute(text("SELECT indexname FROM pg_indexes WHERE tablename = 'ward' AND schemaname = 'mat' AND indexdef LIKE '%old_id%'"))
    for r in res:
        print(r[0])
