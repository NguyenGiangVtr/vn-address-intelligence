#!/usr/bin/env python3

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
        
        with db.cursor() as cur:
            # Check counts by admin_version and is_deleted
            print("PROVINCE counts:")
            cur.execute("""
                SELECT admin_version, is_deleted, COUNT(*) 
                FROM mat.province 
                GROUP BY admin_version, is_deleted 
                ORDER BY admin_version, is_deleted
            """)
            for r in cur.fetchall():
                print(f"  admin_version={r[0]}, is_deleted={r[1]}: {r[2]} records")
            
            print("\nDISTRICT counts:")
            cur.execute("""
                SELECT admin_version, is_deleted, COUNT(*) 
                FROM mat.district 
                GROUP BY admin_version, is_deleted 
                ORDER BY admin_version, is_deleted
            """)
            for r in cur.fetchall():
                print(f"  admin_version={r[0]}, is_deleted={r[1]}: {r[2]} records")
                
            print("\nWARD counts:")
            cur.execute("""
                SELECT admin_version, is_deleted, COUNT(*) 
                FROM mat.ward 
                GROUP BY admin_version, is_deleted 
                ORDER BY admin_version, is_deleted
            """)
            for r in cur.fetchall():
                print(f"  admin_version={r[0]}, is_deleted={r[1]}: {r[2]} records")
        
        db.disconnect()
        
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()