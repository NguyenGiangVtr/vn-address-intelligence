import os
import pandas as pd
from sqlalchemy import create_engine, text
import json

# Connection string
DB_URL = "postgresql://vnai_admin:vnai_admin%4097GHxafU@157.66.81.69:5432/vn_address_intelligence_db"
engine = create_engine(DB_URL)

OUTPUT_DIR = "evidence"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def export_enriched_provinces():
    print("Exporting Enriched Provinces...")
    query = "SELECT province_id, province_name, province_no, decision_number, decision_date, notes FROM mat.province WHERE admin_version = 2"
    df = pd.read_sql(query, engine)
    df.to_csv(f"{OUTPUT_DIR}/enriched_provinces_2025.csv", index=False, encoding='utf-8-sig')
    print(f"Saved to {OUTPUT_DIR}/enriched_provinces_2025.csv")

def export_ward_mapping_samples():
    print("Exporting Ward Mapping Samples...")
    # This table might be empty if seeding hasn't run, but let's try to get what we have
    query = """
        SELECT m.ward_mapping_id, 
               w1.ward_name as old_ward, 
               w2.ward_name as new_ward, 
               m.relationship_type, 
               m.updated_note
        FROM mat.ward_mapping m
        LEFT JOIN mat.ward w1 ON m.ward_id_old = w1.ward_id
        LEFT JOIN mat.ward w2 ON m.ward_id_new = w2.ward_id
        LIMIT 100
    """
    try:
        df = pd.read_sql(query, engine)
        if df.empty:
            # Fallback to a simple ward list if mapping is not fully populated
            query = "SELECT ward_id, ward_name, district_id FROM mat.ward LIMIT 100"
            df = pd.read_sql(query, engine)
            df.to_csv(f"{OUTPUT_DIR}/administrative_units_sample.csv", index=False, encoding='utf-8-sig')
        else:
            df.to_csv(f"{OUTPUT_DIR}/ward_mapping_2025_samples.csv", index=False, encoding='utf-8-sig')
            print(f"Saved to {OUTPUT_DIR}/ward_mapping_2025_samples.csv")
    except Exception as e:
        print(f"Error exporting mapping: {e}")

def export_training_data_samples():
    print("Exporting Training Data Samples...")
    query = "SELECT raw_text, ner_tags_json FROM ath.training_datasets LIMIT 500"
    df = pd.read_sql(query, engine)
    df.to_csv(f"{OUTPUT_DIR}/ner_training_samples_bio.csv", index=False, encoding='utf-8-sig')
    print(f"Saved to {OUTPUT_DIR}/ner_training_samples_bio.csv")

def export_database_stats_report():
    print("Generating Database Stats Report...")
    stats = []
    tables = [
        ("mat.province", "Provinces"),
        ("mat.district", "Districts"),
        ("mat.ward", "Wards"),
        ("osm.raw_entities", "OSM Raw Entities"),
        ("osm.streets", "OSM Streets"),
        ("ath.training_datasets", "Training Samples"),
        ("prq.address_cleansing_queue", "Processing Queue")
    ]
    
    with engine.connect() as conn:
        for table, desc in tables:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            stats.append({"Table": table, "Description": desc, "Count": count})
            
    df = pd.DataFrame(stats)
    df.to_csv(f"{OUTPUT_DIR}/database_volume_report.csv", index=False, encoding='utf-8-sig')
    print(f"Saved to {OUTPUT_DIR}/database_volume_report.csv")

if __name__ == "__main__":
    export_enriched_provinces()
    export_ward_mapping_samples()
    export_training_data_samples()
    export_database_stats_report()
    print("\n--- All evidence files have been exported to the 'evidence/' directory ---")
