#!/usr/bin/env python3
"""
Compute embeddings for corpus addresses to optimize retrieval performance.
"""

import os
import json
import logging
import numpy as np
import psycopg2
from dotenv import load_dotenv
from typing import List, Tuple, Optional
import torch
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_config():
    """Get database config with resolved environment variables."""
    return {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT')),
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASS')
    }

class EmbeddingComputer:
    """Compute and store embeddings for corpus addresses."""
    
    def __init__(self):
        self.db_config = get_db_config()
        self.mgte_model = None
        self.phobert_model = None
        self.phobert_tokenizer = None
        
    def load_mgte_model(self):
        """Load mGTE multilingual embedding model."""
        if self.mgte_model is None:
            logger.info("🔄 Loading mGTE model...")
            self.mgte_model = SentenceTransformer(
                'Alibaba-NLP/gte-multilingual-base',
                trust_remote_code=True
            )
            logger.info("✅ mGTE model loaded")
            
    def load_phobert_model(self):
        """Load PhoBERT model for Vietnamese embeddings."""
        if self.phobert_model is None:
            logger.info("🔄 Loading PhoBERT model...")
            model_name = "vinai/phobert-base"
            self.phobert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.phobert_model = AutoModel.from_pretrained(model_name)
            self.phobert_model.eval()
            logger.info("✅ PhoBERT model loaded")
    
    def compute_phobert_embeddings(self, texts: List[str]) -> np.ndarray:
        """Compute PhoBERT embeddings for text list."""
        self.load_phobert_model()
        
        embeddings = []
        batch_size = 16
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize
            inputs = self.phobert_tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors='pt'
            )
            
            # Get embeddings
            with torch.no_grad():
                outputs = self.phobert_model(**inputs)
                # Use [CLS] token embedding (first token)
                cls_embeddings = outputs.last_hidden_state[:, 0, :].numpy()
                embeddings.extend(cls_embeddings)
                
        return np.array(embeddings)
    
    def compute_mgte_embeddings(self, texts: List[str]) -> np.ndarray:
        """Compute mGTE embeddings for text list."""
        self.load_mgte_model()
        
        # mGTE handles batching internally
        embeddings = self.mgte_model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        return embeddings

    def get_addresses_without_embeddings(self, embedding_type: str, limit: int = 1000) -> List[Tuple[int, str]]:
        """Get addresses that don't have embeddings yet."""
        conn = psycopg2.connect(**self.db_config)
        
        embedding_col = f"{embedding_type}_embedding"
        
        try:
            with conn.cursor() as cur:
                query = f"""
                    SELECT id, standardized_address
                    FROM prq.address_clean_corpus
                    WHERE is_active = true 
                      AND {embedding_col} IS NULL
                    ORDER BY quality_score DESC, id
                    LIMIT %s
                """
                
                cur.execute(query, (limit,))
                return cur.fetchall()
                
        finally:
            conn.close()
    
    def _detect_column_type(self, column: str) -> str:
        """Return the udt_name of the embedding column (e.g. 'vector' or 'jsonb')."""
        conn = psycopg2.connect(**self.db_config)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT udt_name FROM information_schema.columns
                    WHERE table_schema='prq' AND table_name='address_clean_corpus'
                      AND column_name=%s
                    """,
                    (column,),
                )
                row = cur.fetchone()
                return (row[0] if row else "") or ""
        finally:
            conn.close()

    def update_embeddings(self, embedding_type: str, id_embedding_pairs: List[Tuple[int, np.ndarray]]):
        """Update embeddings in database, supporting both vector(768) and jsonb columns.

        When pgvector is not installed the corpus columns fall back to jsonb,
        so we write a JSON array instead of a literal vector cast.
        """
        conn = psycopg2.connect(**self.db_config)

        embedding_col = f"{embedding_type}_embedding"
        col_type = self._detect_column_type(embedding_col).lower()
        is_vector = col_type == "vector"
        if not is_vector:
            logger.info(
                "📝 Embedding column %s is %s; writing JSON array (pgvector not active)",
                embedding_col, col_type or "unknown",
            )

        try:
            with conn.cursor() as cur:
                for record_id, embedding in id_embedding_pairs:
                    if is_vector:
                        vector_literal = "[" + ",".join(f"{float(v):.8f}" for v in embedding.tolist()) + "]"
                        cur.execute(
                            f"""
                            UPDATE prq.address_clean_corpus
                            SET {embedding_col} = %s::vector,
                                embedding_version = 'v1',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (vector_literal, record_id),
                        )
                    else:
                        json_payload = json.dumps([float(v) for v in embedding.tolist()])
                        cur.execute(
                            f"""
                            UPDATE prq.address_clean_corpus
                            SET {embedding_col} = %s::jsonb,
                                embedding_version = 'v1',
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (json_payload, record_id),
                        )

                conn.commit()
                logger.info(f"✅ Updated {len(id_embedding_pairs)} {embedding_type} embeddings")

        except Exception as e:
            logger.error(f"❌ Error updating embeddings: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def compute_and_store_embeddings(
        self,
        embedding_type: str,
        batch_size: int = 500,
        max_batches: Optional[int] = None,
    ):
        """Compute and store embeddings for corpus addresses.

        If ``max_batches`` is set, stop after that many DB update batches (useful
        for smoke runs on huge corpora). Default ``None`` = process until empty.
        """
        logger.info(f"🧠 Starting {embedding_type} embedding computation...")
        
        total_processed = 0
        checkpoint_path = f"reports/{embedding_type}_embedding_checkpoint.json"
        batches_done = 0
        
        while True:
            if max_batches is not None and batches_done >= max_batches:
                logger.info(
                    "⏹️ Stopping after %d batches (--max-batches) for %s",
                    max_batches,
                    embedding_type,
                )
                break
            # Get next batch of addresses without embeddings
            addresses_data = self.get_addresses_without_embeddings(embedding_type, batch_size)
            
            if not addresses_data:
                logger.info(f"✅ All addresses have {embedding_type} embeddings")
                break
                
            # Extract IDs and texts
            ids = [item[0] for item in addresses_data]
            texts = [item[1] for item in addresses_data]
            
            logger.info(f"🔄 Computing {embedding_type} embeddings for {len(texts)} addresses...")
            
            # Compute embeddings
            if embedding_type == 'mgte':
                embeddings = self.compute_mgte_embeddings(texts)
            elif embedding_type == 'phobert':
                embeddings = self.compute_phobert_embeddings(texts)
            else:
                raise ValueError(f"Unsupported embedding type: {embedding_type}")
            
            # Prepare data for update
            id_embedding_pairs = list(zip(ids, embeddings))
            
            # Update database
            self.update_embeddings(embedding_type, id_embedding_pairs)
            
            total_processed += len(texts)
            batches_done += 1
            logger.info(f"📊 Total processed: {total_processed}")
            os.makedirs("reports", exist_ok=True)
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump({"embedding_type": embedding_type, "processed": total_processed}, f, indent=2)
            
        logger.info(f"🎉 {embedding_type.upper()} embedding computation completed! Total: {total_processed}")
    
    def get_embedding_stats(self):
        """Get statistics about embeddings in corpus."""
        conn = psycopg2.connect(**self.db_config)
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN mgte_embedding IS NOT NULL THEN 1 END) as has_mgte,
                        COUNT(CASE WHEN phobert_embedding IS NOT NULL THEN 1 END) as has_phobert,
                        COUNT(CASE WHEN mgte_embedding IS NOT NULL AND phobert_embedding IS NOT NULL THEN 1 END) as has_both
                    FROM prq.address_clean_corpus
                    WHERE is_active = true
                """)
                
                stats = cur.fetchone()
                
                logger.info("📊 Embedding Statistics:")
                logger.info(f"   Total addresses: {stats[0]}")
                logger.info(f"   mGTE embeddings: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
                logger.info(f"   PhoBERT embeddings: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
                logger.info(f"   Both embeddings: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
                
                return stats
                
        finally:
            conn.close()

def main():
    """Main function to compute embeddings."""
    import argparse

    parser = argparse.ArgumentParser(description="Compute PhoBERT + mGTE embeddings for address_clean_corpus")
    parser.add_argument(
        "--phobert-batch-size",
        type=int,
        default=50,
        help="Rows per batch for PhoBERT updates",
    )
    parser.add_argument(
        "--mgte-batch-size",
        type=int,
        default=100,
        help="Rows per batch for mGTE updates",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Optional cap on batches per embedding type (smoke runs); omit for full corpus",
    )
    parser.add_argument(
        "--skip-phobert",
        action="store_true",
        help="Only run mGTE pass",
    )
    parser.add_argument(
        "--skip-mgte",
        action="store_true",
        help="Only run PhoBERT pass",
    )
    args = parser.parse_args()

    logger.info("🚀 Starting embedding computation...")
    
    computer = EmbeddingComputer()
    
    # Show current stats
    computer.get_embedding_stats()
    
    if not args.skip_phobert:
        logger.info("\n" + "="*50)
        logger.info("🎯 Computing PhoBERT embeddings...")
        computer.compute_and_store_embeddings(
            "phobert",
            batch_size=args.phobert_batch_size,
            max_batches=args.max_batches,
        )
    
    if not args.skip_mgte:
        logger.info("\n" + "="*50)
        logger.info("🎯 Computing mGTE embeddings...")
        computer.compute_and_store_embeddings(
            "mgte",
            batch_size=args.mgte_batch_size,
            max_batches=args.max_batches,
        )
    
    # Final stats
    logger.info("\n" + "="*50)
    logger.info("🏁 Final embedding statistics:")
    computer.get_embedding_stats()

if __name__ == "__main__":
    main()