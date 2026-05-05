#!/usr/bin/env python3
"""
test_clean_corpus.py

Test script để kiểm tra integration của bảng prq.address_clean_corpus
với các components trong training pipeline.

Usage:
    python app/ai/test_clean_corpus.py --config app/ai/config.yaml
"""

import argparse
import logging
import yaml
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.ai.db_connector import DBConnector
from app.ai.models.siamese_mgte import SiameseMGTE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_db_connector_methods(db_config: dict):
    """Test các phương thức mới trong DatabaseConnector."""
    logger.info("🧪 Testing DatabaseConnector methods...")
    
    db = DBConnector(db_config)
    
    try:
        db.connect()
        
        # Test 1: load_clean_corpus
        logger.info("  📋 Testing load_clean_corpus...")
        corpus = db.load_clean_corpus(
            admin_epoch="2025",
            source_types=["ADMINISTRATIVE", "QUEUE_STANDARDIZED"],
            min_quality_score=0.5,
            limit=100
        )
        logger.info(f"    ✅ Loaded {len(corpus)} addresses from clean corpus")
        if corpus:
            logger.info(f"    📝 Sample: {corpus[0][:100]}...")
        
        # Test 2: load_clean_corpus_with_metadata
        logger.info("  📋 Testing load_clean_corpus_with_metadata...")
        addresses, metadata = db.load_clean_corpus_with_metadata(
            admin_epoch="2025",
            min_quality_score=0.7,
            limit=50
        )
        logger.info(f"    ✅ Loaded {len(addresses)} addresses with metadata")
        if metadata:
            logger.info(f"    📝 Sample metadata: {metadata[0]}")
        
        # Test 3: Fallback to hierarchical corpus  
        logger.info("  📋 Testing hierarchical corpus fallback...")
        hierarchical = db.load_hierarchical_corpus()
        logger.info(f"    ✅ Loaded {len(hierarchical)} hierarchical addresses")
        
        return True
        
    except Exception as e:
        logger.error("❌ DB Connector test failed: %s", e, exc_info=True)
        return False
    finally:
        db.close()


def test_siamese_integration(db_config: dict):
    """Test integration với Siamese models."""
    logger.info("🧪 Testing Siamese model integration...")
    
    db = DBConnector(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'], 
        user=db_config['user'],
        password=db_config['password'],
        schema=db_config.get('schema', 'public')
    )
    
    try:
        db.connect()
        
        # Load mGTE model
        logger.info("  🤖 Initializing mGTE model...")
        model = SiameseMGTE()
        
        # Test với clean corpus
        logger.info("  📋 Loading clean corpus...")
        addresses, metadata = db.load_clean_corpus_with_metadata(
            admin_epoch="2025",
            min_quality_score=0.6,
            limit=200
        )
        
        if addresses:
            logger.info("  🔄 Encoding corpus with metadata...")
            model.encode_corpus_with_metadata(addresses, metadata)
            
            # Test query
            test_query = "123 Đường Nguyễn Huệ, Quận 1, TP.HCM"
            logger.info(f"  🔍 Testing query: {test_query}")
            
            result_addr, score, latency = model.query(test_query)
            logger.info(f"    ✅ Best match: {result_addr} (score={score:.4f}, {latency:.2f}ms)")
            
            # Test temporal-aware query
            if hasattr(model, 'temporal_aware_query'):
                logger.info("  🕒 Testing temporal-aware query...")
                temporal_result = model.temporal_aware_query(
                    test_query, 
                    epoch_filter="2025"
                )
                logger.info(f"    ✅ Temporal match: {temporal_result[0]} (score={temporal_result[1]:.4f})")
            
        else:
            logger.warning("  ⚠️  No clean corpus available, testing with hierarchical...")
            hierarchical = db.load_hierarchical_corpus()
            if hierarchical:
                model.encode_corpus(hierarchical[:100])
                test_query = "Phường Bến Nghé, Quận 1, TP.HCM"
                result_addr, score, latency = model.query(test_query)
                logger.info(f"    ✅ Hierarchical match: {result_addr} (score={score:.4f})")
        
        return True
        
    except Exception as e:
        logger.error("❌ Siamese integration test failed: %s", e, exc_info=True)
        return False
    finally:
        db.close()


def test_corpus_population_workflow(db_config: dict):
    """Test workflow để populate corpus (dry run)."""
    logger.info("🧪 Testing corpus population workflow...")
    
    try:
        from app.ai.populate_clean_corpus import CorpusPopulator
        
        populator = CorpusPopulator(db_config)
        
        # Test stats
        logger.info("  📊 Getting current corpus stats...")
        stats = populator.get_corpus_stats()
        logger.info(f"    Total records: {stats['total']}")
        for source, data in stats['by_source'].items():
            logger.info(f"    {source}: {data['count']} records, avg_quality={data['avg_quality']:.3f}")
        
        # Note: Không chạy actual population để tránh duplicate data
        logger.info("  ℹ️  Skipping actual population (use populate_clean_corpus.py for real population)")
        
        return True
        
    except Exception as e:
        logger.error("❌ Population workflow test failed: %s", e, exc_info=True)
        return False


def test_api_integration(db_config: dict):
    """Test integration với API server (corpus loading)."""
    logger.info("🧪 Testing API integration...")
    
    try:
        # Test using SQLAlchemy session (như trong API)
        from app.core.database import SessionLocal
        from sqlalchemy import text
        
        with SessionLocal() as db_session:
            # Test clean corpus query
            logger.info("  📋 Testing clean corpus query via SQLAlchemy...")
            clean_corpus_query = text("""
                SELECT COUNT(*) as count,
                       AVG(quality_score) as avg_quality
                FROM prq.address_clean_corpus
                WHERE is_active = true 
                  AND admin_epoch = '2025'
            """)
            
            result = db_session.execute(clean_corpus_query).fetchone()
            if result:
                count = result[0] if result[0] else 0
                avg_quality = result[1] if result[1] else 0
                logger.info(f"    ✅ Found {count} active records, avg_quality={avg_quality:.3f}")
            else:
                logger.info("    ℹ️  No records found in clean corpus")
        
        return True
        
    except Exception as e:
        logger.error("❌ API integration test failed: %s", e, exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="Test address_clean_corpus integration")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    parser.add_argument("--skip-models", action="store_true", 
                       help="Skip model tests (faster)")
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    db_config = config.get('database', {})
    
    logger.info("🚀 Starting address_clean_corpus integration tests...")
    
    results = []
    
    # Test 1: DB Connector methods
    results.append(("DB Connector Methods", test_db_connector_methods(db_config)))
    
    # Test 2: API integration
    results.append(("API Integration", test_api_integration(db_config)))
    
    # Test 3: Corpus population workflow
    results.append(("Population Workflow", test_corpus_population_workflow(db_config)))
    
    # Test 4: Siamese integration (optional)
    if not args.skip_models:
        results.append(("Siamese Integration", test_siamese_integration(db_config)))
    else:
        logger.info("⏭️  Skipping model tests (--skip-models)")
    
    # Summary
    logger.info("📋 Test Results Summary:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"  {status} {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())