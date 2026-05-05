#!/usr/bin/env python3
"""
update_corpus_type_name.py

Update corpus using type_name columns for accurate prefix removal.
This replaces hardcoded REPLACE strings with database-driven approach.

Usage:
    python app/ai/update_corpus_type_name.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def update_corpus_with_type_names():
    """Update corpus using type_name columns for accurate name cleaning."""
    
    print("🔄 Updating corpus with type_name based cleaning...")
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
    
    try:
        with conn.cursor() as cur:
            # 1. Drop unique constraint temporarily
            print("1. Dropping unique constraint temporarily...")
            cur.execute('ALTER TABLE prq.address_clean_corpus DROP CONSTRAINT IF EXISTS unique_standardized_address_epoch')
            
            # 2. Truncate existing corpus
            print("2. Truncating existing corpus...")
            cur.execute('TRUNCATE TABLE prq.address_clean_corpus RESTART IDENTITY CASCADE')
            
            # 3. Insert with type_name based cleaning
            print("3. Inserting with type_name based cleaning...")
            
            insert_query = """
                INSERT INTO prq.address_clean_corpus (
                    standardized_address,
                    address_components,
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
                            -- Version 2: ward + province (skip district)
                            REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                            REPLACE(p.province_name, p.type_name || ' ', '')
                        ELSE
                            -- Version 1: ward + district + province
                            REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                            REPLACE(d.district_name, d.type_name || ' ', '') || ', ' ||
                            REPLACE(p.province_name, p.type_name || ' ', '')
                    END as standardized_address,
                    
                    -- Structured address components
                    CASE 
                        WHEN w.admin_version = 2 THEN
                            jsonb_build_object(
                                'level_3', REPLACE(w.ward_name, w.type_name || ' ', ''),
                                'level_1', REPLACE(p.province_name, p.type_name || ' ', ''),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy',
                                'ward_type', w.type_name,
                                'province_type', p.type_name
                            )
                        ELSE
                            jsonb_build_object(
                                'level_3', REPLACE(w.ward_name, w.type_name || ' ', ''),
                                'level_2', REPLACE(d.district_name, d.type_name || ' ', ''),
                                'level_1', REPLACE(p.province_name, p.type_name || ' ', ''),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy',
                                'ward_type', w.type_name,
                                'district_type', d.type_name,
                                'province_type', p.type_name
                            )
                    END as address_components,
                    
                    'ADMINISTRATIVE' as source_type,
                    w.ward_id as source_id,
                    p.province_id,
                    REPLACE(p.province_name, p.type_name || ' ', '') as province_name,
                    d.district_id,
                    REPLACE(d.district_name, d.type_name || ' ', '') as district_name,
                    w.ward_id,
                    REPLACE(w.ward_name, w.type_name || ' ', '') as ward_name,
                    '2025' as admin_epoch,
                    w.admin_version,
                    1.0000 as quality_score,
                    CURRENT_DATE as effective_date,
                    'TYPE_NAME_CLEAN' as created_by
                    
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
            print(f"   ✅ Inserted {inserted} records with type_name cleaning")
            
            # 4. Remove duplicates (some addresses might be identical after cleaning)
            print("4. Removing duplicates...")
            cur.execute("""
                DELETE FROM prq.address_clean_corpus 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM prq.address_clean_corpus 
                    GROUP BY standardized_address, admin_epoch, source_type
                )
            """)
            
            removed = cur.rowcount
            print(f"   ✅ Removed {removed} duplicate records")
            
            # 5. Re-add unique constraint
            print("5. Re-adding unique constraint...")
            cur.execute('ALTER TABLE prq.address_clean_corpus ADD CONSTRAINT unique_standardized_address_epoch UNIQUE (standardized_address, admin_epoch, source_type)')
            
            conn.commit()
            
            # 6. Verify results
            print("6. Verification results:")
            
            # Basic statistics
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(*) as count,
                    AVG(LENGTH(standardized_address))::int as avg_len,
                    MIN(LENGTH(standardized_address)) as min_len,
                    MAX(LENGTH(standardized_address)) as max_len,
                    COUNT(CASE WHEN standardized_address LIKE '%,%,%' THEN 1 END) as three_parts,
                    COUNT(CASE WHEN standardized_address LIKE '%,%' AND standardized_address NOT LIKE '%,%,%' THEN 1 END) as two_parts
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            results = cur.fetchall()
            print("   📊 Statistics by admin version:")
            print("   Version | Count | Avg | Min | Max | 3-Parts | 2-Parts")
            print("   --------|-------|-----|-----|-----|---------|--------")
            for version, count, avg_len, min_len, max_len, three_parts, two_parts in results:
                print(f"   {version:7} | {count:5} | {avg_len:3} | {min_len:3} | {max_len:3} | {three_parts:7} | {two_parts:7}")
            
            # Check address components structure
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(CASE WHEN address_components ? 'level_1' THEN 1 END) as has_level_1,
                    COUNT(CASE WHEN address_components ? 'level_2' THEN 1 END) as has_level_2,
                    COUNT(CASE WHEN address_components ? 'level_3' THEN 1 END) as has_level_3,
                    COUNT(CASE WHEN address_components ? 'ward_type' THEN 1 END) as has_ward_type,
                    COUNT(CASE WHEN address_components ? 'district_type' THEN 1 END) as has_district_type
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            components = cur.fetchall()
            print("   📋 Address components structure:")
            print("   Version | Level1 | Level2 | Level3 | WardType | DistType")
            print("   --------|--------|--------|--------|----------|----------")
            for version, level1, level2, level3, ward_type, dist_type in components:
                print(f"   {version:7} | {level1:6} | {level2:6} | {level3:6} | {ward_type:8} | {dist_type:8}")
            
            # Sample records to verify cleaning
            cur.execute("""
                SELECT 
                    admin_version,
                    LENGTH(standardized_address) as addr_len,
                    address_components->>'level_3' as clean_ward,
                    address_components->>'ward_type' as ward_type
                FROM prq.address_clean_corpus
                ORDER BY admin_version, id
                LIMIT 4
            """)
            
            samples = cur.fetchall()
            print("   📝 Sample cleaned data:")
            print("   Version | Addr Len | Clean Ward Length | Ward Type Length")
            print("   --------|----------|-------------------|------------------")
            for version, addr_len, clean_ward, ward_type in samples:
                ward_len = len(clean_ward) if clean_ward else 0
                type_len = len(ward_type) if ward_type else 0
                print(f"   {version:7} | {addr_len:8} | {ward_len:17} | {type_len:16}")
            
            print("🎉 Corpus updated successfully with type_name based cleaning!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error during update: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_type_name_cleaning():
    """Verify that type_name based cleaning worked correctly."""
    
    print("🔍 Verifying type_name cleaning...")
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
    
    try:
        with conn.cursor() as cur:
            # Check for any remaining type prefixes in standardized_address
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN standardized_address ~ '(Phường|Xã|Thị trấn|Quận|Huyện|Tỉnh|Thành phố)\\s' THEN 1 END) as has_type_prefix
                FROM prq.address_clean_corpus
            """)
            
            check = cur.fetchone()
            total, has_prefix = check
            
            print(f"   Total records: {total}")
            print(f"   Records with type prefixes: {has_prefix} (should be 0)")
            
            if has_prefix == 0:
                print("   ✅ All type prefixes successfully removed!")
            else:
                print("   ⚠️  Some type prefixes remain - needs investigation")
                
                # Show sample problematic records
                cur.execute("""
                    SELECT standardized_address
                    FROM prq.address_clean_corpus
                    WHERE standardized_address ~ '(Phường|Xã|Thị trấn|Quận|Huyện|Tỉnh|Thành phố)\\s'
                    LIMIT 3
                """)
                
                problems = cur.fetchall()
                print("   Sample problematic addresses:")
                for addr in problems:
                    print(f"     - Length: {len(addr[0])} chars")
            
            return has_prefix == 0
            
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        # Update corpus
        success = update_corpus_with_type_names()
        
        if success:
            # Verify cleaning
            verify_type_name_cleaning()
            
        print("\n🚀 Type name based corpus update completed!")
        
    except Exception as e:
        print(f"\n💥 Update failed: {e}")
        exit(1)