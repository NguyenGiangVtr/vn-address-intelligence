#!/usr/bin/env python3
"""
Migration script: Cập nhật address_cleansing_queue từ admin_version=1 sang admin_version=2

Chức năng:
1. Tạo mapping table từ admin v1 sang v2 dựa trên tên tương ứng  
2. Cập nhật province_id, district_id, ward_id trong address_cleansing_queue
3. Validate dữ liệu sau khi migration
4. Tạo backup bảng trước khi migration

Usage:
    python scripts/migration/migrate_acq_to_admin_v2.py --validate-only
    python scripts/migration/migrate_acq_to_admin_v2.py --create-mapping-only
    python scripts/migration/migrate_acq_to_admin_v2.py --migrate
    python scripts/migration/migrate_acq_to_admin_v2.py --migrate --backup
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.db_connector import DBConnector
from app.ai.utils.config_loader import load_config_with_env

def create_backup_table(db):
    """Tạo backup bảng address_cleansing_queue"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_table = f"address_cleansing_queue_backup_{timestamp}"
    
    print(f"Creating backup table: prq.{backup_table}")
    
    with db.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE prq.{backup_table} AS 
            SELECT * FROM prq.address_cleansing_queue
        """)
        
        # Check backup count
        cur.execute(f"SELECT COUNT(*) as count FROM prq.{backup_table}")
        backup_count = cur.fetchone()['count']
        print(f"   Backup created with {backup_count:,} records")
    
    return backup_table

def create_admin_mapping_table(db):
    """Tạo bảng mapping giữa admin v1 và v2 dựa trên tên"""
    
    print("Creating admin version mapping...")
    
    with db.cursor() as cur:
        # Drop existing mapping table if exists
        cur.execute("DROP TABLE IF EXISTS temp.admin_v1_v2_mapping")
        
        # Create temp mapping table
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS temp;
            
            CREATE TABLE temp.admin_v1_v2_mapping (
                level VARCHAR(10) NOT NULL,
                v1_id INTEGER NOT NULL,
                v1_name VARCHAR(200),
                v2_id INTEGER,
                v2_name VARCHAR(200),
                match_type VARCHAR(20),  -- exact, fuzzy, manual
                confidence FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        print("   Creating Province mapping...")
        # Province mapping - tìm tên tương ứng
        cur.execute("""
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT 
                'province' as level,
                p1.province_id as v1_id,
                p1.province_name as v1_name,
                p2.province_id as v2_id,
                p2.province_name as v2_name,
                'exact' as match_type
            FROM mat.province p1
            JOIN mat.province p2 ON (
                p1.admin_version = 1 AND p2.admin_version = 2 AND
                (
                    -- Exact match
                    LOWER(TRIM(p1.province_name)) = LOWER(TRIM(p2.province_name))
                    -- Or common variations
                    OR (p1.province_name ILIKE '%Ho Chi Minh%' AND p2.province_name ILIKE '%Ho Chi Minh%')
                    OR (p1.province_name ILIKE '%Ha Noi%' AND p2.province_name ILIKE '%Ha Noi%')
                    OR (p1.province_name ILIKE '%Da Nang%' AND p2.province_name ILIKE '%Da Nang%')
                    OR (p1.province_name ILIKE '%Hai Phong%' AND p2.province_name ILIKE '%Hai Phong%')
                    OR (p1.province_name ILIKE '%Can Tho%' AND p2.province_name ILIKE '%Can Tho%')
                )
            )
            WHERE p1.is_deleted = TRUE AND p2.is_deleted = FALSE
        """)
        
        print("   Creating District mapping...")
        # District mapping
        cur.execute("""
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT 
                'district' as level,
                d1.district_id as v1_id,
                d1.district_name as v1_name,
                d2.district_id as v2_id,
                d2.district_name as v2_name,
                'exact' as match_type
            FROM mat.district d1
            JOIN mat.district d2 ON (
                d1.admin_version = 1 AND d2.admin_version = 2 AND
                LOWER(TRIM(d1.district_name)) = LOWER(TRIM(d2.district_name)) AND
                -- Ensure they belong to mapped provinces
                EXISTS (
                    SELECT 1 FROM temp.admin_v1_v2_mapping pm 
                    WHERE pm.level = 'province' 
                    AND pm.v1_id = d1.province_id 
                    AND pm.v2_id = d2.province_id
                )
            )
            WHERE d1.is_deleted = TRUE AND d2.is_deleted = FALSE
        """)
        
        print("   Creating Ward mapping...")
        # Ward mapping 
        cur.execute("""
            INSERT INTO temp.admin_v1_v2_mapping (level, v1_id, v1_name, v2_id, v2_name, match_type)
            SELECT 
                'ward' as level,
                w1.ward_id as v1_id,
                w1.ward_name as v1_name,
                w2.ward_id as v2_id,
                w2.ward_name as v2_name,
                'exact' as match_type
            FROM mat.ward w1
            JOIN mat.ward w2 ON (
                w1.admin_version = 1 AND w2.admin_version = 2 AND
                LOWER(TRIM(w1.ward_name)) = LOWER(TRIM(w2.ward_name)) AND
                -- Ensure they belong to mapped districts
                EXISTS (
                    SELECT 1 FROM temp.admin_v1_v2_mapping dm 
                    WHERE dm.level = 'district' 
                    AND dm.v1_id = w1.district_id 
                    AND dm.v2_id = w2.district_id
                )
            )
            WHERE w1.is_deleted = TRUE AND w2.is_deleted = FALSE
        """)
        
        # Get mapping statistics
        cur.execute("""
            SELECT level, COUNT(*) as mapping_count 
            FROM temp.admin_v1_v2_mapping 
            GROUP BY level 
            ORDER BY level
        """)
        results = cur.fetchall()
        
        print("   Mapping statistics:")
        for r in results:
            print(f"     {r['level']:<10}: {r['mapping_count']:,} mappings")
    
    return True

def validate_mapping_coverage(db):
    """Kiểm tra coverage của mapping so với dữ liệu trong address_cleansing_queue"""
    
    print("Validating mapping coverage...")
    
    with db.cursor() as cur:
        # Check coverage for each level
        for level in ['province', 'district', 'ward']:
            level_id = f"{level}_id"
            
            cur.execute(f"""
                SELECT 
                    COUNT(DISTINCT acq.{level_id}) as total_used,
                    COUNT(DISTINCT m.v1_id) as mapped_count,
                    ROUND(
                        COUNT(DISTINCT m.v1_id) * 100.0 / NULLIF(COUNT(DISTINCT acq.{level_id}), 0), 
                        2
                    ) as coverage_percent
                FROM prq.address_cleansing_queue acq
                LEFT JOIN temp.admin_v1_v2_mapping m ON (
                    m.level = '{level}' AND m.v1_id = acq.{level_id}
                )
                WHERE acq.{level_id} IS NOT NULL
            """)
            
            result = cur.fetchone()
            print(f"   {level.capitalize():<10}: {result['mapped_count']:,}/{result['total_used']:,} ({result['coverage_percent']}%)")
    
    return True

def migrate_address_cleansing_queue(db, dry_run=False):
    """Migration chính: cập nhật ID references trong address_cleansing_queue"""
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating address_cleansing_queue to admin_version=2...")
    
    with db.cursor() as cur:
        # Count records to be updated
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(pm.v2_id) as province_mappable,
                COUNT(dm.v2_id) as district_mappable,
                COUNT(wm.v2_id) as ward_mappable
            FROM prq.address_cleansing_queue acq
            LEFT JOIN temp.admin_v1_v2_mapping pm ON pm.level = 'province' AND pm.v1_id = acq.province_id
            LEFT JOIN temp.admin_v1_v2_mapping dm ON dm.level = 'district' AND dm.v1_id = acq.district_id  
            LEFT JOIN temp.admin_v1_v2_mapping wm ON wm.level = 'ward' AND wm.v1_id = acq.ward_id
        """)
        
        stats = cur.fetchone()
        print(f"   Records analysis:")
        print(f"     Total records: {stats['total']:,}")
        print(f"     Province mappable: {stats['province_mappable']:,}")
        print(f"     District mappable: {stats['district_mappable']:,}")
        print(f"     Ward mappable: {stats['ward_mappable']:,}")
        
        if not dry_run:
            print("   Updating province_id...")
            cur.execute("""
                UPDATE prq.address_cleansing_queue 
                SET province_id = pm.v2_id,
                    province_name = pm.v2_name
                FROM temp.admin_v1_v2_mapping pm
                WHERE pm.level = 'province' 
                AND pm.v1_id = address_cleansing_queue.province_id
            """)
            province_updated = cur.rowcount
            print(f"     Updated {province_updated:,} province references")
            
            print("   Updating district_id...")  
            cur.execute("""
                UPDATE prq.address_cleansing_queue 
                SET district_id = dm.v2_id,
                    district_name = dm.v2_name
                FROM temp.admin_v1_v2_mapping dm
                WHERE dm.level = 'district' 
                AND dm.v1_id = address_cleansing_queue.district_id
            """)
            district_updated = cur.rowcount
            print(f"     Updated {district_updated:,} district references")
            
            print("   Updating ward_id...")
            cur.execute("""
                UPDATE prq.address_cleansing_queue 
                SET ward_id = wm.v2_id,
                    ward_name = wm.v2_name
                FROM temp.admin_v1_v2_mapping wm
                WHERE wm.level = 'ward' 
                AND wm.v1_id = address_cleansing_queue.ward_id
            """)
            ward_updated = cur.rowcount
            print(f"     Updated {ward_updated:,} ward references")
        
        return True

def validate_migration_result(db):
    """Validate kết quả migration"""
    
    print("Validating migration results...")
    
    with db.cursor() as cur:
        # Check admin_version distribution after migration
        cur.execute("""
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
        """)
        
        results = cur.fetchall()
        print("   Admin version distribution after migration:")
        for r in results:
            level = r['level']
            version = r['admin_version']
            count = r['count']
            print(f"     {level:<10} admin_version={version}: {count:,}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Migrate address_cleansing_queue to admin_version=2')
    parser.add_argument('--validate-only', action='store_true', help='Only validate current state')
    parser.add_argument('--create-mapping-only', action='store_true', help='Only create mapping table')
    parser.add_argument('--migrate', action='store_true', help='Run full migration')
    parser.add_argument('--backup', action='store_true', help='Create backup before migration')
    parser.add_argument('--dry-run', action='store_true', help='Dry run without actual updates')
    
    args = parser.parse_args()
    
    try:
        # Load database config
        cfg = load_config_with_env('app/ai/config.yaml')
        db = DBConnector(cfg['database'])
        db.connect()
        
        print(f"Starting admin_version migration - {datetime.now()}")
        
        if args.validate_only:
            print("VALIDATE-ONLY mode")
            validate_migration_result(db)
            
        elif args.create_mapping_only:
            print("CREATE-MAPPING-ONLY mode")
            create_admin_mapping_table(db)
            validate_mapping_coverage(db)
            
        elif args.migrate:
            print("FULL MIGRATION mode")
            
            # Create backup if requested
            if args.backup:
                backup_table = create_backup_table(db)
                print(f"   Backup created: prq.{backup_table}")
            
            # Create mapping
            create_admin_mapping_table(db)
            validate_mapping_coverage(db)
            
            # Run migration
            migrate_address_cleansing_queue(db, dry_run=args.dry_run)
            
            # Validate results
            if not args.dry_run:
                validate_migration_result(db)
            
        else:
            parser.print_help()
        
        db.disconnect()
        print(f"\nMigration completed successfully - {datetime.now()}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()