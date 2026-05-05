#!/usr/bin/env python3
"""
populate_clean_corpus.py

Script để populate bảng prq.address_clean_corpus từ các nguồn dữ liệu:
1. Administrative Master Data (mat.ward, mat.district, mat.province)
2. Queue Standardized Results (prq.address_cleansing_queue)

Usage:
    python app/ai/populate_clean_corpus.py --config app/ai/config.yaml
    python app/ai/populate_clean_corpus.py --source administrative --epoch 2025
    python app/ai/populate_clean_corpus.py --source queue --min-confidence 0.7
"""

import argparse
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import yaml

from app.ai.db_connector import DBConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorpusPopulator:
    """Populate prq.address_clean_corpus từ các nguồn dữ liệu khác nhau."""
    
    def __init__(self, db_config: Dict):
        self.db = DBConnector(db_config)
        
    def populate_from_administrative(self, admin_epoch: str = "2025") -> int:
        """
        Populate corpus từ administrative master data.
        
        Args:
            admin_epoch: Kỳ cải cách hành chính
            
        Returns:
            int: Số lượng records được insert
        """
        logger.info("🏛️ Bắt đầu populate từ Administrative Master Data (epoch=%s)", admin_epoch)
        
        query = """
            INSERT INTO prq.address_clean_corpus (
                standardized_address, 
                source_type, 
                source_id,
                province_id, 
                province_name,
                district_id, 
                district_name, 
                ward_id, 
                ward_name,
                admin_epoch,
                admin_version,
                quality_score,
                effective_date,
                created_by
            )
            SELECT 
                CASE 
                    WHEN w.admin_version = 2 THEN
                        REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                        REPLACE(p.province_name, p.type_name || ' ', '')
                    ELSE
                        REPLACE(w.ward_name, w.type_name || ' ', '') || ', ' ||
                        REPLACE(d.district_name, d.type_name || ' ', '') || ', ' ||
                        REPLACE(p.province_name, p.type_name || ' ', '')
                END as standardized_address,
                'ADMINISTRATIVE' as source_type,
                w.ward_id as source_id,
                p.province_id,
                REPLACE(p.province_name, p.type_name || ' ', '') as province_name,
                d.district_id,
                REPLACE(d.district_name, d.type_name || ' ', '') as district_name, 
                w.ward_id,
                REPLACE(w.ward_name, w.type_name || ' ', '') as ward_name,
                %s as admin_epoch,
                1 as admin_version,
                1.0000 as quality_score,
                CURRENT_DATE as effective_date,
                'POPULATE_SCRIPT' as created_by
            FROM mat.ward w
            JOIN mat.district d ON w.district_id = d.district_id 
                AND d.admin_version = w.admin_version
            JOIN mat.province p ON d.province_id = p.province_id 
                AND p.admin_version = d.admin_version
            WHERE w.is_deleted = false 
              AND d.is_deleted = false 
              AND p.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM prq.address_clean_corpus c 
                  WHERE c.source_type = 'ADMINISTRATIVE' 
                    AND c.source_id = w.ward_id
                    AND c.admin_epoch = %s
              )
        """
        
        with self.db.cursor() as cur:
            cur.execute(query, (admin_epoch, admin_epoch))
            inserted = cur.rowcount
            
        logger.info("✅ Đã insert %d records từ Administrative Data", inserted)
        return inserted

    def populate_from_queue(
        self, 
        min_confidence: float = 0.6,
        admin_epoch: str = "2025",
        batch_size: int = 1000
    ) -> int:
        """
        Populate corpus từ prq.address_cleansing_queue (standardized results).
        
        Args:
            min_confidence: Confidence score tối thiểu 
            admin_epoch: Kỳ cải cách hành chính
            batch_size: Kích thước batch để xử lý
            
        Returns:
            int: Số lượng records được insert
        """
        logger.info(
            "🤖 Bắt đầu populate từ Queue Standardized (min_conf=%.2f, epoch=%s)", 
            min_confidence, admin_epoch
        )
        
        # Query để lấy standardized addresses với confidence cao
        select_query = """
            SELECT DISTINCT
                q.id,
                q.address_standardized,
                q.province_id, 
                q.province_name,
                q.district_id, 
                q.district_name, 
                q.ward_id, 
                q.ward_name,
                GREATEST(
                    COALESCE(q.phobert_confidence_score, 0), 
                    COALESCE(q.mgte_confidence_score, 0)
                ) as max_confidence,
                q.selected_ai_model,
                q.updated_at
            FROM prq.address_cleansing_queue q
            WHERE q.processing_status = 'COMPLETED' 
              AND q.address_standardized IS NOT NULL
              AND LENGTH(q.address_standardized) > 10
              AND GREATEST(
                  COALESCE(q.phobert_confidence_score, 0), 
                  COALESCE(q.mgte_confidence_score, 0)
              ) >= %s
              AND NOT EXISTS (
                  SELECT 1 FROM prq.address_clean_corpus c 
                  WHERE c.source_type = 'QUEUE_STANDARDIZED' 
                    AND c.source_id = q.id
              )
            ORDER BY max_confidence DESC
            LIMIT %s
        """
        
        insert_query = """
            INSERT INTO prq.address_clean_corpus (
                standardized_address,
                source_type, 
                source_id,
                province_id,
                province_name, 
                district_id,
                district_name,
                ward_id,
                ward_name,
                admin_epoch,
                admin_version,
                quality_score,
                effective_date,
                created_by
            ) VALUES %s
        """
        
        total_inserted = 0
        
        with self.db.cursor() as cur:
            # Lấy dữ liệu theo batch 
            cur.execute(select_query, (min_confidence, batch_size * 10))  # Lấy nhiều hơn để filter
            rows = cur.fetchall()
            
            if not rows:
                logger.info("Không có dữ liệu mới để populate từ queue")
                return 0
                
            # Chuẩn bị data cho bulk insert
            insert_data = []
            seen_addresses = set()  # Dedup trong batch
            
            for row in rows:
                if isinstance(row, dict):
                    addr = row['address_standardized']
                    queue_id = row['id']
                    max_conf = float(row['max_confidence'])
                else:
                    addr = row[1]
                    queue_id = row[0] 
                    max_conf = float(row[8])
                
                # Skip duplicates trong batch
                if addr in seen_addresses:
                    continue
                    
                seen_addresses.add(addr)
                
                insert_data.append((
                    addr,                           # standardized_address
                    'QUEUE_STANDARDIZED',          # source_type
                    queue_id,                      # source_id
                    row[2] if isinstance(row, dict) else row[2],  # province_id
                    row[3] if isinstance(row, dict) else row[3],  # province_name
                    row[4] if isinstance(row, dict) else row[4],  # district_id  
                    row[5] if isinstance(row, dict) else row[5],  # district_name
                    row[6] if isinstance(row, dict) else row[6],  # ward_id
                    row[7] if isinstance(row, dict) else row[7],  # ward_name
                    admin_epoch,                   # admin_epoch
                    1,                            # admin_version
                    max_conf,                     # quality_score
                    date.today(),                 # effective_date
                    'POPULATE_SCRIPT'             # created_by
                ))
                
                if len(insert_data) >= batch_size:
                    break
            
            # Bulk insert
            if insert_data:
                from psycopg2.extras import execute_values
                execute_values(
                    cur, 
                    insert_query, 
                    insert_data,
                    template=None,
                    page_size=100
                )
                total_inserted = len(insert_data)
                
        logger.info("✅ Đã insert %d records từ Queue Standardized", total_inserted)
        return total_inserted

    def update_corpus_embeddings(
        self, 
        embedding_model: str = "mgte",
        batch_size: int = 500,
        admin_epoch: str = "2025"
    ) -> int:
        """
        Cập nhật pre-computed embeddings cho corpus entries.
        
        Args:
            embedding_model: Model để compute embeddings ("mgte" or "phobert")
            batch_size: Kích thước batch
            admin_epoch: Epoch cần cập nhật
            
        Returns:
            int: Số lượng records được cập nhật
        """
        logger.info(
            "🧠 Bắt đầu compute embeddings (%s) cho corpus (epoch=%s)", 
            embedding_model, admin_epoch
        )
        
        # Import model tương ứng
        if embedding_model.lower() == "mgte":
            from app.ai.models.siamese_mgte import SiameseMGTE
            model = SiameseMGTE()
            embedding_col = "mgte_embedding"
        elif embedding_model.lower() == "phobert":
            from app.ai.models.phobert_model import PhoBERTModel  
            model = PhoBERTModel()
            embedding_col = "phobert_embedding"
        else:
            raise ValueError(f"Unsupported embedding model: {embedding_model}")
        
        # Lấy addresses chưa có embedding
        select_query = f"""
            SELECT id, standardized_address
            FROM prq.address_clean_corpus
            WHERE admin_epoch = %s 
              AND is_active = true
              AND {embedding_col} IS NULL
            ORDER BY quality_score DESC
            LIMIT %s
        """
        
        total_updated = 0
        
        with self.db.cursor() as cur:
            cur.execute(select_query, (admin_epoch, batch_size))
            rows = cur.fetchall()
            
            if not rows:
                logger.info("Tất cả corpus entries đã có embeddings")
                return 0
                
            # Extract addresses và IDs
            ids = []
            addresses = []
            for row in rows:
                if isinstance(row, dict):
                    ids.append(row['id'])
                    addresses.append(row['standardized_address'])
                else:
                    ids.append(row[0])
                    addresses.append(row[1])
                    
            logger.info("Computing embeddings cho %d addresses...", len(addresses))
            
            # Compute embeddings batch
            embeddings = model.model.encode(addresses, convert_to_numpy=True)
            
            # Update từng record (có thể optimize bằng unnest() sau)
            update_query = f"""
                UPDATE prq.address_clean_corpus 
                SET {embedding_col} = %s,
                    embedding_version = 'v1',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            
            for i, (record_id, embedding) in enumerate(zip(ids, embeddings)):
                # Convert numpy array sang list để serialize JSON
                embedding_list = embedding.tolist()
                cur.execute(update_query, (embedding_list, record_id))
                
                if (i + 1) % 100 == 0:
                    logger.debug("Đã cập nhật %d/%d embeddings", i + 1, len(ids))
                    
            total_updated = len(ids)
            
        logger.info("✅ Đã cập nhật %s embeddings cho %d records", embedding_model, total_updated)
        return total_updated

    def get_corpus_stats(self) -> Dict:
        """Lấy thống kê về corpus hiện tại."""
        query = """
            SELECT 
                source_type,
                admin_epoch,
                COUNT(*) as count,
                AVG(quality_score) as avg_quality,
                COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as has_mgte_emb,
                COUNT(CASE WHEN phobert_embedding IS NOT NULL THEN 1 END) as has_phobert_emb
            FROM prq.address_clean_corpus 
            WHERE is_active = true
            GROUP BY source_type, admin_epoch
            ORDER BY source_type, admin_epoch
        """
        
        with self.db.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            
        stats = {"total": 0, "by_source": {}}
        
        for row in rows:
            if isinstance(row, dict):
                source = row['source_type']
                epoch = row['admin_epoch']
                count = row['count']
                avg_qual = float(row['avg_quality']) if row['avg_quality'] else 0.0
                mgte_emb = row['has_mgte_emb']
                phobert_emb = row['has_phobert_emb']
            else:
                source, epoch, count, avg_qual, mgte_emb, phobert_emb = row
                avg_qual = float(avg_qual) if avg_qual else 0.0
                
            key = f"{source}_{epoch}"
            stats["by_source"][key] = {
                "count": count,
                "avg_quality": avg_qual,
                "mgte_embeddings": mgte_emb,
                "phobert_embeddings": phobert_emb
            }
            stats["total"] += count
            
        return stats


def main():
    parser = argparse.ArgumentParser(description="Populate prq.address_clean_corpus")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    parser.add_argument("--source", choices=["administrative", "queue", "both"], 
                       default="both", help="Data source to populate from")
    parser.add_argument("--epoch", default="2025", help="Administrative epoch")
    parser.add_argument("--min-confidence", type=float, default=0.6, 
                       help="Minimum confidence for queue data")
    parser.add_argument("--compute-embeddings", action="store_true",
                       help="Compute embeddings after population")
    parser.add_argument("--embedding-model", choices=["mgte", "phobert"], 
                       default="mgte", help="Embedding model to use")
    parser.add_argument("--batch-size", type=int, default=1000, 
                       help="Batch size for processing")
    parser.add_argument("--stats-only", action="store_true",
                       help="Only show corpus statistics")
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    db_config = config.get('database', {})
    
    populator = CorpusPopulator(db_config)
    
    try:
        # Show stats first
        logger.info("📊 Current Corpus Statistics:")
        stats = populator.get_corpus_stats()
        logger.info(f"Total records: {stats['total']}")
        for source, data in stats['by_source'].items():
            logger.info(f"  {source}: {data['count']} records, avg_quality={data['avg_quality']:.3f}")
            
        if args.stats_only:
            return
            
        total_inserted = 0
        
        # Populate từ administrative data
        if args.source in ["administrative", "both"]:
            inserted = populator.populate_from_administrative(args.epoch)
            total_inserted += inserted
            
        # Populate từ queue data  
        if args.source in ["queue", "both"]:
            inserted = populator.populate_from_queue(
                args.min_confidence, args.epoch, args.batch_size
            )
            total_inserted += inserted
            
        # Compute embeddings nếu được yêu cầu
        if args.compute_embeddings and total_inserted > 0:
            populator.update_corpus_embeddings(
                args.embedding_model, args.batch_size, args.epoch
            )
            
        # Final stats
        logger.info("📊 Final Statistics:")
        final_stats = populator.get_corpus_stats()
        logger.info(f"Total records: {final_stats['total']} (+{total_inserted})")
        
        logger.info("🎉 Population completed successfully!")
        
    except Exception as e:
        logger.error("❌ Error during population: %s", e, exc_info=True)
        raise
    finally:
        populator.db.close()


if __name__ == "__main__":
    main()