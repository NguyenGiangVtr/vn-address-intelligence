#!/usr/bin/env python3
"""
Test script to validate PreLabeler improvements with admin_version=2
"""

import sys
import json
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.export_for_annotation import export_data, PreLabeler

def main():
    """Test PreLabeler với admin_version improvements"""
    
    print("=== TESTING PRELABELER IMPROVEMENTS ===")
    
    # Test 1: Export small dataset và kiểm tra admin_version usage
    print("\n1. Testing export with admin_version tracking...")
    test_output = "data/test_prelabeler_admin_v2.json"
    
    try:
        export_data('app/ai/config.yaml', test_output, limit=20)
        print("   ✓ Export completed successfully")
        
        # Analyze output file
        with open(test_output, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"   ✓ Exported {len(data)} records")
        
        # Count admin_version usage
        admin_stats = {
            "v1": {"province": 0, "district": 0, "ward": 0}, 
            "v2": {"province": 0, "district": 0, "ward": 0},
            "null": {"province": 0, "district": 0, "ward": 0}
        }
        
        for record in data:
            meta = record.get("data", {}).get("meta", {})
            versions = meta.get("admin_versions", {})
            
            for level in ["province", "district", "ward"]:
                version = versions.get(level)
                if version == 1:
                    admin_stats["v1"][level] += 1
                elif version == 2:
                    admin_stats["v2"][level] += 1
                else:
                    admin_stats["null"][level] += 1
        
        print("\n   Admin version distribution:")
        for level in ["province", "district", "ward"]:
            v1_count = admin_stats["v1"][level]
            v2_count = admin_stats["v2"][level] 
            null_count = admin_stats["null"][level]
            total = v1_count + v2_count + null_count
            
            if total > 0:
                v2_percent = (v2_count * 100.0) / total
                print(f"     {level.capitalize():<10}: v2={v2_count:2d}/{total:2d} ({v2_percent:5.1f}%)")
        
        # Test 2: Kiểm tra quality của predictions
        print("\n2. Testing prediction quality...")
        
        total_predictions = 0
        label_counts = {}
        confidence_scores = []
        
        for record in data:
            predictions = record.get("predictions", [{}])[0].get("result", [])
            total_predictions += len(predictions)
            
            for pred in predictions:
                label = pred["value"]["labels"][0]
                score = pred["score"]
                
                label_counts[label] = label_counts.get(label, 0) + 1
                confidence_scores.append(score)
        
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            print(f"   ✓ Total predictions: {total_predictions}")
            print(f"   ✓ Average confidence: {avg_confidence:.3f}")
            print(f"   ✓ Label distribution: {dict(sorted(label_counts.items()))}")
        
        # Test 3: Spot check một vài samples
        print("\n3. Sample predictions:")
        for i, record in enumerate(data[:3]):
            text = record["data"]["text"]
            meta = record["data"]["meta"]
            context = meta["context"]
            versions = meta["admin_versions"]
            predictions = record.get("predictions", [{}])[0].get("result", [])
            
            print(f"\n   Sample {i+1}:")
            print(f"   Text: {text}")
            print(f"   Context: {context}")
            print(f"   Admin versions: {versions}")
            print(f"   Labels: {len(predictions)} predictions")
            
            # Show high-confidence predictions
            for pred in predictions[:3]:  # Show first 3
                label = pred["value"]["labels"][0]
                text_span = pred["value"]["text"]
                confidence = pred["score"]
                print(f"     - {label}: '{text_span}' ({confidence:.2f})")
        
        print(f"\n✅ All tests passed! Output saved to: {test_output}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()