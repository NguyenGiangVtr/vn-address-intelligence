import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.ai.db_connector import DBConnector
from app.ai.utils.config_loader import load_config_with_env

cfg = load_config_with_env("src/app/ai/config.yaml")
db = DBConnector(cfg["database"])
db.connect()

# Check A1 results
result = db.execute_query("SELECT COUNT(*) FROM prq.supa_benchmark_specimen WHERE run_id=94 AND pred_standardized IS NOT NULL")
count = result[0][0] if result else 0
print(f"A1 processed: {count}/1000")

# Check average latency
result = db.execute_query("SELECT AVG(latency_ms) FROM prq.supa_benchmark_specimen WHERE run_id=94 AND latency_ms IS NOT NULL")
avg_lat = result[0][0] if result and result[0][0] else None
if avg_lat:
    print(f"Average latency: {avg_lat:.2f} ms")

db.disconnect()
