from app.core.database import engine, sql_text
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def patch_administrative_tables():
    """
    Adds SCD (Slowly Changing Dimension) columns to administrative tables (province, district, ward)
    if they are missing. This is necessary for the NSO sync and SCD sync services.
    """
    tables = ['province', 'district', 'ward']
    
    with engine.connect() as conn:
        for table in tables:
            logger.info(f"Checking and patching table mat.{table}...")
            
            # 1. Add SCD columns
            # valid_from / valid_to: khoảng hiệu lực
            # is_active: dòng đại diện hiện tại (UI/API); thay thế is_current (xem migration 20260512_*)
            # version_id / predecessor_id: chuỗi thay thế

            queries = [
                f"ALTER TABLE mat.{table} ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP DEFAULT NOW()",
                f"ALTER TABLE mat.{table} ADD COLUMN IF NOT EXISTS valid_to TIMESTAMP DEFAULT '9999-12-31'",
                f"ALTER TABLE mat.{table} ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
                f"ALTER TABLE mat.{table} ADD COLUMN IF NOT EXISTS version_id INTEGER DEFAULT 1",
                f"ALTER TABLE mat.{table} ADD COLUMN IF NOT EXISTS predecessor_id INTEGER",
            ]
            
            for q in queries:
                try:
                    conn.execute(sql_text(q))
                    logger.info(f"  OK: {q.split('ADD COLUMN')[1].strip()}")
                except Exception as e:
                    logger.error(f"  Failed to execute {q}: {e}")
            
            # 2. Add Foreign Key for predecessor_id
            fk_name = f"fk_{table}_predecessor"
            fk_query = f"ALTER TABLE mat.{table} ADD CONSTRAINT {fk_name} FOREIGN KEY (predecessor_id) REFERENCES mat.{table}(row_id)"
            
            try:
                # Check if FK exists in PostgreSQL
                check_fk = sql_text(f"""
                    SELECT count(*) FROM information_schema.table_constraints 
                    WHERE constraint_name='{fk_name}' AND table_name='{table}'
                """)
                exists = conn.execute(check_fk).scalar()
                if not exists:
                    conn.execute(sql_text(fk_query))
                    logger.info(f"  Added FK constraint: {fk_name}")
                else:
                    logger.info(f"  FK constraint already exists: {fk_name}")
            except Exception as e:
                logger.warning(f"  Could not add FK for mat.{table}: {e}")

        conn.commit()
    logger.info("✅ Database administrative tables patched successfully.")

if __name__ == "__main__":
    patch_administrative_tables()
