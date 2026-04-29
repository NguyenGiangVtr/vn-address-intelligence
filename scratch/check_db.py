from app.core.database import engine, text
try:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'ward_mapping'"))
        cols = [r[0] for r in res.fetchall()]
        print("Columns in ward_mapping:", cols)
except Exception as e:
    print("Error:", e)
