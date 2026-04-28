from app.core.database import create_all_tables
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    print("🚀 Initializing Administrative, OSM, AI Hub, and Queue schemas/tables...")
    try:
        create_all_tables()
        print("✅ Database initialization complete. Schemas created and metadata seeded.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
