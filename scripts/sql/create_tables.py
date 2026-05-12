import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.core.database import create_all_tables

if __name__ == "__main__":
    print("🚀 Initializing Administrative, OSM, AI Hub, and Queue schemas/tables...")
    try:
        create_all_tables()
        print("✅ Database initialization complete. Schemas created and metadata seeded.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)
