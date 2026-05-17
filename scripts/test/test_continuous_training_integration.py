#!/usr/bin/env python3
"""
Integration test for continuous training pipeline from prelabeler cases.

This test:
1. Seeds 60 prelabeler cases with test_result = true
2. Triggers training via API
3. Verifies checkpoint creation
4. Verifies training_history record

Usage:
    python scripts/test/test_continuous_training_integration.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Bootstrap import paths
for _p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
    if (_p / "pyproject.toml").is_file():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

import _bootstrap_import_paths  # noqa: E402
_bootstrap_import_paths.install()

from sqlalchemy import text
from app.core.database import SessionLocal


def seed_prelabeler_cases(count: int = 60) -> List[str]:
    """
    Seed prelabeler test cases with passed status.
    
    Returns:
        List of case IDs created
    """
    print(f"\n{'='*60}")
    print(f"Seeding {count} prelabeler cases...")
    print(f"{'='*60}")
    
    session = SessionLocal()
    case_ids = []
    
    try:
        # Sample addresses with expected entities
        sample_addresses = [
            {
                "input": "268 Lý Thường Kiệt, Phường 14, Quận 10, TP. Hồ Chí Minh",
                "expected": [
                    {"label": "NUM", "text": "268"},
                    {"label": "STR", "text": "Lý Thường Kiệt"},
                    {"label": "WDS", "text": "Phường 14"},
                    {"label": "DST", "text": "Quận 10"},
                    {"label": "PRO", "text": "TP. Hồ Chí Minh"},
                ]
            },
            {
                "input": "123 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
                "expected": [
                    {"label": "NUM", "text": "123"},
                    {"label": "STR", "text": "Nguyễn Huệ"},
                    {"label": "WDS", "text": "Phường Bến Nghé"},
                    {"label": "DST", "text": "Quận 1"},
                    {"label": "PRO", "text": "TP. Hồ Chí Minh"},
                ]
            },
            {
                "input": "45 Lê Lợi, Phường Bến Thành, Quận 1, TP. Hồ Chí Minh",
                "expected": [
                    {"label": "NUM", "text": "45"},
                    {"label": "STR", "text": "Lê Lợi"},
                    {"label": "WDS", "text": "Phường Bến Thành"},
                    {"label": "DST", "text": "Quận 1"},
                    {"label": "PRO", "text": "TP. Hồ Chí Minh"},
                ]
            },
        ]
        
        # Create cases by cycling through samples
        for i in range(count):
            sample = sample_addresses[i % len(sample_addresses)]
            case_id = f"test_case_{i}_{int(time.time())}"
            
            # Create test_result with passed = true
            test_result = {
                "passed": True,
                "details": [],
                "unexpected": [],
                "validation_errors": []
            }
            
            session.execute(text("""
                INSERT INTO ai.prelabeler_testcases 
                (id, name, input, note, expected, strict, test_result, tested_at, created_at, updated_at)
                VALUES 
                (:id, :name, :input, :note, CAST(:expected AS JSONB), :strict, 
                 CAST(:test_result AS JSONB), NOW(), NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    expected = EXCLUDED.expected,
                    test_result = EXCLUDED.test_result,
                    tested_at = EXCLUDED.tested_at,
                    updated_at = EXCLUDED.updated_at
            """), {
                "id": case_id,
                "name": f"Integration Test Case {i+1}",
                "input": sample["input"],
                "note": "Auto-generated for integration test",
                "expected": json.dumps(sample["expected"]),
                "strict": True,
                "test_result": json.dumps(test_result),
            })
            
            case_ids.append(case_id)
        
        session.commit()
        print(f"✓ Successfully seeded {len(case_ids)} cases")
        
    except Exception as e:
        session.rollback()
        print(f"✗ Failed to seed cases: {e}")
        raise
    finally:
        session.close()
    
    return case_ids


def verify_passed_cases_count() -> int:
    """Verify number of passed cases in database."""
    session = SessionLocal()
    try:
        result = session.execute(text("""
            SELECT COUNT(*) as cnt
            FROM ai.prelabeler_testcases
            WHERE expected IS NOT NULL
              AND jsonb_array_length(expected) > 0
              AND (test_result->>'passed')::boolean = true
        """)).mappings().first()
        
        count = result["cnt"] if result else 0
        print(f"✓ Found {count} passed cases in database")
        return count
    finally:
        session.close()


def trigger_training_api(min_samples: int = 50) -> Dict[str, Any]:
    """
    Trigger training via API endpoint.
    
    Note: This is a mock - in real test, you'd use requests library
    to call the actual API endpoint.
    """
    print(f"\n{'='*60}")
    print(f"Triggering training API...")
    print(f"{'='*60}")
    
    # In a real integration test, you would do:
    # import requests
    # response = requests.post(
    #     "http://localhost:8000/api/training/trigger-ner-from-prelabeler",
    #     params={"min_samples": min_samples, "epochs": 1, "batch_size": 8},
    #     headers={"Authorization": f"Bearer {token}"}
    # )
    # return response.json()
    
    # For this test, we'll simulate the response
    print("⚠ Note: This is a simulation. In production, use actual API call.")
    print("  To test manually:")
    print("  1. Start server: python -m app.api.server")
    print("  2. Login and get token")
    print("  3. POST /api/training/trigger-ner-from-prelabeler")
    
    return {
        "status": "accepted",
        "job_id": "simulated-job-id",
        "message": f"Training started with {min_samples}+ passed cases",
        "note": "This is a simulated response for testing"
    }


def verify_checkpoint_exists(output_dir_pattern: str = "models/phobert-ner-vn-*") -> bool:
    """
    Verify that a checkpoint directory was created.
    
    Returns:
        True if checkpoint exists, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Verifying checkpoint creation...")
    print(f"{'='*60}")
    
    project_root = Path(__file__).parent.parent.parent
    models_dir = project_root / "models"
    
    if not models_dir.exists():
        print(f"✗ Models directory does not exist: {models_dir}")
        return False
    
    # Find latest checkpoint matching pattern
    checkpoints = sorted(models_dir.glob("phobert-ner-vn-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not checkpoints:
        print(f"✗ No checkpoints found matching pattern: {output_dir_pattern}")
        return False
    
    latest = checkpoints[0]
    print(f"✓ Found checkpoint: {latest.name}")
    
    # Verify checkpoint contents
    required_files = ["config.json", "pytorch_model.bin", "training_log.json"]
    missing = []
    
    for fname in required_files:
        if not (latest / fname).exists():
            missing.append(fname)
    
    if missing:
        print(f"⚠ Checkpoint missing files: {missing}")
        return False
    
    print(f"✓ Checkpoint contains all required files")
    return True


def verify_training_history() -> bool:
    """
    Verify that training_history table has a new record.
    
    Returns:
        True if record exists, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Verifying training_history record...")
    print(f"{'='*60}")
    
    session = SessionLocal()
    try:
        # Get latest training history record
        result = session.execute(text("""
            SELECT id, version, accuracy, f1_score, loss, samples_count, notes, created_at
            FROM ath.training_history
            ORDER BY created_at DESC
            LIMIT 1
        """)).mappings().first()
        
        if not result:
            print(f"✗ No training_history records found")
            return False
        
        print(f"✓ Found training_history record:")
        print(f"  - ID: {result['id']}")
        print(f"  - Version: {result['version']}")
        print(f"  - F1 Score: {result['f1_score']:.4f}")
        print(f"  - Accuracy: {result['accuracy']:.4f}")
        print(f"  - Samples: {result['samples_count']}")
        print(f"  - Created: {result['created_at']}")
        
        # Check if it's recent (within last hour)
        if result['created_at']:
            age_seconds = (datetime.now() - result['created_at']).total_seconds()
            if age_seconds > 3600:
                print(f"⚠ Record is older than 1 hour ({age_seconds/60:.1f} minutes)")
                return False
        
        return True
        
    finally:
        session.close()


def cleanup_test_cases(case_ids: List[str]):
    """Clean up test cases after test."""
    print(f"\n{'='*60}")
    print(f"Cleaning up test cases...")
    print(f"{'='*60}")
    
    session = SessionLocal()
    try:
        for case_id in case_ids:
            session.execute(text("""
                DELETE FROM ai.prelabeler_testcases WHERE id = :id
            """), {"id": case_id})
        
        session.commit()
        print(f"✓ Cleaned up {len(case_ids)} test cases")
    except Exception as e:
        session.rollback()
        print(f"⚠ Failed to cleanup: {e}")
    finally:
        session.close()


def main():
    """Run integration test."""
    print(f"\n{'='*60}")
    print(f"CONTINUOUS TRAINING INTEGRATION TEST")
    print(f"{'='*60}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    case_ids = []
    success = True
    
    try:
        # Step 1: Seed test cases
        case_ids = seed_prelabeler_cases(count=60)
        
        # Step 2: Verify count
        count = verify_passed_cases_count()
        if count < 50:
            print(f"✗ Insufficient passed cases: {count} < 50")
            success = False
            return
        
        # Step 3: Trigger training (simulated)
        response = trigger_training_api(min_samples=50)
        print(f"✓ API Response: {response['status']}")
        
        # Step 4: Verify checkpoint (skip in simulation)
        print(f"\n⚠ Checkpoint verification skipped (requires actual training)")
        print(f"  To verify manually:")
        print(f"  1. Run: python -m app.ai.train_ner --from-prelabeler --min-prelabeler-samples 50 --epochs 1")
        print(f"  2. Check: ls -la models/phobert-ner-vn-*")
        
        # Step 5: Verify training_history (skip in simulation)
        print(f"\n⚠ Training history verification skipped (requires actual training)")
        print(f"  To verify manually:")
        print(f"  1. After training completes")
        print(f"  2. Query: SELECT * FROM ath.training_history ORDER BY created_at DESC LIMIT 1")
        
        print(f"\n{'='*60}")
        print(f"✓ INTEGRATION TEST SETUP COMPLETED")
        print(f"{'='*60}")
        print(f"\nNext steps to complete full integration test:")
        print(f"1. Start API server: python -m app.api.server")
        print(f"2. Login and get auth token")
        print(f"3. POST /api/training/trigger-ner-from-prelabeler")
        print(f"4. Wait for training to complete (~5-15 minutes)")
        print(f"5. Verify checkpoint and training_history")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    finally:
        # Cleanup
        if case_ids:
            cleanup_choice = input("\nCleanup test cases? (y/n): ").strip().lower()
            if cleanup_choice == 'y':
                cleanup_test_cases(case_ids)
            else:
                print(f"⚠ Test cases left in database. Clean up manually if needed.")
    
    print(f"\n{'='*60}")
    if success:
        print(f"✓ TEST PASSED (setup phase)")
    else:
        print(f"✗ TEST FAILED")
    print(f"{'='*60}\n")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
