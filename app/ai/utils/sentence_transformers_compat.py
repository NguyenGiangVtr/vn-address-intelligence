"""
Tương thích sentence-transformers: API đổi tên theo phiên bản.

- Module backbone (Transformer): get_embedding_dimension (mới) vs get_word_embedding_dimension (cũ).
- SentenceTransformer: get_embedding_dimension (mới) vs get_sentence_embedding_dimension (cũ).

VPS thường pin bộ cũ hơn máy dev → dùng helper thay vì gọi trực tiếp một tên.
"""

from __future__ import annotations

from typing import Any, Optional


def transformer_backbone_embedding_dim(module: Any) -> int:
    """
    Chiều vector token từ backbone (đầu vào pooling), dùng khi tạo ``models.Pooling(...)``.
    """
    for name in ("get_embedding_dimension", "get_word_embedding_dimension"):
        fn = getattr(module, name, None)
        if callable(fn):
            dim = fn()
            if dim is not None:
                return int(dim)

    inner = getattr(module, "auto_model", None) or getattr(module, "model", None)
    cfg = getattr(inner, "config", None) if inner is not None else None
    hidden = getattr(cfg, "hidden_size", None)
    if hidden is not None:
        return int(hidden)

    raise AttributeError(
        f"{type(module).__name__}: không suy ra được embedding dim cho Pooling "
        "(thiếu get_embedding_dimension / get_word_embedding_dimension / config.hidden_size)."
    )


def sentence_transformer_output_dim(model: Any) -> Optional[int]:
    """
    Chiều vector sau ``encode`` (sau pooling), phù hợp log / kiểm tra.
    Trả None nếu không suy ra được (hiếm).
    """
    for name in ("get_embedding_dimension", "get_sentence_embedding_dimension"):
        fn = getattr(model, name, None)
        if callable(fn):
            dim = fn()
            if dim is not None:
                return int(dim)
    return None
