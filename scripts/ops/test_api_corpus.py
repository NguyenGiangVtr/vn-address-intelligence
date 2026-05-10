#!/usr/bin/env python3
import sys
from pathlib import Path
_ops_dir = Path(__file__).resolve().parent
if str(_ops_dir) not in sys.path:
    sys.path.insert(0, str(_ops_dir))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

"""Test API corpus loading"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path.cwd()))

def test_api_corpus():
    """Test API corpus loading functionality."""
    print("Testing API corpus loading...")
    
    try:
        from sqlalchemy import text, create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Create SQLAlchemy session like in API
        from urllib.parse import quote_plus
        password = quote_plus(os.getenv('DB_PASS'))
        DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db_session:
            # Test query like in _load_parser_corpus
            clean_corpus_query = text("""
                SELECT standardized_address 
                FROM prq.address_clean_corpus
                WHERE is_active = true 
                  AND admin_epoch = '2025'
                  AND quality_score >= 0.7
                  AND LENGTH(standardized_address) > 5
                ORDER BY quality_score DESC, usage_count DESC
                LIMIT 10
            """)
            
            result = db_session.execute(clean_corpus_query).fetchall()
            print(f"API query returned {len(result)} addresses")
            
            if result:
                print("Sample addresses:")
                for i, row in enumerate(result):
                    addr = row[0]
                    print(f"  {i+1}: {addr[:60]}...")
                return True
            else:
                print("No addresses found")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_api_corpus()
    if success:
        print("\nAPI integration test passed!")
    else:
        print("\nAPI integration test failed!")
        exit(1)