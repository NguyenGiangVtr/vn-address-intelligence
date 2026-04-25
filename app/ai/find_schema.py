import os
import psycopg2

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), 
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME"), 
    user=os.getenv("DB_USER"), 
    password=os.getenv("DB_PASS")
)
cur = conn.cursor()

# Xem các cột của bảng
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'scm'
      AND table_name   = 'output_fast_shipping_distinct'
    ORDER BY ordinal_position
""")
print("=== Columns of scm.output_fast_shipping_distinct ===")
for r in cur.fetchall():
    print(f"  {r[0]:<35} {r[1]:<20} nullable={r[2]}")

# Xem primary key
cur.execute("""
    SELECT kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema    = kcu.table_schema
    WHERE tc.constraint_type = 'PRIMARY KEY'
      AND tc.table_schema    = 'scm'
      AND tc.table_name      = 'output_fast_shipping_distinct'
""")
pks = cur.fetchall()
print(f"\n=== Primary Key ===")
for pk in pks:
    print(f"  {pk[0]}")

# Xem 2 dòng mẫu
cur.execute("SELECT * FROM scm.output_fast_shipping_distinct LIMIT 2")
rows = cur.fetchall()
cols = [d[0] for d in cur.description]
print(f"\n=== Sample rows (columns) ===")
print(cols)

cur.close()
conn.close()
