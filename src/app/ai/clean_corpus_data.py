#!/usr/bin/env python3
"""
clean_corpus_data.py

Script để làm sạch data trong address_clean_corpus:
1. TRIM standardized_address  
2. Fix NULL address_components
3. Ensure proper structure by admin_version

Usage:
    python app/ai/clean_corpus_data.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def clean_corpus_data():
    """Clean corpus data: trim addresses and fix components."""
    
    print("🧹 Starting corpus data cleaning...")
    
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS')
    )
    
    try:
        with conn.cursor() as cur:
            # 0. Check current data quality
            print("0. Checking current data quality...")
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN standardized_address != TRIM(standardized_address) THEN 1 END) as needs_trim,
                    COUNT(CASE WHEN address_components IS NULL THEN 1 END) as null_components,
                    AVG(LENGTH(standardized_address))::int as avg_len
                FROM prq.address_clean_corpus
            """)
            
            before = cur.fetchone()
            print(f"   Total records: {before[0]}")
            print(f"   Needs trimming: {before[1]}")
            print(f"   NULL components: {before[2]}")
            print(f"   Average length: {before[3]} chars")
            
            # 1. Trim standardized_address
            if before[1] > 0:
                print("1. Trimming standardized_address...")
                cur.execute("""
                    UPDATE prq.address_clean_corpus 
                    SET standardized_address = TRIM(standardized_address),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE standardized_address != TRIM(standardized_address)
                """)
                
                trimmed = cur.rowcount
                print(f"   ✅ Trimmed {trimmed} records")
            else:
                print("1. ✅ All addresses already trimmed")
            
            # 2. Fix NULL address_components
            if before[2] > 0:
                print("2. Fixing NULL address_components...")
                cur.execute("""
                    UPDATE prq.address_clean_corpus 
                    SET address_components = CASE 
                            WHEN admin_version = 2 THEN
                                jsonb_build_object(
                                    'level_3', ward_name,
                                    'level_1', province_name,
                                    'admin_version', admin_version,
                                    'address_type', 'administrative_hierarchy'
                                )
                            ELSE
                                jsonb_build_object(
                                    'level_3', ward_name,
                                    'level_2', district_name,
                                    'level_1', province_name,
                                    'admin_version', admin_version,
                                    'address_type', 'administrative_hierarchy'
                                )
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE address_components IS NULL
                """)
                
                fixed_components = cur.rowcount
                print(f"   ✅ Fixed {fixed_components} NULL address_components")
            else:
                print("2. ✅ All address_components already populated")
            
            # 3. Ensure admin_version = 2 doesn't have level_2
            print("3. Checking admin_version = 2 structure...")
            cur.execute("""
                SELECT COUNT(*) 
                FROM prq.address_clean_corpus 
                WHERE admin_version = 2 AND address_components ? 'level_2'
            """)
            
            v2_with_level2 = cur.fetchone()[0]
            if v2_with_level2 > 0:
                print(f"   Fixing {v2_with_level2} version 2 records with level_2...")
                cur.execute("""
                    UPDATE prq.address_clean_corpus 
                    SET address_components = jsonb_build_object(
                            'level_3', ward_name,
                            'level_1', province_name,
                            'admin_version', admin_version,
                            'address_type', 'administrative_hierarchy'
                        ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE admin_version = 2 AND address_components ? 'level_2'
                """)
                
                fixed_v2 = cur.rowcount
                print(f"   ✅ Fixed {fixed_v2} version 2 records")
            else:
                print("   ✅ Admin version 2 structure is correct")
            
            # 4. Clean any duplicate whitespace in addresses
            print("4. Cleaning duplicate whitespace...")
            cur.execute("""
                UPDATE prq.address_clean_corpus 
                SET standardized_address = REGEXP_REPLACE(standardized_address, '\\s+', ' ', 'g'),
                    updated_at = CURRENT_TIMESTAMP
                WHERE standardized_address ~ '\\s{2,}'
            """)
            
            whitespace_cleaned = cur.rowcount
            if whitespace_cleaned > 0:
                print(f"   ✅ Cleaned whitespace in {whitespace_cleaned} records")
            else:
                print("   ✅ No duplicate whitespace found")
            
            conn.commit()
            
            # 5. Final verification
            print("5. Final verification...")
            cur.execute("""
                SELECT 
                    admin_version,
                    COUNT(*) as total,
                    COUNT(CASE WHEN address_components IS NULL THEN 1 END) as null_components,
                    COUNT(CASE WHEN address_components ? 'level_1' THEN 1 END) as has_level1,
                    COUNT(CASE WHEN address_components ? 'level_2' THEN 1 END) as has_level2,
                    COUNT(CASE WHEN address_components ? 'level_3' THEN 1 END) as has_level3,
                    AVG(LENGTH(standardized_address))::int as avg_len,
                    COUNT(CASE WHEN standardized_address != TRIM(standardized_address) THEN 1 END) as untrimmed
                FROM prq.address_clean_corpus
                GROUP BY admin_version
                ORDER BY admin_version
            """)
            
            results = cur.fetchall()
            print("   📊 Final data quality by admin_version:")
            print("   Ver | Total | Null | L1   | L2   | L3   | AvgLen | Untrimmed")
            print("   ----|-------|------|------|------|------|--------|----------")
            
            total_records = 0
            total_issues = 0
            
            for version, total, null_comp, l1, l2, l3, avg_len, untrimmed in results:
                total_records += total
                issues = null_comp + untrimmed
                total_issues += issues
                
                print(f"   {version:3} | {total:5} | {null_comp:4} | {l1:4} | {l2:4} | {l3:4} | {avg_len:6} | {untrimmed:9}")
            
            print(f"\n   📋 Summary:")
            print(f"   Total records: {total_records}")
            print(f"   Total issues: {total_issues}")
            
            if total_issues == 0:
                print("   ✅ All data is clean!")
            else:
                print(f"   ⚠️  {total_issues} issues remaining")
            
            return total_issues == 0
            
    except Exception as e:
        print(f"❌ Error during cleaning: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_corpus_integration():
    """Test corpus loading to ensure integration still works."""
    
    print("🔍 Verifying corpus integration...")
    
    try:
        import sys
        from pathlib import Path
        import yaml
        
        # Add to path
        sys.path.append(str(Path.cwd()))
        from app.ai.db_connector import DBConnector
        
        # Load config
        from app.paths import ai_config_yaml

        with open(ai_config_yaml(), "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        db_config = config['database'].copy()
        db_config['host'] = os.getenv('DB_HOST')
        db_config['port'] = int(os.getenv('DB_PORT'))
        db_config['dbname'] = os.getenv('DB_NAME')
        db_config['user'] = os.getenv('DB_USER')
        db_config['password'] = os.getenv('DB_PASS')
        
        db = DBConnector(db_config)
        db.connect()
        
        # Test clean corpus loading
        corpus = db.load_clean_corpus(admin_epoch='2025', limit=5)
        print(f"   ✅ Clean corpus: {len(corpus)} addresses loaded")
        
        # Test hierarchical corpus
        hierarchical = db.load_hierarchical_corpus()
        print(f"   ✅ Hierarchical corpus: {len(hierarchical)} addresses loaded")
        
        # Test metadata loading
        addresses, metadata = db.load_clean_corpus_with_metadata(admin_epoch='2025', limit=3)
        print(f"   ✅ Metadata loading: {len(addresses)} addresses with metadata")
        
        # Verify address quality
        all_trimmed = all(addr == addr.strip() for addr in corpus)
        print(f"   ✅ All addresses properly trimmed: {all_trimmed}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        print("🚀 Starting corpus data cleaning process...\n")
        
        # Clean data
        success = clean_corpus_data()
        
        if success:
            print("\n🧪 Running integration tests...")
            integration_ok = verify_corpus_integration()
            
            if integration_ok:
                print("\n🎉 Corpus data cleaning completed successfully!")
                print("✅ All data is clean and integration tests passed!")
            else:
                print("\n⚠️  Data cleaning succeeded but integration tests failed")
                exit(1)
        else:
            print("\n❌ Data cleaning completed with some issues")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Cleaning process failed: {e}")
        exit(1)