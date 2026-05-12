#!/usr/bin/env python3
"""
Test script cho Ground Truth Service
====================================

Script test các tính năng của GroundTruthService sau khi migrate
từ mat.google_ground_truth sang prq.ground_truth

Usage:
    python scripts/test/test_ground_truth_service.py --test-all
    python scripts/test/test_ground_truth_service.py --test-corpus
    python scripts/test/test_ground_truth_service.py --test-stats
"""

import argparse
import os
import sys
from pathlib import Path
from pprint import pprint

for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break
import _bootstrap_import_paths  # noqa: E402

_bootstrap_import_paths.install()

from app.services.ground_truth_service import (
    get_ground_truth_service, 
    get_corpus_for_training, 
    get_training_data
)
from app.core.database import create_all_tables


def test_basic_functionality():
    """Test basic functionality của GroundTruthService"""
    print("🔍 Testing basic Ground Truth Service functionality...")
    
    try:
        with get_ground_truth_service() as service:
            # Test get statistics
            stats = service.get_statistics()
            print(f"📊 Ground Truth Statistics:")
            pprint(stats)
            
            if stats['total_records'] == 0:
                print("⚠️  No data found in prq.ground_truth. Please run migration first:")
                print("   python scripts/migration/migrate_ground_truth_to_prq.py --migrate")
                return False
            
            # Test get validated addresses (limited)
            addresses = service.get_validated_addresses(limit=5)
            print(f"\n📋 Sample addresses (first 5):")
            for i, addr in enumerate(addresses[:5], 1):
                print(f"  {i}. ID={addr['id']}: {addr['address'][:60]}...")
                print(f"     Source: {addr['source_system']}, Quality: {addr['data_quality_score']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing basic functionality: {str(e)}")
        return False


def test_corpus_loading():
    """Test corpus loading functionality"""
    print("\n🏗️  Testing corpus loading...")
    
    try:
        # Test shortcut function
        corpus = get_corpus_for_training(limit=100)
        print(f"📚 Corpus loaded: {len(corpus)} addresses")
        
        if corpus:
            print("📋 Sample corpus addresses:")
            for i, addr in enumerate(corpus[:3], 1):
                print(f"  {i}. {addr[:80]}...")
        else:
            print("⚠️  Empty corpus returned")
            
        # Test service method
        with get_ground_truth_service() as service:
            corpus2 = service.get_corpus_addresses(
                limit=50,
                min_quality_score=0.5,
                source_systems=['TYPESENSE', 'GOOGLE', 'MANUAL']
            )
            print(f"📚 Service corpus: {len(corpus2)} addresses")
            
        return len(corpus) > 0 or len(corpus2) > 0
        
    except Exception as e:
        print(f"❌ Error testing corpus loading: {str(e)}")
        return False


def test_training_data():
    """Test training data functionality"""
    print("\n🎯 Testing training data functionality...")
    
    try:
        # Test training pairs
        with get_ground_truth_service() as service:
            pairs = service.get_training_pairs(limit=10)
            print(f"🔗 Training pairs generated: {len(pairs)}")
            
            if pairs:
                print("📋 Sample training pairs:")
                for i, (raw, norm) in enumerate(pairs[:3], 1):
                    print(f"  {i}. Raw: {raw[:50]}...")
                    print(f"     Norm: {norm[:50]}...")
        
        # Test training DataFrame
        training_df = get_training_data(limit=10)
        print(f"📊 Training DataFrame: {len(training_df)} rows x {len(training_df.columns)} cols")
        
        if not training_df.empty:
            print(f"📋 DataFrame columns: {list(training_df.columns)}")
        
        return len(pairs) > 0 or not training_df.empty
        
    except Exception as e:
        print(f"❌ Error testing training data: {str(e)}")
        return False


def test_filtering():
    """Test filtering functionality"""
    print("\n🔍 Testing filtering functionality...")
    
    try:
        with get_ground_truth_service() as service:
            # Test province filter
            ho_chi_minh_data = service.get_validated_addresses(
                province_id=79,  # TP.HCM thường có ID 79
                limit=5
            )
            print(f"🏙️  HCM addresses found: {len(ho_chi_minh_data)}")
            
            # Test source system filter
            typesense_data = service.get_validated_addresses(
                source_system='TYPESENSE',
                limit=5
            )
            print(f"🔍 TYPESENSE data: {len(typesense_data)}")
            
            # Test validation filter
            validated_data = service.get_validated_addresses(
                include_unvalidated=False,
                limit=5
            )
            print(f"✅ Validated only: {len(validated_data)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing filtering: {str(e)}")
        return False


def test_performance():
    """Test performance với large dataset"""
    print("\n⚡ Testing performance with large dataset...")
    
    try:
        import time
        
        with get_ground_truth_service() as service:
            # Test large corpus loading
            start_time = time.time()
            large_corpus = service.get_corpus_addresses(limit=10000)
            load_time = time.time() - start_time
            
            print(f"📚 Large corpus load: {len(large_corpus):,} addresses in {load_time:.2f}s")
            print(f"⚡ Performance: {len(large_corpus) / load_time:.0f} addresses/second")
            
            # Test với cache (second call)
            start_time = time.time()
            large_corpus2 = service.get_corpus_addresses(limit=5000)
            load_time2 = time.time() - start_time
            
            print(f"📚 Second load: {len(large_corpus2):,} addresses in {load_time2:.2f}s")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing performance: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Ground Truth Service functionality")
    parser.add_argument('--test-all', action='store_true', help='Run all tests')
    parser.add_argument('--test-basic', action='store_true', help='Test basic functionality')
    parser.add_argument('--test-corpus', action='store_true', help='Test corpus loading')
    parser.add_argument('--test-training', action='store_true', help='Test training data')
    parser.add_argument('--test-filtering', action='store_true', help='Test filtering')
    parser.add_argument('--test-performance', action='store_true', help='Test performance')
    
    args = parser.parse_args()
    
    if not any([args.test_all, args.test_basic, args.test_corpus, 
               args.test_training, args.test_filtering, args.test_performance]):
        print("❌ Please specify at least one test to run. Use --help for options.")
        return 1
    
    print("🧪 Ground Truth Service Test Suite")
    print("=" * 50)
    
    # Ensure database is ready
    print("📋 Ensuring database schemas and tables exist...")
    create_all_tables()
    
    tests = []
    results = []
    
    if args.test_all or args.test_basic:
        tests.append(("Basic Functionality", test_basic_functionality))
    
    if args.test_all or args.test_corpus:
        tests.append(("Corpus Loading", test_corpus_loading))
    
    if args.test_all or args.test_training:
        tests.append(("Training Data", test_training_data))
    
    if args.test_all or args.test_filtering:
        tests.append(("Filtering", test_filtering))
    
    if args.test_all or args.test_performance:
        tests.append(("Performance", test_performance))
    
    # Run tests
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 20} {test_name} {'=' * 20}")
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"💥 Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ground Truth Service is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())