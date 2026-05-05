#!/usr/bin/env python3
"""
Analyze admin_version mapping issue in address_cleansing_queue
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
        
        print('=== KIEM TRA ADDRESS_CLEANSING_QUEUE ===')
        with db.cursor() as cur:
            cur.execute('SELECT COUNT(*) as total FROM prq.address_cleansing_queue')
            total_count = cur.fetchone()['total']
            print(f'Tong so records: {total_count}')
            
            # Kiem tra admin_version cua mat.province/district/ward duoc reference
            cur.execute('''
                SELECT 
                    'Province' as level,
                    p.admin_version,
                    COUNT(*) as count
                FROM prq.address_cleansing_queue acq
                JOIN mat.province p ON acq.province_id = p.province_id
                GROUP BY p.admin_version
                UNION ALL
                SELECT 
                    'District' as level,
                    d.admin_version,
                    COUNT(*) as count
                FROM prq.address_cleansing_queue acq
                JOIN mat.district d ON acq.district_id = d.district_id
                GROUP BY d.admin_version
                UNION ALL
                SELECT 
                    'Ward' as level,
                    w.admin_version,
                    COUNT(*) as count
                FROM prq.address_cleansing_queue acq
                JOIN mat.ward w ON acq.ward_id = w.ward_id
                GROUP BY w.admin_version
                ORDER BY level, admin_version
            ''')
            results = cur.fetchall()
            print('\nPhan bo admin_version trong du lieu referenced:')
            for r in results:
                level = r['level']
                version = r['admin_version']
                count = r['count']
                print(f'{level:<10} admin_version={version:<3} count={count}')
        
        print('\n=== KIEM TRA ADMIN_VERSION MAPPING ===')
        with db.cursor() as cur:
            # Kiem tra bang mapping
            cur.execute('SELECT COUNT(*) as total FROM mat.admin_unit_mapping')
            mapping_count = cur.fetchone()['total']
            print(f'Tong so mapping records: {mapping_count}')
            
            if mapping_count > 0:
                cur.execute('''
                    SELECT level, admin_version, COUNT(*) as count
                    FROM mat.admin_unit_mapping
                    GROUP BY level, admin_version
                    ORDER BY level, admin_version
                ''')
                mapping_results = cur.fetchall()
                print('Phan bo mapping theo level va admin_version:')
                for r in mapping_results:
                    level = r['level']
                    version = r['admin_version'] 
                    count = r['count']
                    print(f'Level {level:<3} admin_version={version:<3} count={count}')
        
        print('\n=== SAMPLE DATA COMPARISON ===')
        with db.cursor() as cur:
            # Lay 3 sample de so sanh
            cur.execute('''
                SELECT 
                    acq.id, acq.raw_address,
                    acq.ward_id, acq.district_id, acq.province_id,
                    w1.ward_name as ward_v1, d1.district_name as dist_v1, p1.province_name as prov_v1,
                    w2.ward_name as ward_v2, d2.district_name as dist_v2, p2.province_name as prov_v2
                FROM prq.address_cleansing_queue acq
                LEFT JOIN mat.ward w1 ON acq.ward_id = w1.ward_id AND w1.admin_version = 1
                LEFT JOIN mat.district d1 ON acq.district_id = d1.district_id AND d1.admin_version = 1
                LEFT JOIN mat.province p1 ON acq.province_id = p1.province_id AND p1.admin_version = 1
                LEFT JOIN mat.ward w2 ON acq.ward_id = w2.ward_id AND w2.admin_version = 2
                LEFT JOIN mat.district d2 ON acq.district_id = d2.district_id AND d2.admin_version = 2
                LEFT JOIN mat.province p2 ON acq.province_id = p2.province_id AND p2.admin_version = 2
                LIMIT 3
            ''')
            samples = cur.fetchall()
            print('Sample comparison (admin_version 1 vs 2):')
            for s in samples:
                print(f'\nID: {s["id"]}')
                print(f'Raw: {s["raw_address"]}')
                print(f'V1: {s["prov_v1"]} / {s["dist_v1"]} / {s["ward_v1"]}')
                print(f'V2: {s["prov_v2"]} / {s["dist_v2"]} / {s["ward_v2"]}')
                
        db.disconnect()
        print('\nDatabase analysis completed')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()