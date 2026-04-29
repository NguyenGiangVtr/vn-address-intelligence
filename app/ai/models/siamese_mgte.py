"""
models/siamese_mgte.py
======================
mGTE (Alibaba-NLP/gte-multilingual-base) Siamese Bi-Encoder —
baseline đa ngôn ngữ, đúng như Layer 2 của hệ thống hiện tại.
"""

import logging
import time
from typing import List, Optional, Tuple

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SiameseMGTE:
    """
    Siamese Network dùng mGTE (multilingual) làm backbone.
    Zero-shot, không cần fine-tune — dùng làm baseline.
    """

    MODEL_NAME = "Alibaba-NLP/gte-multilingual-base"

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        batch_size: int = 32,
        device: str = "auto",
    ):
        self.model_name = model_name
        self.batch_size = batch_size
        self.device     = "cuda" if (device == "auto" and torch.cuda.is_available()) else ("cpu" if device == "auto" else device)

        logger.info(" Loading mGTE: %s (device=%s)", model_name, self.device)
        self.model = SentenceTransformer(
            model_name, 
            device=self.device,
            trust_remote_code=True
        )
        self.model.eval()

        self._corpus: List[str]             = []
        self._corpus_emb: Optional[np.ndarray] = None

        logger.info(" mGTE Siamese loaded. Emb dim: %d",
                    self.model.get_sentence_embedding_dimension())

    # ------------------------------------------------------------------
    def encode_corpus(self, addresses: List[str]):
        """Pre-compute corpus embeddings (chạy 1 lần)."""
        logger.info(" Encoding %d corpus addresses (mGTE)...", len(addresses))
        self._corpus     = addresses
        self._corpus_emb = self.model.encode(
            addresses,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        logger.info(" mGTE corpus encoded. Shape: %s", self._corpus_emb.shape)

    # ------------------------------------------------------------------
    def normalize(self, query: str, top_k: int = 1) -> Tuple[str, float, float]:
        """
        Returns
        -------
        (best_address, cosine_score, latency_ms)
        """
        assert self._corpus_emb is not None, "Gọi encode_corpus() trước."
        t0 = time.time()

        q_emb  = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._corpus_emb @ q_emb
        idx    = int(np.argmax(scores))

        latency_ms = (time.time() - t0) * 1000
        return self._corpus[idx], float(scores[idx]), latency_ms

    # ------------------------------------------------------------------
    def normalize_batch(self, queries: List[str]) -> List[Tuple[str, float, float]]:
        return [self.normalize(q) for q in queries]
eries]
