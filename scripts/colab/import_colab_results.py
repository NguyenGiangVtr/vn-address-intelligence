"""
Import kết quả từ Colab (CSV) về PostgreSQL.

Usage:
    python scripts/colab/import_colab_results.py --csv ablation_n1000_results.csv
"""

import argparse
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.core.database import engine
from sqlalchemy import text


def import_colab_results(csv_path: str):
    """Import CSV từ Colab về PostgreSQL."""
    
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} rows")
    print(f"  Configs: {df['config'].unique().tolist()}")
    
    with engine.connect() as conn:
        # Tạo run_id cho mỗi config
        configs = df['config'].unique()
        run_ids = {}
        
        for idx, config in enumerate(configs):
            config_df = df[df['config'] == config]
            
            # Insert run
            result = conn.execute(text("""
                INSERT INTO prq.supa_benchmark_run
                (n, seed, profile, git_commit, notes, created_at)
                VALUES (:n, :seed, :profile, :git_commit, :notes, :created_at)
                RETURNING id
            """), {
                "n": len(config_df),
                "seed": 3001 + idx,
                "profile": "SUP-1.0.0",
                "git_commit": "colab-gpu-run",
                "notes": f"Colab GPU - {config} - N={len(config_df)}",
                "created_at": datetime.utcnow()
            })
            
            run_id = result.fetchone()[0]
            run_ids[config] = run_id
            print(f"✓ Created run_id {run_id} for {config}")
        
        conn.commit()
        
        # Import specimens
        print(f"\nImporting specimens...")
        for _, row in df.iterrows():
            run_id = run_ids[row['config']]
            
            conn.execute(text("""
                INSERT INTO prq.supa_benchmark_specimen
                (run_id, gt_id, raw_address, ref_address_v2, pred_standardized, latency_ms)
                VALUES (:run_id, :gt_id, :raw_address, :ref_address_v2, :pred_standardized, :latency_ms)
            """), {
                "run_id": run_id,
                "gt_id": int(row['gt_id']),
                "raw_address": row['raw_address'],
                "ref_address_v2": row['ref_address_v2'],
                "pred_standardized": row['pred_standardized'],
                "latency_ms": float(row['latency_ms'])
            })
        
        conn.commit()
        print(f"✓ Imported {len(df)} specimens")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"IMPORT SUMMARY")
    print(f"{'='*60}")
    for config, run_id in run_ids.items():
        count = len(df[df['config'] == config])
        avg_latency = df[df['config'] == config]['latency_ms'].mean()
        print(f"{config:20s} | run_id={run_id:3d} | N={count:4d} | latency={avg_latency:6.1f}ms")
    
    print(f"\n{'='*60}")
    print(f"NEXT STEPS:")
    print(f"{'='*60}")
    for run_id in run_ids.values():
        print(f"python scripts/experiments/supa_benchmark.py eval --run-id {run_id}")
    
    print(f"\npython scripts/experiments/supa_benchmark.py aggregate-runs \\")
    print(f"    --run-ids {','.join(map(str, run_ids.values()))} \\")
    print(f"    --out-json reports/ablation_n1000_colab_aggregate.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Colab results to PostgreSQL")
    parser.add_argument("--csv", type=str, required=True, help="CSV file from Colab")
    
    args = parser.parse_args()
    
    import_colab_results(args.csv)
