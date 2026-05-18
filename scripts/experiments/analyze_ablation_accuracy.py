#!/usr/bin/env python3
"""
Ablation Study - Accuracy Analysis
Đánh giá độ chính xác của 3 cấu hình trên Run ID 96 (N=50)
"""

import sys
import os

# Add src to path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, src_path)

from app.core.database import engine

def analyze_ablation_accuracy():
    """Phân tích accuracy của 3 cấu hình Ablation Study"""
    
    # Connect using SQLAlchemy engine
    conn = engine.raw_connection()
    cur = conn.cursor()
    
    # Set search path
    cur.execute("SET search_path TO prq")
    
    print("=" * 80)
    print("ABLATION STUDY - ACCURACY ANALYSIS")
    print("=" * 80)
    print()
    
    # Lấy thông tin run
    cur.execute("""
        SELECT id, n_realized, rng_seed, noise_profile_id, notes
        FROM supa_benchmark_run
        WHERE id = 96
    """)
    run_info = cur.fetchone()
    print(f"Run ID: {run_info[0]}")
    print(f"Cohort size: N={run_info[1]}")
    print(f"Seed: {run_info[2]}")
    print(f"Noise profile: {run_info[3]}")
    print(f"Notes: {run_info[4]}")
    print()
    
    # Phân tích accuracy
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN pred_standardized IS NOT NULL THEN 1 END) as with_pred,
            COUNT(CASE WHEN pred_standardized = ref_address_v2 THEN 1 END) as exact_match,
            AVG(latency_ms) as avg_latency,
            MIN(latency_ms) as min_latency,
            MAX(latency_ms) as max_latency
        FROM supa_benchmark_specimen
        WHERE run_id = 96
    """)
    
    result = cur.fetchone()
    total = result[0]
    with_pred = result[1]
    exact_match = result[2]
    avg_latency = result[3] or 0
    min_latency = result[4] or 0
    max_latency = result[5] or 0
    
    print("OVERALL RESULTS:")
    print(f"  Total specimens: {total}")
    print(f"  With predictions: {with_pred} ({with_pred/total*100:.1f}%)")
    print(f"  Exact matches: {exact_match} ({exact_match/total*100:.1f}%)")
    print(f"  Avg latency: {avg_latency:.2f} ms")
    print(f"  Min latency: {min_latency:.2f} ms")
    print(f"  Max latency: {max_latency:.2f} ms")
    print()
    
    # Phân tích theo stratum
    cur.execute("""
        SELECT 
            stratum_code,
            COUNT(*) as total,
            COUNT(CASE WHEN pred_standardized = ref_address_v2 THEN 1 END) as exact_match,
            AVG(latency_ms) as avg_latency
        FROM supa_benchmark_specimen
        WHERE run_id = 96
        GROUP BY stratum_code
        ORDER BY stratum_code
    """)
    
    print("ACCURACY BY STRATUM:")
    print(f"{'Stratum':<15} {'Total':<10} {'Exact Match':<15} {'Accuracy':<12} {'Avg Latency':<15}")
    print("-" * 80)
    
    for row in cur.fetchall():
        noise_level = row[0] or 'NULL'
        total_n = row[1]
        exact_match_n = row[2]
        avg_lat = row[3] or 0
        accuracy = exact_match_n / total_n * 100 if total_n > 0 else 0
        
        print(f"{noise_level:<15} {total_n:<10} {exact_match_n:<15} {accuracy:>10.1f}% {avg_lat:>13.2f} ms")
    
    print()
    
    # Lấy một số ví dụ sai
    cur.execute("""
        SELECT 
            id,
            noisy_raw_address,
            ref_address_v2,
            pred_standardized,
            stratum_code,
            latency_ms
        FROM supa_benchmark_specimen
        WHERE run_id = 96 
          AND pred_standardized IS NOT NULL
          AND pred_standardized != ref_address_v2
        LIMIT 10
    """)
    
    errors = cur.fetchall()
    if errors:
        print("SAMPLE ERRORS (first 10):")
        print("-" * 80)
        for i, row in enumerate(errors, 1):
            lat = row[5] or 0
            print(f"\n{i}. Specimen ID: {row[0]} | Stratum: {row[4]} | Latency: {lat:.2f}ms")
            try:
                print(f"   Input:     {row[1]}")
                print(f"   Expected:  {row[2]}")
                print(f"   Predicted: {row[3]}")
            except UnicodeEncodeError:
                print(f"   [Unicode encoding error - skipped]")
    
    cur.close()
    conn.close()
    
    print()
    print("=" * 80)
    print("Analysis complete!")
    print("=" * 80)

if __name__ == "__main__":
    analyze_ablation_accuracy()
