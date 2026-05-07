#!/usr/bin/env python3
"""
Setup pgvector extension and create vector similarity indexes.
"""

import os
import logging
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_config():
    """Get database config with resolved environment variables."""
    return {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT')),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASS')
    }

def check_pgvector_extension():
    """Check if pgvector extension is installed."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            # Check if extension exists
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM pg_extension WHERE extname = 'vector'
                )
            """)
            
            extension_exists = cur.fetchone()[0]
            
            if extension_exists:
                logger.info("✅ pgvector extension is installed")
                
                # Check version
                cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                version = cur.fetchone()[0]
                logger.info(f"📦 pgvector version: {version}")
                
                return True
            else:
                logger.warning("⚠️ pgvector extension is not installed")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error checking pgvector extension: {e}")
        return False
    finally:
        conn.close()

def install_pgvector_extension():
    """Try to install pgvector extension."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            logger.info("🔧 Installing pgvector extension...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            logger.info("✅ pgvector extension installed successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error installing pgvector extension: {e}")
        logger.error("Note: You may need superuser privileges or ask your DBA to install pgvector")
        return False
    finally:
        conn.close()

def check_embedding_columns():
    """Check if embedding columns exist and their data types."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'prq' 
                  AND table_name = 'address_clean_corpus'
                  AND column_name LIKE '%embedding%'
                ORDER BY column_name
            """)
            
            columns = cur.fetchall()
            
            if columns:
                logger.info("📋 Embedding columns in address_clean_corpus:")
                for col_name, data_type, nullable in columns:
                    logger.info(f"   {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
                    
                # Check if they're vector types
                cur.execute("""
                    SELECT 
                        column_name,
                        udt_name
                    FROM information_schema.columns
                    WHERE table_schema = 'prq' 
                      AND table_name = 'address_clean_corpus'
                      AND column_name LIKE '%embedding%'
                      AND udt_name = 'vector'
                """)
                
                vector_cols = cur.fetchall()
                
                if vector_cols:
                    logger.info("✅ Found vector-type embedding columns:")
                    for col_name, udt_name in vector_cols:
                        logger.info(f"   {col_name}: {udt_name}")
                    return True
                else:
                    logger.warning("⚠️ Embedding columns exist but are not vector type")
                    return False
            else:
                logger.error("❌ No embedding columns found")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error checking embedding columns: {e}")
        return False
    finally:
        conn.close()

def convert_json_to_vector():
    """Legacy no-op for backward compatibility (embeddings are written as vector)."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            logger.info("🔄 Embeddings are expected in native vector columns; skipping conversion.")
            
            # First check if we have any data
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as mgte_count,
                    COUNT(CASE WHEN phobert_embedding IS NOT NULL THEN 1 END) as phobert_count
                FROM prq.address_clean_corpus
            """)
            
            total, mgte_count, phobert_count = cur.fetchone()
            logger.info(f"📊 Current data: {total} total, {mgte_count} mGTE, {phobert_count} PhoBERT")
            
            if mgte_count == 0 and phobert_count == 0:
                logger.warning("⚠️ No embeddings found to convert. Run compute_embeddings.py first.")
                return False
            
            conn.commit()
            logger.info("✅ Conversion step skipped")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error converting to vector type: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def create_vector_indexes():
    """Create vector similarity indexes for fast retrieval."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            # Check if we have vector data
            cur.execute("""
                SELECT 
                    COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as mgte_count,
                    COUNT(CASE WHEN phobert_embedding IS NOT NULL THEN 1 END) as phobert_count
                FROM prq.address_clean_corpus
                WHERE is_active = true
            """)
            
            mgte_count, phobert_count = cur.fetchone()
            
            if mgte_count == 0 and phobert_count == 0:
                logger.error("❌ No vector embeddings found. Run conversion first.")
                return False
            
            logger.info(f"📊 Creating indexes for {mgte_count} mGTE and {phobert_count} PhoBERT vectors...")
            
            # Create mGTE vector index
            if mgte_count > 0:
                logger.info("🏗️ Creating mGTE vector index (HNSW)...")
                try:
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_corpus_mgte_vector_hnsw 
                        ON prq.address_clean_corpus 
                        USING hnsw (mgte_embedding vector_cosine_ops)
                        WHERE is_active = true AND mgte_embedding IS NOT NULL
                    """)
                    logger.info("✅ mGTE HNSW index created")
                except Exception as e:
                    logger.warning(f"⚠️ HNSW index failed, trying IVFFlat: {e}")
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_corpus_mgte_vector_ivfflat
                        ON prq.address_clean_corpus 
                        USING ivfflat (mgte_embedding vector_cosine_ops)
                        WITH (lists = 100)
                        WHERE is_active = true AND mgte_embedding IS NOT NULL
                    """)
                    logger.info("✅ mGTE IVFFlat index created")
            
            # Create PhoBERT vector index
            if phobert_count > 0:
                logger.info("🏗️ Creating PhoBERT vector index (HNSW)...")
                try:
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_corpus_phobert_vector_hnsw
                        ON prq.address_clean_corpus 
                        USING hnsw (phobert_embedding vector_cosine_ops)
                        WHERE is_active = true AND phobert_embedding IS NOT NULL
                    """)
                    logger.info("✅ PhoBERT HNSW index created")
                except Exception as e:
                    logger.warning(f"⚠️ HNSW index failed, trying IVFFlat: {e}")
                    cur.execute("""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_corpus_phobert_vector_ivfflat
                        ON prq.address_clean_corpus 
                        USING ivfflat (phobert_embedding vector_cosine_ops)
                        WITH (lists = 100)
                        WHERE is_active = true AND phobert_embedding IS NOT NULL
                    """)
                    logger.info("✅ PhoBERT IVFFlat index created")
            
            conn.commit()
            logger.info("✅ Vector indexes created successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating vector indexes: {e}")
        return False
    finally:
        conn.close()

def check_index_status():
    """Check status of vector indexes."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'address_clean_corpus'
                  AND indexname LIKE '%vector%'
                ORDER BY indexname
            """)
            
            indexes = cur.fetchall()
            
            if indexes:
                logger.info("📋 Vector indexes found:")
                for schema, table, index_name, index_def in indexes:
                    logger.info(f"   {index_name}")
                    logger.info(f"     {index_def}")
            else:
                logger.warning("⚠️ No vector indexes found")
                
            return len(indexes) > 0
            
    except Exception as e:
        logger.error(f"❌ Error checking index status: {e}")
        return False
    finally:
        conn.close()

def main():
    """Main function to setup vector indexes."""
    logger.info("🚀 Starting vector index setup...")
    
    # Step 1: Check pgvector extension
    if not check_pgvector_extension():
        if not install_pgvector_extension():
            logger.error("❌ Cannot proceed without pgvector extension")
            return
    
    # Step 2: Check embedding columns
    if not check_embedding_columns():
        logger.info("🔄 Need to convert JSON embeddings to vector type")
        if not convert_json_to_vector():
            logger.error("❌ Vector conversion failed")
            return
    
    # Step 3: Create vector indexes
    if not create_vector_indexes():
        logger.error("❌ Index creation failed")
        return
    
    # Step 4: Verify indexes
    logger.info("🔍 Verifying created indexes...")
    check_index_status()
    benchmark_query_latency()
    
    logger.info("🎉 Vector index setup completed!")

def benchmark_query_latency(samples: int = 20):
    """Quick p95 latency benchmark for vector similarity."""
    config = get_db_config()
    conn = psycopg2.connect(**config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT mgte_embedding
                FROM prq.address_clean_corpus
                WHERE is_active = true AND mgte_embedding IS NOT NULL
                LIMIT %s
                """,
                (samples,),
            )
            rows = cur.fetchall()
            if not rows:
                logger.warning("⚠️ No vectors found for latency benchmark")
                return
            import time
            latencies = []
            for (vec,) in rows:
                t0 = time.time()
                cur.execute(
                    """
                    SELECT id
                    FROM prq.address_clean_corpus
                    WHERE is_active = true AND mgte_embedding IS NOT NULL
                    ORDER BY mgte_embedding <=> %s::vector
                    LIMIT 10
                    """,
                    (vec,),
                )
                cur.fetchall()
                latencies.append((time.time() - t0) * 1000.0)
            latencies.sort()
            p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
            logger.info("📈 Vector query latency p95=%.2fms (target <10ms)", p95)
    finally:
        conn.close()


if __name__ == "__main__":
    main()