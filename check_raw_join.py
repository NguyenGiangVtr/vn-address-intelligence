
from sqlalchemy import create_engine, text
from app.core.config import Config

def check_raw_join():
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Checking raw join result...")
        query = text("""
            SELECT m.ward_mapping_id, w.ward_name, d.district_name, p.province_name
            FROM mat.ward_mapping m
            LEFT JOIN mat.ward w ON m.ward_id_old = w.ward_id AND w.admin_version = 1
            LEFT JOIN mat.district d ON m.district_id_old = d.district_id AND d.admin_version = 1
            LEFT JOIN mat.province p ON m.province_id_old = p.province_id AND p.admin_version = 1
            WHERE m.is_deleted = false
            LIMIT 5
        """)
        result = conn.execute(query).fetchall()
        for row in result:
            print(f"ID: {row[0]}, Ward: {row[1] is not None}, Dist: {row[2] is not None}, Prov: {row[3] is not None}")

if __name__ == "__main__":
    check_raw_join()
