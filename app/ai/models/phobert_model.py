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

from app.ai.utils.sentence_transformers_compat import transformer_backbone_embedding_dim
from app.ai.utils.torch_hf_weights_compat import hf_trusted_torch_load

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
        # PyTorch 2.6+ defaults torch.load(weights_only=True); pytorch_model.bin của HF thường cần False.
        with hf_trusted_torch_load():
            transformer = models.Transformer(model_name, max_seq_length=max_seq_length)
            pooling = models.Pooling(transformer_backbone_embedding_dim(transformer))
            self.model = SentenceTransformer(
                modules=[transformer, pooling], device=self.device
            )
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
        if not addresses:
            raise ValueError("Cannot encode an empty corpus. Provide at least one address.")
        
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
        
        # Validate embeddings shape
        if self._corpus_emb.shape[0] != len(addresses):
            raise ValueError(
                f"Embeddings shape mismatch: got {self._corpus_emb.shape[0]} embeddings "
                f"but expected {len(addresses)} for the corpus."
            )
        
        if self._corpus_emb.ndim != 2:
            raise ValueError(f"Embeddings must be 2D array, got shape: {self._corpus_emb.shape}")
        
        # Check for NaN or inf in embeddings
        if np.any(np.isnan(self._corpus_emb)) or np.any(np.isinf(self._corpus_emb)):
            nan_count = np.sum(np.isnan(self._corpus_emb))
            inf_count = np.sum(np.isinf(self._corpus_emb))
            logger.warning("Embeddings contain NaN (%d) or Inf (%d) values", nan_count, inf_count)
            # Replace NaN/Inf with zeros (safe fallback)
            self._corpus_emb = np.nan_to_num(self._corpus_emb, nan=0.0, posinf=0.0, neginf=0.0)
        
        logger.info(" Corpus encoded. Shape: %s", self._corpus_emb.shape)

    # ------------------------------------------------------------------
    def normalize(self, query: str, top_k: int = 1) -> Tuple[str, float, float]:
        """
        Chuẩn hóa một địa chỉ.

        Returns
        -------
        (best_address, cosine_score, latency_ms)
        """
        if self._corpus_emb is None:
            raise RuntimeError(
                "Corpus embeddings not initialized. Call encode_corpus() with addresses first."
            )
        
        if self._corpus_emb.size == 0:
            raise ValueError("Corpus embeddings are empty. Call encode_corpus() with non-empty addresses.")
        
        if len(self._corpus) == 0:
            raise ValueError("Corpus addresses list is empty.")
        
        if self._corpus_emb.shape[0] != len(self._corpus):
            raise ValueError(
                f"Corpus data integrity check failed: {self._corpus_emb.shape[0]} embeddings "
                f"but {len(self._corpus)} addresses. This indicates data corruption."
            )
        
        t0 = time.time()

        q_emb  = self.model.encode(
            [_segment(query)],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0]
        scores = self._corpus_emb @ q_emb          # cosine (do normalized)
        idx    = int(np.argmax(scores))
        
        # Validate index
        if idx < 0 or idx >= len(self._corpus):
            raise IndexError(
                f"Computed index {idx} is out of bounds for corpus of size {len(self._corpus)}"
            )

        latency_ms = (time.time() - t0) * 1000
        return self._corpus[idx], float(scores[idx]), latency_ms

    # ------------------------------------------------------------------
    def normalize_batch(self, queries: List[str]) -> List[Tuple[str, float, float]]:
        """Chuẩn hóa nhiều địa chỉ, trả về list (address, score, latency_ms)."""
        return [self.normalize(q) for q in queries]
