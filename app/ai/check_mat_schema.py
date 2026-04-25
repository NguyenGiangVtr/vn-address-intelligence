from utils.config_loader import load_config_with_env
import psycopg2

cfg = load_config_with_env("app/ai/config.yaml")["database"]

conn = psycopg2.connect(
    host=cfg["host"], port=cfg["port"],
    dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"]
)
cur = conn.cursor()

for table in ["mat.province", "mat.district", "mat.ward"]:
    print(f"\n=== Columns of {table} ===")
    parts = table.split('.')
    schema, tname = parts[0], parts[1]
    cur.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = '{schema}' AND table_name = '{tname}'
        ORDER BY ordinal_position
    """)
    for r in cur.fetchall():
        print(f"  {r[0]:<20} {r[1]}")

cur.close()
conn.close()
