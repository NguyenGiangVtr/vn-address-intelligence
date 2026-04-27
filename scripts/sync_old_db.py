import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert
from app.core.config import Config
from app.core.database import SessionLocal, Province, District, Ward, WardMapping

def sync_data():
    if not Config.OLD_DB_HOST:
        print("Missing OLD_DB_HOST config in .env. Please fill in OLD_DB_* variables.")
        return
        
    print(f"Connecting to old database at {Config.OLD_DB_HOST}...")
    old_engine = create_engine(Config.OLD_SQLALCHEMY_DATABASE_URL)
    new_engine = SessionLocal().get_bind()
    
    metadata = MetaData()
    print("Reflecting old database schema 'mat'...")
    try:
        metadata.reflect(bind=old_engine, schema="mat")
    except Exception as e:
        print(f"Failed to reflect old database schema: {e}")
        return
    
    # Những cột này chỉ tồn tại ở DB mới, không update từ DB cũ
    excluded_columns = {"population", "area_km2", "decision_number", "decision_date", "notes"}
    
    # Mapping model to expected old table names (case-insensitive)
    models_mapping = {
        "province": Province,
        "district": District,
        "ward": Ward,
        "ward_mapping": WardMapping
    }
    
    with new_engine.connect() as new_conn:
        for expected_name, model_class in models_mapping.items():
            # Find the actual table name in old DB by case-insensitive matching
            old_table_key = None
            for key in metadata.tables.keys():
                # key is usually "schema.tablename"
                if key.lower() == f"mat.{expected_name}":
                    old_table_key = key
                    break
            
            if not old_table_key:
                print(f"Table {expected_name} not found in old database (schema 'mat').")
                continue
                
            print(f"Syncing table {old_table_key} to mat.{expected_name}...")
            old_table = metadata.tables[old_table_key]
            
            with old_engine.connect() as old_conn:
                rows = old_conn.execute(old_table.select()).mappings().all()
                
            if not rows:
                print(f"No data found in {old_table_key}")
                continue
                
            valid_columns = {c.name for c in model_class.__table__.columns}
            data = [{k: v for k, v in dict(row).items() if k in valid_columns} for row in rows]
            
            # Upsert using PostgreSQL INSERT ... ON CONFLICT DO UPDATE
            stmt = insert(model_class).values(data)
            
            # Get primary key columns for this table
            pk_cols = [c.name for c in model_class.__table__.primary_key.columns]
            
            # Build SET clause: update all columns except primary keys and explicitly excluded columns
            update_cols = {}
            for c in stmt.excluded:
                # Do not update primary keys
                if c.name in pk_cols:
                    continue
                # Do not override excluded columns if they are not in the source DB
                if c.name in excluded_columns:
                    continue
                update_cols[c.name] = c

            if not update_cols:
                # If there are no columns to update, just ignore on conflict
                upsert_stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
            else:
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=pk_cols,
                    set_=update_cols
                )
            
            try:
                new_conn.execute(upsert_stmt)
                new_conn.commit()
                print(f"Successfully synced {len(data)} rows for {expected_name}")
            except Exception as e:
                print(f"Error syncing {expected_name}: {e}")
                new_conn.rollback()

if __name__ == "__main__":
    sync_data()
