#!/usr/bin/env python3
"""
Migration script: Di chuyển dữ liệu từ mat.google_ground_truth sang prq.ground_truth

Chức năng:
1. Tạo bảng prq.ground_truth mới nếu chưa có
2. Migrate dữ liệu từ bảng cũ sang bảng mới với metadata mới
3. Validate dữ liệu sau khi migrate
4. Option: Drop bảng cũ sau khi migrate thành công

Usage:
    python scripts/migration/migrate_ground_truth_to_prq.py --validate-only
    python scripts/migration/migrate_ground_truth_to_prq.py --migrate
    python scripts/migration/migrate_ground_truth_to_prq.py --migrate --drop-old-table
"""

import sys
import os
import argparse
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import insert

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal, GoogleGroundTruth, GroundTruth, create_all_tables


def validate_data(session):
    """Kiểm tra tính toàn vẹn dữ liệu"""
    print("🔍 Validating data integrity...")
    
    # Đếm records trong bảng cũ và mới
    old_count = session.query(GoogleGroundTruth).count()
    new_count = session.query(GroundTruth).count()
    
    print(f"  📊 Records count:")
    print(f"    - mat.google_ground_truth: {old_count:,}")
    print(f"    - prq.ground_truth: {new_count:,}")
    
    if old_count == 0:
        print("  ⚠️  No data found in mat.google_ground_truth")
        return False
        
    # Kiểm tra sample data
    sample_old = session.query(GoogleGroundTruth).limit(5).all()
    if sample_old:
        print(f"  📋 Sample from old table:")
        for record in sample_old[:2]:
            print(f"    - ID {record.id}: {record.address[:50]}...")
    
    # Kiểm tra unique IDs
    duplicate_check = session.execute(text("""
        SELECT COUNT(*) as total, COUNT(DISTINCT id) as unique_ids 
        FROM mat.google_ground_truth
    """)).fetchone()
    
    if duplicate_check.total != duplicate_check.unique_ids:
        print(f"  ⚠️  Found duplicate IDs: {duplicate_check.total - duplicate_check.unique_ids}")
        return False
    
    print("  ✅ Data validation passed")
    return True


def migrate_data(session, batch_size=1000):
    """Migrate dữ liệu từ bảng cũ sang bảng mới"""
    print("🚀 Starting data migration...")
    
    total_records = session.query(GoogleGroundTruth).count()
    print(f"  📊 Total records to migrate: {total_records:,}")
    
    if total_records == 0:
        print("  ⚠️  No data to migrate")
        return False
    
    # Clear target table first
    print("  🧹 Clearing target table prq.ground_truth...")
    session.execute(text("TRUNCATE TABLE prq.ground_truth CASCADE"))
    session.commit()
    
    # Migrate in batches
    migrated_count = 0
    errors = []
    
    for offset in range(0, total_records, batch_size):
        print(f"  📦 Processing batch {offset // batch_size + 1}/{(total_records + batch_size - 1) // batch_size}...")
        
        # Fetch batch from old table
        old_records = session.query(GoogleGroundTruth).offset(offset).limit(batch_size).all()
        
        if not old_records:
            break
            
        # Convert to new format
        new_records = []
        for old_record in old_records:
            try:
                new_record = {
                    'id': old_record.id,
                    'address': old_record.address,
                    'old_address': old_record.old_address,
                    'ward_id': old_record.ward_id,
                    'district_id': old_record.district_id,
                    'province_id': old_record.province_id,
                    'old_ward_id': old_record.old_ward_id,
                    'old_district_id': old_record.old_district_id,
                    'old_province_id': old_record.old_province_id,
                    'old_address_eng': old_record.old_address_eng,
                    'address_eng': old_record.address_eng,
                    'latitude': old_record.latitude,
                    'longitude': old_record.longitude,
                    'popular': old_record.popular or 0,
                    
                    # New metadata fields
                    'source_system': 'TYPESENSE',
                    'data_quality_score': None,  # To be calculated later
                    'is_validated': False,
                    'validation_notes': None,
                    
                    'created_at': old_record.created_at or datetime.now(),
                    'updated_at': datetime.now()
                }
                new_records.append(new_record)
            except Exception as e:
                errors.append(f"Record ID {old_record.id}: {str(e)}")
                continue
        
        # Insert batch to new table
        if new_records:
            try:
                stmt = insert(GroundTruth).values(new_records)
                session.execute(stmt)
                session.commit()
                migrated_count += len(new_records)
                print(f"    ✅ Migrated {len(new_records)} records (Total: {migrated_count:,})")
            except Exception as e:
                session.rollback()
                error_msg = f"Batch insert failed at offset {offset}: {str(e)}"
                print(f"    ❌ {error_msg}")
                errors.append(error_msg)
                continue
    
    # Report results
    print(f"\n📈 Migration Results:")
    print(f"  - Total processed: {total_records:,}")
    print(f"  - Successfully migrated: {migrated_count:,}")
    print(f"  - Errors: {len(errors)}")
    
    if errors:
        print(f"\n❌ Errors encountered:")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  - ... and {len(errors) - 10} more errors")
    
    # Final validation
    new_count = session.query(GroundTruth).count()
    print(f"\n🔍 Post-migration validation:")
    print(f"  - Records in prq.ground_truth: {new_count:,}")
    
    success_rate = (migrated_count / total_records * 100) if total_records > 0 else 0
    print(f"  - Success rate: {success_rate:.1f}%")
    
    return success_rate >= 95.0  # Consider successful if >= 95%


def drop_old_table(session):
    """Drop bảng cũ sau khi migrate thành công"""
    print("🗑️  Dropping old table mat.google_ground_truth...")
    try:
        session.execute(text("DROP TABLE IF EXISTS mat.google_ground_truth CASCADE"))
        session.commit()
        print("  ✅ Old table dropped successfully")
        return True
    except Exception as e:
        session.rollback()
        print(f"  ❌ Failed to drop old table: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate Google Ground Truth data from mat to prq schema")
    parser.add_argument('--validate-only', action='store_true', help='Only validate data, do not migrate')
    parser.add_argument('--migrate', action='store_true', help='Perform data migration')
    parser.add_argument('--drop-old-table', action='store_true', help='Drop old table after successful migration')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for migration (default: 1000)')
    
    args = parser.parse_args()
    
    if not args.validate_only and not args.migrate:
        print("❌ Please specify either --validate-only or --migrate")
        return 1
    
    print("🏗️  Google Ground Truth Migration Tool")
    print("=" * 50)
    
    # Ensure tables exist
    print("📋 Creating database schemas and tables...")
    create_all_tables()
    
    session = SessionLocal()
    try:
        # Always validate first
        if not validate_data(session):
            print("❌ Data validation failed. Aborting.")
            return 1
        
        if args.validate_only:
            print("✅ Validation completed. No migration performed.")
            return 0
        
        # Perform migration
        if args.migrate:
            success = migrate_data(session, batch_size=args.batch_size)
            if not success:
                print("❌ Migration failed or incomplete.")
                return 1
            
            print("✅ Migration completed successfully!")
            
            # Drop old table if requested
            if args.drop_old_table:
                if drop_old_table(session):
                    print("✅ Cleanup completed - old table removed.")
                else:
                    print("⚠️  Migration successful but failed to drop old table.")
            
            return 0
    
    except Exception as e:
        print(f"💥 Unexpected error: {str(e)}")
        session.rollback()
        return 1
    
    finally:
        session.close()


if __name__ == "__main__":
    exit(main())