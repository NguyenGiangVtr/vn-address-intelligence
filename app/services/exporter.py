import json
import logging
from app.core.database import SessionLocal, TrainingDataset
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Exporter")

def export_training_data(output_path="data/training_data.jsonl"):
    """
    Export data from ath.training_datasets to JSONL format for Hugging Face.
    """
    session = SessionLocal()
    try:
        datasets = session.query(TrainingDataset).all()
        if not datasets:
            logger.warning("⚠️ No data to export.")
            return

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_file, "w", encoding="utf-8") as f:
            for item in datasets:
                # Format: {"tokens": [...], "ner_tags": [...]}
                json.dump(item.ner_tags_json, f, ensure_ascii=False)
                f.write("\n")
        
        logger.info(f"OK: Exported {len(datasets)} samples to {output_path}")
        
    except Exception as e:
        logger.error(f"Error export: {e}")
    finally:
        session.close()
