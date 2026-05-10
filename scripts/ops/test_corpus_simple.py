#!/usr/bin/env python3
import sys
from pathlib import Path
_ops_dir = Path(__file__).resolve().parent
if str(_ops_dir) not in sys.path:
    sys.path.insert(0, str(_ops_dir))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

"""
Simple test script for address_clean_corpus integration
"""

import os
import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add app to path  
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.ai.db_connector import DBConnector

def test_db_methods():
    """Test database connector methods."""
    print("🧪 Testing DatabaseConnector methods...")
    
    # Load config  
    with open('app/ai/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Update config with env vars
    db_config = config['database'].copy()
    db_config['host'] = os.getenv('DB_HOST')
    db_config['port'] = int(os.getenv('DB_PORT'))
    db_config['dbname'] = os.getenv('DB_NAME')
    db_config['user'] = os.getenv('DB_USER')
    db_config['password'] = os.getenv('DB_PASS')
    
    db = DBConnector(db_config)
    
    try:
        db.connect()
        print("✅ Database connection successful")
        
        # Test 1: load_clean_corpus
        print("\n📋 Testing load_clean_corpus...")
        corpus = db.load_clean_corpus(
            admin_epoch="2025",
            source_types=["ADMINISTRATIVE"],
            min_quality_score=0.5,
            limit=10
        )
        print(f"   Loaded {len(corpus)} addresses from clean corpus")
        if corpus:
            print(f"   Sample: {corpus[0][:100]}...")
        
        # Test 2: load_clean_corpus_with_metadata
        print("\n📋 Testing load_clean_corpus_with_metadata...")
        addresses, metadata = db.load_clean_corpus_with_metadata(
            admin_epoch="2025",
            min_quality_score=0.7,
            limit=5
        )
        print(f"   Loaded {len(addresses)} addresses with metadata")
        if metadata:
            print(f"   Sample metadata: {metadata[0]}")
        
        # Test 3: Fallback to hierarchical corpus
        print("\n📋 Testing hierarchical corpus fallback...")
        hierarchical = db.load_hierarchical_corpus()
        print(f"   Loaded {len(hierarchical[:10])} hierarchical addresses (showing first 10)")
        if hierarchical:
            print(f"   Sample: {hierarchical[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_db_methods()
    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n💥 Tests failed!")
        exit(1)