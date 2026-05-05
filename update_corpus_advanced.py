#!/usr/bin/env python3
"""
update_corpus_advanced.py

Advanced corpus update with:
1. Type name cleanup (remove Phường, Quận, Tỉnh prefixes)
2. Admin version-specific address formatting
3. Structured address components
"""

import os
import psycopg2
from dotenv import load_dotenv
import json

load_dotenv()

def clean_administrative_name(name, name_type):
    """
    Remove type prefixes from administrative names.
    
    Args:
        name: Original name with type prefix
        name_type: 'ward', 'district', or 'province'
        
    Returns:
        Cleaned name without type prefix
    """
    if not name:
        return name
        
    # Define type prefixes to remove
    if name_type == 'ward':
        prefixes = ['Phường ', 'Xã ', 'Thị trấn ']
    elif name_type == 'district':
        prefixes = ['Quận ', 'Huyện ', 'Thành phố ', 'Thị xã ']
    elif name_type == 'province':
        prefixes = ['Thành phố ', 'Tỉnh ']
    else:
        return name
    
    # Remove prefix if found
    for prefix in prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]
    
    return name

def create_address_components(ward_name, district_name, province_name, admin_version):
    """
    Create structured address components.
    
    Args:
        ward_name: Cleaned ward name
        district_name: Cleaned district name  
        province_name: Cleaned province name
        admin_version: Administrative version
        
    Returns:
        JSON structure with address components
    """
    components = {
        "level_3": ward_name,  # Ward/Commune level
        "level_1": province_name,  # Province/City level
        "admin_version": admin_version,
        "address_type": "administrative_hierarchy"
    }
    
    # Add district for admin_version = 1 only
    if admin_version == 1:
        components["level_2"] = district_name
        
    return components

def generate_standardized_address(ward_name, district_name, province_name, admin_version):
    """
    Generate standardized address based on admin version.
    
    Args:
        ward_name: Cleaned ward name
        district_name: Cleaned district name
        province_name: Cleaned province name
        admin_version: Administrative version
        
    Returns:
        Standardized address string
    """
    if admin_version == 2:
        # Version 2: ward + province only
        return f"{ward_name}, {province_name}"
    else:
        # Version 1: ward + district + province  
        return f"{ward_name}, {district_name}, {province_name}"

def update_corpus_advanced():
    """Update corpus with advanced name cleanup and version logic."""
    
    print("🔄 Starting advanced corpus update...")
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
    
    try:
        with conn.cursor() as cur:
            # 1. Truncate existing corpus
            print("1. Truncating existing corpus...")
            cur.execute("TRUNCATE TABLE prq.address_clean_corpus RESTART IDENTITY CASCADE")
            conn.commit()
            
            # 2. Insert with advanced logic
            print("2. Inserting with advanced name cleanup and version logic...")
            
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
                            REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g') || ', ' ||
                            REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g')
                        ELSE
                            REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g') || ', ' ||
                            REGEXP_REPLACE(d.district_name, '^(Quận|Huyện|Thành phố|Thị xã)\\s+', '', 'g') || ', ' ||
                            REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g')
                    END as standardized_address,
                    
                    CASE 
                        WHEN w.admin_version = 2 THEN
                            jsonb_build_object(
                                'level_3', REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g'),
                                'level_1', REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g'),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy'
                            )
                        ELSE
                            jsonb_build_object(
                                'level_3', REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g'),
                                'level_2', REGEXP_REPLACE(d.district_name, '^(Quận|Huyện|Thành phố|Thị xã)\\s+', '', 'g'),
                                'level_1', REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g'),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy'
                            )
                    END as address_components,
                    
                    'ADMINISTRATIVE' as source_type,
                    w.ward_id as source_id,
                    p.province_id,
                    REGEXP_REPLACE(p.province_name, '^(Thành phố|Tỉnh)\\s+', '', 'g') as province_name,
                    d.district_id,
                    REGEXP_REPLACE(d.district_name, '^(Quận|Huyện|Thành phố|Thị xã)\\s+', '', 'g') as district_name,
                    w.ward_id,
                    REGEXP_REPLACE(w.ward_name, '^(Phường|Xã|Thị trấn)\\s+', '', 'g') as ward_name,
                    '2025' as admin_epoch,
                    w.admin_version,
                    1.0000 as quality_score,
                    CURRENT_DATE as effective_date,
                    'ADVANCED_UPDATE' as created_by
                    
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
            
            print(f"   ✅ Inserted {inserted} records with advanced logic")
            
            # 3. Verify results
            print("3. Verifying results...")
            
            # Check by admin_version
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(*) as count,
                    COUNT(CASE WHEN standardized_address LIKE '%,%,%' THEN 1 END) as three_parts,
                    COUNT(CASE WHEN standardized_address LIKE '%,%' AND standardized_address NOT LIKE '%,%,%' THEN 1 END) as two_parts,
                    AVG(LENGTH(standardized_address))::int as avg_length
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            results = cur.fetchall()
            print("   Admin Version | Count | 3-Parts | 2-Parts | Avg Length")
            print("   --------------|-------|---------|---------|----------")
            for version, count, three_parts, two_parts, avg_len in results:
                print(f"   {version:12} | {count:5} | {three_parts:7} | {two_parts:7} | {avg_len:8}")
            
            # Check address components structure
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(CASE WHEN address_components ? 'level_2' THEN 1 END) as has_district,
                    COUNT(CASE WHEN address_components ? 'level_1' THEN 1 END) as has_province,
                    COUNT(CASE WHEN address_components ? 'level_3' THEN 1 END) as has_ward
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            components_stats = cur.fetchall()
            print("\\n   Version | Has District | Has Province | Has Ward")
            print("   --------|--------------|--------------|----------")
            for version, has_district, has_province, has_ward in components_stats:
                print(f"   {version:7} | {has_district:12} | {has_province:12} | {has_ward:8}")
                
            # Sample records
            print("\\n4. Sample records:")
            cur.execute("""
                SELECT admin_version, standardized_address, address_components
                FROM prq.address_clean_corpus
                ORDER BY admin_version, id
                LIMIT 4
            """)
            
            samples = cur.fetchall()
            for version, addr, components in samples:
                print(f"   v{version}: {addr}")
                print(f"        Components: {json.dumps(components, ensure_ascii=False)}")
                print()
            
            print("🎉 Advanced corpus update completed successfully!")
            
    except Exception as e:
        print(f"❌ Error during update: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_corpus_advanced()