#!/usr/bin/env python3
"""
Debug script to analyze admin unit names between version 1 and 2
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.utils.config_loader import load_config_with_env

def main():
    try:
        cfg = load_config_with_env('app/ai/config.yaml')
        db = DBConnector(cfg['database'])
        db.connect()
        
        print('=== ADMIN VERSION COMPARISON ===')
        
        # Compare province names
        print('\n--- PROVINCES ---')
        with db.cursor() as cur:
            cur.execute("""
                SELECT 'v1' as version, province_id, province_name, is_deleted
                FROM mat.province 
                WHERE admin_version = 1 
                ORDER BY province_name
                LIMIT 5
            """)
            v1_provinces = cur.fetchall()
            
            cur.execute("""
                SELECT 'v2' as version, province_id, province_name, is_deleted
                FROM mat.province 
                WHERE admin_version = 2 
                ORDER BY province_name
                LIMIT 5
            """)
            v2_provinces = cur.fetchall()
            
            print("Version 1 (sample):")
            for p in v1_provinces:
                print(f"  ID:{p['province_id']:<3} {p['province_name']:<30} deleted:{p['is_deleted']}")
            
            print("\nVersion 2 (sample):")
            for p in v2_provinces:
                print(f"  ID:{p['province_id']:<3} {p['province_name']:<30} deleted:{p['is_deleted']}")
        
        # Check common patterns
        print('\n--- PROVINCE MATCHING PATTERNS ---')
        with db.cursor() as cur:
            cur.execute("""
                SELECT 
                    p1.province_id as v1_id,
                    p1.province_name as v1_name,
                    p2.province_id as v2_id,
                    p2.province_name as v2_name
                FROM mat.province p1
                CROSS JOIN mat.province p2
                WHERE p1.admin_version = 1 AND p2.admin_version = 2
                AND p1.is_deleted = TRUE AND p2.is_deleted = FALSE
                AND (
                    LOWER(TRIM(p1.province_name)) = LOWER(TRIM(p2.province_name))
                    OR p1.province_name ILIKE '%' || TRIM(SPLIT_PART(p2.province_name, ' ', -1)) || '%'
                    OR p2.province_name ILIKE '%' || TRIM(SPLIT_PART(p1.province_name, ' ', -1)) || '%'
                )
                LIMIT 10
            """)
            matches = cur.fetchall()
            
            if matches:
                print("Potential matches found:")
                for m in matches:
                    print(f"  v1:{m['v1_id']:<3} '{m['v1_name']:<25}' <-> v2:{m['v2_id']:<3} '{m['v2_name']}'")
            else:
                print("No direct matches found")
        
        # Check deletion status patterns
        print('\n--- DELETION STATUS ---')
        with db.cursor() as cur:
            for version in [1, 2]:
                cur.execute(f"""
                    SELECT is_deleted, COUNT(*) as count
                    FROM mat.province
                    WHERE admin_version = {version}
                    GROUP BY is_deleted
                """)
                results = cur.fetchall()
                print(f"Version {version}:")
                for r in results:
                    status = "deleted" if r['is_deleted'] else "active"
                    print(f"  {status}: {r['count']}")
        
        # Check if there are any similar names
        print('\n--- FUZZY MATCHING ANALYSIS ---')
        with db.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT
                    LOWER(REPLACE(REPLACE(REPLACE(province_name, 'Thành phố ', ''), 'Tỉnh ', ''), 'TP. ', '')) as cleaned_name
                FROM mat.province 
                WHERE admin_version = 1 AND is_deleted = TRUE
                ORDER BY cleaned_name
                LIMIT 10
            """)
            v1_cleaned = cur.fetchall()
            
            cur.execute("""
                SELECT DISTINCT
                    LOWER(REPLACE(REPLACE(REPLACE(province_name, 'Thành phố ', ''), 'Tỉnh ', ''), 'TP. ', '')) as cleaned_name
                FROM mat.province 
                WHERE admin_version = 2 AND is_deleted = FALSE
                ORDER BY cleaned_name
                LIMIT 10
            """)
            v2_cleaned = cur.fetchall()
            
            print("V1 cleaned names:")
            for p in v1_cleaned:
                print(f"  '{p['cleaned_name']}'")
            
            print("\nV2 cleaned names:")
            for p in v2_cleaned:
                print(f"  '{p['cleaned_name']}'")
        
        db.disconnect()
        print('\nDebug analysis completed')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()