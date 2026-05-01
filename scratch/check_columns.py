import sys
import os
sys.path.append(os.getcwd())
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'mat' AND table_name = 'ward_mapping'")).fetchall()
    print([r[0] for r in res])
finally:
    db.close()
