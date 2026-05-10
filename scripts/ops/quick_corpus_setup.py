#!/usr/bin/env python3
import sys
from pathlib import Path
_ops_dir = Path(__file__).resolve().parent
if str(_ops_dir) not in sys.path:
    sys.path.insert(0, str(_ops_dir))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

"""
Quick corpus setup script with proper environment variable handling.
"""

import os
import logging
from typing import Dict, Any
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_config() -> Dict[str, Any]:
    """Get database config with resolved environment variables."""
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASS'),
        'schema': 'prq'
    }

def test_connection() -> bool:
    """Test database connection."""
    config = get_db_config()
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['dbname'],
            user=config['user'],
            password=config['password']
        )
        conn.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_corpus_status():
    """Check current status of address_clean_corpus table."""
    config = get_db_config()
    
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['dbname'],
        user=config['user'],
        password=config['password']
    )
    
    try:
        with conn.cursor() as cur:
            # Check if table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'prq' 
                    AND table_name = 'address_clean_corpus'
                )
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logger.error("❌ Table prq.address_clean_corpus does not exist")
                return False
                
            logger.info("✅ Table prq.address_clean_corpus exists")
            
            # Check current data
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT source_type) as source_types,
                    COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as has_mgte_emb,
                    COUNT(CASE WHEN phobert_embedding IS NOT NULL THEN 1 END) as has_phobert_emb,
                    MAX(created_at) as last_created
                FROM prq.address_clean_corpus
                WHERE is_active = true
            """)
            
            stats = cur.fetchone()
            logger.info(f"📊 Current corpus statistics:")
            logger.info(f"   Total records: {stats[0]}")
            logger.info(f"   Source types: {stats[1]}")
            logger.info(f"   mGTE embeddings: {stats[2]}")
            logger.info(f"   PhoBERT embeddings: {stats[3]}")
            logger.info(f"   Last created: {stats[4]}")
            
            # Check by source type
            cur.execute("""
                SELECT 
                    source_type,
                    admin_epoch,
                    COUNT(*) as count,
                    AVG(quality_score)::numeric(5,3) as avg_quality
                FROM prq.address_clean_corpus 
                WHERE is_active = true
                GROUP BY source_type, admin_epoch
                ORDER BY source_type, admin_epoch
            """)
            
            breakdown = cur.fetchall()
            if breakdown:
                logger.info(f"📋 Breakdown by source:")
                for source, epoch, count, avg_qual in breakdown:
                    logger.info(f"   {source} ({epoch}): {count} records, quality={avg_qual}")
            
            return stats[0] > 0
            
    finally:
        conn.close()

def populate_administrative_corpus():
    """Populate corpus from administrative master data."""
    config = get_db_config()
    
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['dbname'],
        user=config['user'],
        password=config['password']
    )
    
    try:
        with conn.cursor() as cur:
            logger.info("🏛️ Starting administrative corpus population...")
            
            # Insert from administrative data
            query = """
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
                            TRIM(REPLACE(w.ward_name, COALESCE(w.type_name || ' ', ''), '')) || ', ' ||
                            TRIM(REPLACE(p.province_name, COALESCE(p.type_name || ' ', ''), ''))
                        ELSE
                            TRIM(REPLACE(w.ward_name, COALESCE(w.type_name || ' ', ''), '')) || ', ' ||
                            TRIM(REPLACE(d.district_name, COALESCE(d.type_name || ' ', ''), '')) || ', ' ||
                            TRIM(REPLACE(p.province_name, COALESCE(p.type_name || ' ', ''), ''))
                    END as standardized_address,
                    CASE 
                        WHEN w.admin_version = 2 THEN
                            jsonb_build_object(
                                'level_3', TRIM(REPLACE(w.ward_name, COALESCE(w.type_name || ' ', ''), '')),
                                'level_1', TRIM(REPLACE(p.province_name, COALESCE(p.type_name || ' ', ''), '')),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy'
                            )
                        ELSE
                            jsonb_build_object(
                                'level_3', TRIM(REPLACE(w.ward_name, COALESCE(w.type_name || ' ', ''), '')),
                                'level_2', TRIM(REPLACE(d.district_name, COALESCE(d.type_name || ' ', ''), '')),
                                'level_1', TRIM(REPLACE(p.province_name, COALESCE(p.type_name || ' ', ''), '')),
                                'admin_version', w.admin_version,
                                'address_type', 'administrative_hierarchy'
                            )
                    END as address_components,
                    'ADMINISTRATIVE' as source_type,
                    w.ward_id as source_id,
                    p.province_id,
                    TRIM(REPLACE(p.province_name, COALESCE(p.type_name || ' ', ''), '')) as province_name,
                    d.district_id,
                    TRIM(REPLACE(d.district_name, COALESCE(d.type_name || ' ', ''), '')) as district_name, 
                    w.ward_id,
                    TRIM(REPLACE(w.ward_name, COALESCE(w.type_name || ' ', ''), '')) as ward_name,
                    '2025' as admin_epoch,
                    w.admin_version,
                    1.0000 as quality_score,
                    CURRENT_DATE as effective_date,
                    'QUICK_SETUP_SCRIPT' as created_by
                FROM mat.ward w
                JOIN mat.district d ON w.district_id = d.district_id 
                    AND d.admin_version = w.admin_version
                JOIN mat.province p ON d.province_id = p.province_id 
                    AND p.admin_version = d.admin_version
                WHERE w.is_deleted = false 
                  AND d.is_deleted = false 
                  AND p.is_deleted = false
                  AND NOT EXISTS (
                      SELECT 1 FROM prq.address_clean_corpus c 
                      WHERE c.source_type = 'ADMINISTRATIVE' 
                        AND c.source_id = w.ward_id
                        AND c.admin_epoch = '2025'
                  )
            """
            
            cur.execute(query)
            inserted = cur.rowcount
            conn.commit()
            
            logger.info(f"✅ Inserted {inserted} administrative records")
            return inserted
            
    except Exception as e:
        logger.error(f"❌ Error populating administrative corpus: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def populate_queue_corpus(min_confidence: float = 0.7, limit: int = 1000):
    """Populate corpus from queue standardized results."""
    config = get_db_config()
    
    conn = psycopg2.connect(
        host=config['host'],
        port=config['port'],
        database=config['dbname'],
        user=config['user'],
        password=config['password']
    )
    
    try:
        with conn.cursor() as cur:
            logger.info(f"🤖 Starting queue corpus population (min_conf={min_confidence})...")
            
            query = """
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
                SELECT DISTINCT
                    TRIM(q.address_standardized) as standardized_address,
                    jsonb_build_object(
                        'source_id', q.id,
                        'processing_method', q.processing_method,
                        'ai_model', q.selected_ai_model,
                        'confidence_phobert', q.phobert_confidence_score,
                        'confidence_mgte', q.mgte_confidence_score,
                        'address_type', 'ai_standardized'
                    ) as address_components,
                    'QUEUE_STANDARDIZED' as source_type,
                    q.id as source_id,
                    q.province_id,
                    q.province_name, 
                    q.district_id,
                    q.district_name,
                    q.ward_id,
                    q.ward_name,
                    '2025' as admin_epoch,
                    1 as admin_version,
                    GREATEST(
                        COALESCE(q.phobert_confidence_score, 0), 
                        COALESCE(q.mgte_confidence_score, 0)
                    ) as quality_score,
                    CURRENT_DATE as effective_date,
                    'QUICK_SETUP_SCRIPT' as created_by
                FROM prq.address_cleansing_queue q
                WHERE q.processing_status = 'COMPLETED' 
                  AND q.address_standardized IS NOT NULL
                  AND LENGTH(TRIM(q.address_standardized)) > 10
                  AND GREATEST(
                      COALESCE(q.phobert_confidence_score, 0), 
                      COALESCE(q.mgte_confidence_score, 0)
                  ) >= %s
                  AND NOT EXISTS (
                      SELECT 1 FROM prq.address_clean_corpus c 
                      WHERE c.source_type = 'QUEUE_STANDARDIZED' 
                        AND c.source_id = q.id
                  )
                ORDER BY GREATEST(
                    COALESCE(q.phobert_confidence_score, 0), 
                    COALESCE(q.mgte_confidence_score, 0)
                ) DESC
                LIMIT %s
            """
            
            cur.execute(query, (min_confidence, limit))
            inserted = cur.rowcount
            conn.commit()
            
            logger.info(f"✅ Inserted {inserted} queue records")
            return inserted
            
    except Exception as e:
        logger.error(f"❌ Error populating queue corpus: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main function to set up corpus."""
    logger.info("🚀 Starting quick corpus setup...")
    
    # Test connection
    if not test_connection():
        return
        
    # Check current status
    has_data = check_corpus_status()
    
    # Always try to add more queue data if possible
    admin_count = 0
    
    # Skip administrative population if already exists
    if has_data:
        logger.info("⏭️ Skipping administrative data (already exists)")
    else:
        admin_count = populate_administrative_corpus()
    
    # Populate queue data
    queue_count = populate_queue_corpus(min_confidence=0.7, limit=2000)
    
    # Final check
    logger.info("🎯 Final status check:")
    check_corpus_status()
    
    total = admin_count + queue_count
    logger.info(f"🎉 Setup completed! Total records added: {total}")

if __name__ == "__main__":
    main()