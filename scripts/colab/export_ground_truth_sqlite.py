"""
Export ground_truth từ PostgreSQL sang SQLite cho Google Colab.

Usage:
    python scripts/colab/export_ground_truth_sqlite.py --limit 15000 --output ground_truth.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.core.database import engine
from sqlalchemy import text


def export_ground_truth_sqlite(limit: int, output_path: str):
    """Export ground_truth từ PostgreSQL sang SQLite."""
    
    # Xóa file cũ nếu tồn tại
    from pathlib import Path
    output_file = Path(output_path)
    if output_file.exists():
        output_file.unlink()
        print(f"Removed existing file: {output_path}")
    
    print(f"Connecting to PostgreSQL...")
    with engine.connect() as pg_conn:
        # Query ground_truth
        query = text(f"""
            SELECT 
                id, old_address, address, 
                province_id, district_id, ward_id,
                latitude, longitude, popular, created_at
            FROM prq.ground_truth
            ORDER BY id
            LIMIT :limit
        """)
        
        result = pg_conn.execute(query, {"limit": limit})
        rows = result.fetchall()
        columns = result.keys()
        
        print(f"[OK] Fetched {len(rows)} rows from PostgreSQL")
    
    # Write to SQLite
    print(f"Writing to {output_path}...")
    sqlite_conn = sqlite3.connect(output_path)
    sqlite_cur = sqlite_conn.cursor()
    
    # Create table
    col_defs = ", ".join([f"{col} TEXT" for col in columns])
    sqlite_cur.execute(f"CREATE TABLE ground_truth ({col_defs})")
    
    # Insert data
    placeholders = ", ".join(["?" for _ in columns])
    sqlite_cur.executemany(
        f"INSERT INTO ground_truth VALUES ({placeholders})",
        [tuple(row) for row in rows]
    )
    
    sqlite_conn.commit()
    sqlite_conn.close()
    
    print(f"[OK] Exported {len(rows)} rows to {output_path}")
    
    # Verify
    verify_conn = sqlite3.connect(output_path)
    verify_cur = verify_conn.cursor()
    verify_cur.execute("SELECT COUNT(*) FROM ground_truth")
    count = verify_cur.fetchone()[0]
    verify_conn.close()
    
    print(f"[OK] Verified: {count} rows in SQLite")
    
    # File size
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"[OK] File size: {size_mb:.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export ground_truth to SQLite")
    parser.add_argument("--limit", type=int, default=15000, help="Number of rows to export")
    parser.add_argument("--output", type=str, default="colab_vnai/ground_truth.db", help="Output SQLite file")
    
    args = parser.parse_args()
    
    export_ground_truth_sqlite(args.limit, args.output)
