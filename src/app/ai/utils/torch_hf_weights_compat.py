"""
Tương thích PyTorch 2.6+ khi transformers / sentence-transformers load pytorch_model.bin:
mặc định có thể dùng torch.load(..., weights_only=True) và từ chối checkpoint cũ.

Khi load trọng số từ Hugging Face cache hoặc thư mục mô hình tin cậy, cần
weights_only=False (đúng như các phiên bản PyTorch cũ hơn).
"""

from __future__ import annotations

import contextlib
import functools
import inspect
from typing import Any, Callable

import torch


def _wrap_torch_load(orig: Callable[..., Any]) -> Callable[..., Any]:
    sig = inspect.signature(orig)
    supports_weights_only = "weights_only" in sig.parameters

    @functools.wraps(orig)
    def _inner(*args: Any, **kwargs: Any):
        if supports_weights_only:
            kwargs.setdefault("weights_only", False)
        return orig(*args, **kwargs)

    return _inner


@contextlib.contextmanager
def hf_trusted_torch_load():
    """
    Patch torch.load tạm thời: thêm weights_only=False nếu caller chưa truyền.
    Không đè biến nếu caller đã chỉ định weights_only=True một cách tường minh —
    chỉ khác khi không có trong kwargs (ghi nhận bằng setdefault).

    Scope: chỉ nên bọc các lệnh load mô hình HF / local tin cậy.
    """
    orig = torch.load
    torch.load = _wrap_torch_load(orig)
    try:
        yield
    finally:
        torch.load = orig
