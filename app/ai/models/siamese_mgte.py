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

    # ------------------------------------------------------------------
    def match_with_temporal(
        self,
        query: str,
        epoch_filter: Optional[str] = None,
        admin_version_filter: Optional[int] = None,
        top_k: int = 1,
    ) -> Tuple[str, float, float]:
        """
        Temporal-aware matching: lọc corpus theo epoch / admin_version trước khi tính similarity.

        Parameters
        ----------
        query                : Địa chỉ cần khớp
        epoch_filter         : 'PRE_2025' | 'POST_2025' | None (không lọc)
        admin_version_filter : 1 (Pre-2025) | 2 (Post-2025) | None (không lọc)
        top_k                : Số kết quả trả về (hiện tại luôn 1)

        Returns
        -------
        (best_address, cosine_score, latency_ms)

        Ghi chú: Corpus mặc định không chứa metadata epoch.
        Khi corpus được tải từ DB (via encode_corpus_with_metadata),
        phương thức này sẽ lọc theo epoch trước khi tính cosine similarity.
        """
        assert self._corpus_emb is not None, "Gọi encode_corpus() trước."
        t0 = time.time()

        # Xác định indices cần dùng (lọc theo epoch nếu có metadata)
        if hasattr(self, "_corpus_metadata") and self._corpus_metadata and epoch_filter:
            valid_indices = [
                i for i, meta in enumerate(self._corpus_metadata)
                if meta.get("epoch") == epoch_filter
                or (admin_version_filter and meta.get("admin_version") == admin_version_filter)
            ]
            if not valid_indices:
                # Fallback về toàn bộ corpus nếu không có entry phù hợp
                valid_indices = list(range(len(self._corpus)))
        else:
            valid_indices = list(range(len(self._corpus)))

        filtered_emb    = self._corpus_emb[valid_indices]
        filtered_corpus = [self._corpus[i] for i in valid_indices]

        q_emb  = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = filtered_emb @ q_emb
        idx    = int(np.argmax(scores))

        latency_ms = (time.time() - t0) * 1000
        return filtered_corpus[idx], float(scores[idx]), latency_ms

    def encode_corpus_with_metadata(
        self,
        addresses: List[str],
        metadata: Optional[List[dict]] = None,
    ):
        """
        Mở rộng encode_corpus để lưu metadata (epoch, admin_version…) kèm theo.

        Parameters
        ----------
        addresses : Danh sách địa chỉ corpus
        metadata  : Danh sách dict cùng độ dài với addresses.
                    Mỗi dict có thể chứa 'epoch' (PRE_2025/POST_2025), 'admin_version'…
        """
        self.encode_corpus(addresses)
        self._corpus_metadata = metadata or []
        logger.info(
            " Corpus metadata loaded: %d entries", len(self._corpus_metadata)
        )
