import argparse
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH để có thể import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import create_all_tables, sync_typesense_to_db

def main():
    parser = argparse.ArgumentParser(description="Sync Ground Truth data from Typesense to PostgreSQL.")
    parser.add_argument("--province", type=int, help="Province ID to filter (e.g., 92 for HCM)")
    parser.add_argument("--limit", type=int, help="Limit number of records to sync")
    parser.add_argument("--create-tables", action="store_true", help="Create tables before syncing")

    args = parser.parse_args()

    if args.create_tables:
        print("Initializing database schemas and tables...")
        create_all_tables()

    sync_typesense_to_db(province_id=args.province, limit=args.limit)

if __name__ == "__main__":
    main()
