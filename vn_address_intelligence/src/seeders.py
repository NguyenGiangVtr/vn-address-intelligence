import pandas as pd
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import engine, SessionLocal, Province, District, Ward, AddressCleansingQueue, OSMStreet, OSMBuilding, OSMPoi, OSMRawEntity, TrainingDataset
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Seeders")

def seed_master_data(data_dir: str):
    session = SessionLocal()
    data_path = Path(data_dir)
    try:
        session.execute(text("TRUNCATE TABLE mat.ward, mat.district, mat.province CASCADE"))
        session.commit()
        logger.info("🧹 Cleaned mat schema.")

        # Seed Province
        f = data_path / "province.csv"
        if f.exists():
            df = pd.read_csv(f).where(pd.notnull(pd.read_csv(f)), None)
            session.bulk_save_objects([Province(**row) for row in df.to_dict(orient="records")])
            logger.info(f"OK: Seeded {len(df)} provinces.")

        # Seed District
        f = data_path / "district.csv"
        if f.exists():
            df = pd.read_csv(f).where(pd.notnull(pd.read_csv(f)), None)
            session.bulk_save_objects([District(**row) for row in df.to_dict(orient="records")])
            logger.info(f"OK: Seeded {len(df)} districts.")

        # Seed Ward
        f = data_path / "ward.csv"
        if f.exists():
            df = pd.read_csv(f).where(pd.notnull(pd.read_csv(f)), None)
            session.bulk_save_objects([Ward(**row) for row in df.to_dict(orient="records")])
            logger.info(f"OK: Seeded {len(df)} wards.")

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error seeding: {e}")
    finally:
        session.close()

def seed_cleansing_queue(csv_path: str):
    session = SessionLocal()
    try:
        session.execute(text("TRUNCATE TABLE prq.address_cleansing_queue RESTART IDENTITY"))
        session.commit()

        batch_size = 5000
        reader = pd.read_csv(csv_path, chunksize=batch_size)
        ignore_cols = ['id', 'created_at', 'updated_at']
        valid_cols = [c.name for c in AddressCleansingQueue.__table__.columns if c.name not in ignore_cols]
        
        total_seeded = 0
        for chunk in reader:
            chunk = chunk.where(pd.notnull(chunk), None)
            records = []
            for _, row in chunk.iterrows():
                data = {k: (None if pd.isna(v) or v == 'NaN' else v) for k, v in row.to_dict().items()}
                for json_col in ['phobert_parsed_components', 'mgte_parsed_components', 'phobert_embedding', 'mgte_embedding']:
                    val = data.get(json_col)
                    if val and isinstance(val, (str, dict, list)):
                        try:
                            if isinstance(val, str): val = json.loads(val)
                            data[json_col] = json.dumps(val, ensure_ascii=False)
                        except: data[json_col] = None
                    else: data[json_col] = None

                record = {k: v for k, v in data.items() if k in valid_cols}
                if not record.get('processing_status'): record['processing_status'] = 'PENDING'
                records.append(record)

            if records:
                col_names = ", ".join(records[0].keys())
                placeholders = ", ".join([f":{k}" for k in records[0].keys()])
                query = text(f"INSERT INTO prq.address_cleansing_queue ({col_names}) VALUES ({placeholders})")
                session.execute(query, records)
                session.commit()
                total_seeded += len(records)
                logger.info(f"📦 Seeded {total_seeded} rows...")
        logger.info(f"✅ DONE: Total seeded {total_seeded} rows.")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ ERROR: {e}")
    finally:
        session.close()

def check_database_stats():
    session = SessionLocal()
    stats = {}
    try:
        stats['mat.province'] = session.query(Province).count()
        stats['mat.district'] = session.query(District).count()
        stats['mat.ward'] = session.query(Ward).count()
        stats['osm.streets'] = session.query(OSMStreet).count()
        stats['osm.buildings'] = session.query(OSMBuilding).count()
        stats['osm.raw_entities'] = session.query(OSMRawEntity).count()
        stats['ath.training_datasets'] = session.query(TrainingDataset).count()
        stats['prq.address_cleansing_queue'] = session.query(AddressCleansingQueue).count()
    except Exception as e:
        logger.error(f"Stats Error: {e}")
    finally:
        session.close()
    return stats
