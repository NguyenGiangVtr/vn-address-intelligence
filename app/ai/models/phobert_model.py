"""
models/phobert_model.py
=======================
PhoBERT Siamese Network (Bi-Encoder) dùng để chuẩn hóa địa chỉ:
  1. Encode query và toàn bộ corpus địa chỉ chuẩn thành dense vectors.
  2. Cosine-similarity → chọn địa chỉ chuẩn gần nhất.

Yêu cầu: vinai/phobert-base, sentence-transformers, pyvi (tách từ).
"""

import logging
import time
from typing import List, Optional, Tuple

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, models

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Optional word segmentation (PhoBERT performs better with segmented input)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from pyvi import ViTokenizer
    _HAS_PYVI = True
except ImportError:
    _HAS_PYVI = False
    logger.warning("️  pyvi chưa cài — PhoBERT sẽ dùng raw text (giảm độ chính xác).")


def _segment(text: str) -> str:
    """Tách từ tiếng Việt cho PhoBERT."""
    if _HAS_PYVI and text:
        return ViTokenizer.tokenize(text)
    return text


# ──────────────────────────────────────────────────────────────────────────────
# PhoBERT Siamese Model
# ──────────────────────────────────────────────────────────────────────────────
class PhoBERTSiamese:
    """
    Siamese Network dùng PhoBERT làm backbone.
    Hoạt động như Bi-Encoder: encode corpus một lần, tại query-time
    chỉ cần encode query rồi tính cosine similarity.
    """

    MODEL_NAME = "vinai/phobert-base"

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        max_seq_length: int = 256,
        batch_size: int = 32,
        device: str = "auto",
    ):
        self.model_name     = model_name
        self.max_seq_length = max_seq_length
        self.batch_size     = batch_size
        self.device         = self._resolve_device(device)

        logger.info(" Loading PhoBERT: %s (device=%s)", model_name, self.device)
        transformer = models.Transformer(model_name, max_seq_length=max_seq_length)
        pooling     = models.Pooling(transformer.get_word_embedding_dimension())
        self.model  = SentenceTransformer(modules=[transformer, pooling], device=self.device)
        self.model.eval()

        # Pre-computed corpus embeddings
        self._corpus: List[str]    = []
        self._corpus_emb: Optional[np.ndarray] = None

        logger.info(" PhoBERT Siamese loaded.")

    # ------------------------------------------------------------------
    def _resolve_device(self, device: str) -> str:
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    # ------------------------------------------------------------------
    def encode_corpus(self, addresses: List[str]):
        """Pre-compute embeddings cho toàn bộ corpus (chạy 1 lần)."""
        logger.info(" Encoding %d corpus addresses (PhoBERT)...", len(addresses))
        segmented = [_segment(a) for a in addresses]
        self._corpus = addresses  # giữ original để trả kết quả
        self._corpus_emb = self.model.encode(
            segmented,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        logger.info(" Corpus encoded. Shape: %s", self._corpus_emb.shape)

    # ------------------------------------------------------------------
    def normalize(self, query: str, top_k: int = 1) -> Tuple[str, float, float]:
        """
        Chuẩn hóa một địa chỉ.

        Returns
        -------
        (best_address, cosine_score, latency_ms)
        """
        assert self._corpus_emb is not None, "Gọi encode_corpus() trước."
        t0 = time.time()

        q_emb  = self.model.encode(
            [_segment(query)],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        scores = self._corpus_emb @ q_emb          # cosine (do normalized)
        idx    = int(np.argmax(scores))

        latency_ms = (time.time() - t0) * 1000
        return self._corpus[idx], float(scores[idx]), latency_ms

    # ------------------------------------------------------------------
    def normalize_batch(self, queries: List[str]) -> List[Tuple[str, float, float]]:
        """Chuẩn hóa nhiều địa chỉ, trả về list (address, score, latency_ms)."""
        return [self.normalize(q) for q in queries]
