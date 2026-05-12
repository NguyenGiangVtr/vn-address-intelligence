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

from app.ai.utils.sentence_transformers_compat import sentence_transformer_output_dim

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

        try:
            import sentence_transformers as st
            import transformers

            logger.info(
                " mGTE deps: torch=%s transformers=%s sentence_transformers=%s",
                getattr(torch, "__version__", "?"),
                getattr(transformers, "__version__", "?"),
                getattr(st, "__version__", "?"),
            )
        except Exception:
            pass

        # VPS Debug: Check for einops which is required by GTE remote code
        try:
            import einops
            logger.info(" Dependency check: 'einops' is installed.")
        except ImportError:
            logger.warning(" Dependency check: 'einops' is MISSING. mGTE (Alibaba-NLP) will fail to load!")
            
        try:
            self.model = SentenceTransformer(
                model_name, 
                device=self.device,
                trust_remote_code=True
            )
            self.model.eval()
        except Exception as e:
            logger.error(f" Failed to initialize SentenceTransformer for mGTE: {e}")
            msg = str(e).lower()
            if "out of memory" in msg:
                logger.error(" >>> CRITICAL: CUDA/RAM Out of Memory while loading mGTE.")
            elif "remote code" in msg:
                logger.error(" >>> CRITICAL: Failed to load remote code. Check 'trust_remote_code=True' and internet connection.")
            elif "out of bounds" in msg or ("index" in msg and "bound" in msg):
                logger.error(
                    " >>> Gợi ý (index/embedding out of bounds): thường do cache HF hỏng hoặc "
                    "torch/transformers/tokenizers không tương thích với remote code của gte-multilingual. "
                    "Thử: (1) xóa cache model: rm -rf ~/.cache/huggingface/hub/models--Alibaba-NLP--gte-multilingual-base* "
                    "(hoặc SNAP_HOME tương ứng); (2) pip install -U tokenizers transformers sentence-transformers "
                    "theo requirements-prod.txt; (3) đặt PARSER_MGTE_DEVICE=cpu trong .env rồi restart API."
                )
            raise e

        self._corpus: List[str]             = []
        self._corpus_emb: Optional[np.ndarray] = None

        _edim = sentence_transformer_output_dim(self.model)
        logger.info(
            " mGTE Siamese loaded. Emb dim: %s",
            _edim if _edim is not None else "unknown",
        )

    # ------------------------------------------------------------------
    def encode_corpus(self, addresses: List[str]):
        """Pre-compute corpus embeddings (chạy 1 lần)."""
        if not addresses:
            raise ValueError("Cannot encode an empty corpus. Provide at least one address.")
        
        logger.info(" Encoding %d corpus addresses (mGTE)...", len(addresses))
        self._corpus     = addresses
        self._corpus_emb = self.model.encode(
            addresses,
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
        
        logger.info(" mGTE corpus encoded. Shape: %s", self._corpus_emb.shape)

    # ------------------------------------------------------------------
    def normalize(self, query: str, top_k: int = 1) -> Tuple[str, float, float]:
        """
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

        q_emb  = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._corpus_emb @ q_emb
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
        return [self.normalize(q) for q in queries]

    def retrieve_top_k(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Return top-k corpus candidates and cosine scores."""
        if self._corpus_emb is None or len(self._corpus) == 0:
            raise RuntimeError("Corpus embeddings not initialized. Call encode_corpus() first.")
        k = max(1, min(top_k, len(self._corpus)))
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._corpus_emb @ q_emb
        idxs = np.argpartition(-scores, range(k))[:k]
        sorted_idxs = idxs[np.argsort(-scores[idxs])]
        return [(self._corpus[i], float(scores[i])) for i in sorted_idxs]

    def retrieve_top_k_with_meta(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Like retrieve_top_k but also returns the corpus metadata dict for each
        candidate, so callers can read fields such as ``latitude``/``longitude``.

        Falls back to empty dicts if encode_corpus_with_metadata() was not used.
        """
        if self._corpus_emb is None or len(self._corpus) == 0:
            raise RuntimeError("Corpus embeddings not initialized. Call encode_corpus() first.")
        k = max(1, min(top_k, len(self._corpus)))
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self._corpus_emb @ q_emb
        idxs = np.argpartition(-scores, range(k))[:k]
        sorted_idxs = idxs[np.argsort(-scores[idxs])]
        meta_list = getattr(self, "_corpus_metadata", None) or []
        out: List[Tuple[str, float, dict]] = []
        for i in sorted_idxs:
            meta = meta_list[i] if i < len(meta_list) else {}
            out.append((self._corpus[i], float(scores[i]), meta or {}))
        return out

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
        
        # Validate corpus embeddings integrity
        if self._corpus_emb.size == 0:
            raise ValueError("Corpus embeddings are empty. Call encode_corpus() with non-empty addresses.")
        
        if len(self._corpus) == 0:
            raise ValueError("Corpus addresses list is empty. Call encode_corpus() with non-empty addresses.")
        
        if self._corpus_emb.shape[0] != len(self._corpus):
            raise ValueError(
                f"Corpus embeddings ({self._corpus_emb.shape[0]}) and addresses ({len(self._corpus)}) "
                f"have mismatched lengths. This indicates a data corruption issue."
            )
        
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
                logger.warning(
                    "No corpus entries matched epoch_filter=%s, admin_version_filter=%s. Using full corpus.",
                    epoch_filter, admin_version_filter
                )
                valid_indices = list(range(len(self._corpus)))
        else:
            valid_indices = list(range(len(self._corpus)))

        # Convert to NumPy array for proper fancy indexing
        valid_indices_arr = np.array(valid_indices, dtype=np.int64)
        
        # Validate indices before using them
        if np.any(valid_indices_arr < 0) or np.any(valid_indices_arr >= len(self._corpus)):
            raise IndexError(
                f"Invalid indices generated: min={valid_indices_arr.min()}, max={valid_indices_arr.max()}, "
                f"corpus_size={len(self._corpus)}"
            )
        
        # Apply fancy indexing with NumPy array
        filtered_emb    = self._corpus_emb[valid_indices_arr]
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
