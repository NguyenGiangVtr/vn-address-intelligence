import sys
import os
sys.path.append(os.getcwd())
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("Adding district_id_new column...")
    conn.execute(text("ALTER TABLE mat.ward_mapping ADD COLUMN IF NOT EXISTS district_id_new INTEGER"))
    conn.commit()
    print("Done.")
