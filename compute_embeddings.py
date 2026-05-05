#!/usr/bin/env python3
"""
Compute embeddings for corpus addresses to optimize retrieval performance.
"""

import os
import logging
import numpy as np
import psycopg2
from dotenv import load_dotenv
from typing import List, Tuple
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
    
    def update_embeddings(self, embedding_type: str, id_embedding_pairs: List[Tuple[int, np.ndarray]]):
        """Update embeddings in database."""
        conn = psycopg2.connect(**self.db_config)
        
        embedding_col = f"{embedding_type}_embedding"
        
        try:
            import json
            
            with conn.cursor() as cur:
                for record_id, embedding in id_embedding_pairs:
                    # Convert numpy array to JSON string for JSONB storage
                    embedding_json = json.dumps(embedding.tolist())
                    
                    cur.execute(f"""
                        UPDATE prq.address_clean_corpus 
                        SET {embedding_col} = %s::jsonb,
                            embedding_version = 'v1',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (embedding_json, record_id))
                
                conn.commit()
                logger.info(f"✅ Updated {len(id_embedding_pairs)} {embedding_type} embeddings")
                
        except Exception as e:
            logger.error(f"❌ Error updating embeddings: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def compute_and_store_embeddings(self, embedding_type: str, batch_size: int = 500):
        """Compute and store embeddings for corpus addresses."""
        logger.info(f"🧠 Starting {embedding_type} embedding computation...")
        
        total_processed = 0
        
        while True:
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
            logger.info(f"📊 Total processed: {total_processed}")
            
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
    logger.info("🚀 Starting embedding computation...")
    
    computer = EmbeddingComputer()
    
    # Show current stats
    computer.get_embedding_stats()
    
    # Compute PhoBERT embeddings first (Vietnamese specialized, no trust_remote_code needed)
    logger.info("\n" + "="*50)
    logger.info("🎯 Computing PhoBERT embeddings...")
    computer.compute_and_store_embeddings('phobert', batch_size=50)
    
    # Compute mGTE embeddings (multilingual baseline)
    logger.info("\n" + "="*50)
    logger.info("🎯 Computing mGTE embeddings...")
    computer.compute_and_store_embeddings('mgte', batch_size=100)
    
    # Final stats
    logger.info("\n" + "="*50)
    logger.info("🏁 Final embedding statistics:")
    computer.get_embedding_stats()

if __name__ == "__main__":
    main()