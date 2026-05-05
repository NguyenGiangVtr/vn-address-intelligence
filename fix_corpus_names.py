#!/usr/bin/env python3
"""
fix_corpus_names.py

Fix corpus to actually remove type names using simple SUBSTRING approach
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def fix_corpus_names():
    """Fix corpus names by removing type prefixes using SUBSTRING."""
    
    print("Fixing corpus names with SUBSTRING method...")
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
    
    try:
        with conn.cursor() as cur:
            # Test SUBSTRING method first
            print("Testing SUBSTRING method...")
            cur.execute("""
                SELECT 
                    'Phường Thanh Lương' as original,
                    SUBSTRING('Phường Thanh Lương' FROM 8) as cleaned,
                    LENGTH('Phường Thanh Lương') as orig_len,
                    LENGTH(SUBSTRING('Phường Thanh Lương' FROM 8)) as clean_len
            """)
            
            test = cur.fetchone()
            print(f"Test: {test[2]} -> {test[3]} chars (should be shorter)")
            
            # Truncate and recreate with proper name cleaning
            print("Truncating existing corpus...")
            cur.execute("TRUNCATE TABLE prq.address_clean_corpus RESTART IDENTITY CASCADE")
            
            # Simple insert with SUBSTRING cleanup
            print("Inserting with SUBSTRING cleanup...")
            
            insert_query = """
                INSERT INTO prq.address_clean_corpus (
                    standardized_address,
                    source_type,
                    source_id,
                    province_id,
                    province_name,
                    district_id,
                    district_name,
                    ward_id,
                    ward_name,
                    admin_epoch,
                    admin_version,
                    quality_score,
                    effective_date,
                    created_by
                )
                SELECT 
                    CASE 
                        WHEN w.admin_version = 2 THEN
                            -- Version 2: ward + province only
                            CASE 
                                WHEN w.ward_name LIKE 'Phường %' THEN SUBSTRING(w.ward_name FROM 8)
                                WHEN w.ward_name LIKE 'Xã %' THEN SUBSTRING(w.ward_name FROM 4)
                                WHEN w.ward_name LIKE 'Thị trấn %' THEN SUBSTRING(w.ward_name FROM 9)
                                ELSE w.ward_name 
                            END || ', ' ||
                            CASE 
                                WHEN p.province_name LIKE 'Thành phố %' THEN SUBSTRING(p.province_name FROM 11)
                                WHEN p.province_name LIKE 'Tỉnh %' THEN SUBSTRING(p.province_name FROM 6)
                                ELSE p.province_name 
                            END
                        ELSE
                            -- Version 1: ward + district + province
                            CASE 
                                WHEN w.ward_name LIKE 'Phường %' THEN SUBSTRING(w.ward_name FROM 8)
                                WHEN w.ward_name LIKE 'Xã %' THEN SUBSTRING(w.ward_name FROM 4)
                                WHEN w.ward_name LIKE 'Thị trấn %' THEN SUBSTRING(w.ward_name FROM 9)
                                ELSE w.ward_name 
                            END || ', ' ||
                            CASE 
                                WHEN d.district_name LIKE 'Quận %' THEN SUBSTRING(d.district_name FROM 6)
                                WHEN d.district_name LIKE 'Huyện %' THEN SUBSTRING(d.district_name FROM 7)
                                WHEN d.district_name LIKE 'Thành phố %' THEN SUBSTRING(d.district_name FROM 11)
                                WHEN d.district_name LIKE 'Thị xã %' THEN SUBSTRING(d.district_name FROM 8)
                                ELSE d.district_name 
                            END || ', ' ||
                            CASE 
                                WHEN p.province_name LIKE 'Thành phố %' THEN SUBSTRING(p.province_name FROM 11)
                                WHEN p.province_name LIKE 'Tỉnh %' THEN SUBSTRING(p.province_name FROM 6)
                                ELSE p.province_name 
                            END
                    END as standardized_address,
                    
                    'ADMINISTRATIVE' as source_type,
                    w.ward_id as source_id,
                    p.province_id,
                    -- Clean province name
                    CASE 
                        WHEN p.province_name LIKE 'Thành phố %' THEN SUBSTRING(p.province_name FROM 11)
                        WHEN p.province_name LIKE 'Tỉnh %' THEN SUBSTRING(p.province_name FROM 6)
                        ELSE p.province_name 
                    END as province_name,
                    d.district_id,
                    -- Clean district name
                    CASE 
                        WHEN d.district_name LIKE 'Quận %' THEN SUBSTRING(d.district_name FROM 6)
                        WHEN d.district_name LIKE 'Huyện %' THEN SUBSTRING(d.district_name FROM 7)
                        WHEN d.district_name LIKE 'Thành phố %' THEN SUBSTRING(d.district_name FROM 11)
                        WHEN d.district_name LIKE 'Thị xã %' THEN SUBSTRING(d.district_name FROM 8)
                        ELSE d.district_name 
                    END as district_name,
                    w.ward_id,
                    -- Clean ward name
                    CASE 
                        WHEN w.ward_name LIKE 'Phường %' THEN SUBSTRING(w.ward_name FROM 8)
                        WHEN w.ward_name LIKE 'Xã %' THEN SUBSTRING(w.ward_name FROM 4)
                        WHEN w.ward_name LIKE 'Thị trấn %' THEN SUBSTRING(w.ward_name FROM 9)
                        ELSE w.ward_name 
                    END as ward_name,
                    '2025' as admin_epoch,
                    w.admin_version,
                    1.0000 as quality_score,
                    CURRENT_DATE as effective_date,
                    'FIXED_NAMES' as created_by
                    
                FROM mat.ward w
                JOIN mat.district d ON w.district_id = d.district_id 
                    AND d.admin_version = w.admin_version
                JOIN mat.province p ON d.province_id = p.province_id 
                    AND p.admin_version = d.admin_version
                WHERE w.is_deleted = false 
                  AND d.is_deleted = false 
                  AND p.is_deleted = false
            """
            
            cur.execute(insert_query)
            inserted = cur.rowcount
            conn.commit()
            
            print(f"Successfully inserted {inserted} records with cleaned names")
            
            # Verify the cleaning worked
            print("Verifying name cleanup...")
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN standardized_address LIKE '%Phường %' THEN 1 END) as has_phuong,
                    COUNT(CASE WHEN standardized_address LIKE '%Quận %' THEN 1 END) as has_quan,
                    COUNT(CASE WHEN standardized_address LIKE '%Tỉnh %' THEN 1 END) as has_tinh,
                    COUNT(*) as total,
                    AVG(LENGTH(standardized_address))::int as avg_length
                FROM prq.address_clean_corpus
            """)
            
            verify = cur.fetchone()
            print(f"Verification:")
            print(f"  Addresses with 'Phường': {verify[0]} (should be 0)")
            print(f"  Addresses with 'Quận': {verify[1]} (should be 0)")  
            print(f"  Addresses with 'Tỉnh': {verify[2]} (should be 0)")
            print(f"  Total records: {verify[3]}")
            print(f"  Average length: {verify[4]} chars")
            
            # Check by version
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(*) as count,
                    AVG(LENGTH(standardized_address))::int as avg_len,
                    COUNT(CASE WHEN standardized_address LIKE '%,%,%' THEN 1 END) as three_parts,
                    COUNT(CASE WHEN standardized_address LIKE '%,%' AND standardized_address NOT LIKE '%,%,%' THEN 1 END) as two_parts
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            version_stats = cur.fetchall()
            print(f"By version:")
            for version, count, avg_len, three_parts, two_parts in version_stats:
                print(f"  Version {version}: {count} records, avg {avg_len} chars, {three_parts} 3-parts, {two_parts} 2-parts")
                
            print("Corpus names fixed successfully!")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_corpus_names()