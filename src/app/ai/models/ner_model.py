"""
ner_model.py
============
Mô hình Named Entity Recognition (NER): fine-tuned PhoBERT cục bộ hoặc model
Hugging Face (token classification), ví dụ dathuynh1108/ner-address-electra-base-vn.

Dataset tham chiếu: https://huggingface.co/datasets/dathuynh1108/ner-address-standard-dataset
Model tham chiếu: https://huggingface.co/dathuynh1108/ner-address-electra-base-vn
"""

import logging
import torch
from typing import List, Dict, Any, Optional
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

from app.ai.utils.torch_hf_weights_compat import hf_trusted_torch_load

logger = logging.getLogger(__name__)

# Nhãn BIO từ bộ dữ liệu / model Electra chuẩn hoá → mã trong constants (STR, WDS, DST, PRO)
HF_ENTITY_TO_INTERNAL = {
    "STREET": "STR",
    "WARD": "WDS",
    "DISTRICT": "DST",
    "PROVINCE": "PRO",
}

DEFAULT_HF_NER_MODEL_ID = "dathuynh1108/ner-address-electra-base-vn"


def resolve_ner_model_path() -> str:
    """
    Thứ tự giống production: NER_MODEL_ID → thư mục models/phobert-ner-vn → id Hugging Face mặc định.
    """
    import os
    from pathlib import Path

    env_ner = (os.environ.get("NER_MODEL_ID") or "").strip()
    if env_ner:
        return env_ner
    local = Path("models/phobert-ner-vn")
    if local.exists():
        return str(local)
    return DEFAULT_HF_NER_MODEL_ID


class AddressNER:
    """
    Sử dụng PhoBERT Fine-tuned để bóc tách thành phần địa chỉ.
    Nhãn hỗ trợ: Xem chi tiết tại app/ai/constants.py
    """
    
    def __init__(self, model_path: str = "vinai/phobert-base", device: str = "auto"):
        self.device = 0 if (device == "auto" and torch.cuda.is_available()) else -1
        self.model_path = model_path
        self.ner_pipeline = None

        model_dir = model_path.strip() if isinstance(model_path, str) else ""
        # Chỉ bỏ qua khi không cấu hình path, hoặc khi dùng đúng backbone PhoBERT chưa fine-tune
        skip_load = (not model_dir) or model_dir == "vinai/phobert-base"

        if skip_load:
            logger.info("NER fine-tuned model not configured/found. Using Regex fallback.")
            return
        
        try:
            logger.info(f"Loading fine-tuned NER model from {model_path}...")
            with hf_trusted_torch_load():
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_path, trust_remote_code=True
                )
                if getattr(self.tokenizer, "model_max_length", 512) > 4096:
                    self.tokenizer.model_max_length = 512
                self.model = AutoModelForTokenClassification.from_pretrained(model_path)
            
            # token-classification (cùng task NER); hỗ trợ Electra/PhoBERT fine-tuned
            self.ner_pipeline = pipeline(
                "token-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device,
                aggregation_strategy="simple",
            )
            logger.info("Fine-tuned NER model loaded.")
        except Exception as e:
            logger.warning(f"Cannot load fine-tuned NER model at {model_path}. Using Regex fallback. Error: {e}")

    def extract(self, text: str) -> Dict[str, str]:
        """
        Bóc tách địa chỉ thành các thực thể.
        """
        if not text:
            return {}
            
        if self.ner_pipeline:
            try:
                entities = self.ner_pipeline(text, truncation=True, max_length=512)
            except TypeError:
                entities = self.ner_pipeline(text)
            return self._format_entities(entities)
        else:
            return self._regex_fallback(text)

    @staticmethod
    def _normalize_span_label(entity_group: Optional[str]) -> str:
        """B-/I-STREET (HF) hoặc STR (model nội bộ) → mã thống nhất STR/WDS/DST/PRO."""
        if not entity_group:
            return ""
        g = entity_group.strip()
        if g.startswith("B-") or g.startswith("I-"):
            g = g[2:]
        return HF_ENTITY_TO_INTERNAL.get(g.upper(), g)

    def _format_entities(self, entities: List[Any]) -> Dict[str, str]:
        """Gom các span cùng loại (ví dụ nhiều cụm STREET) thành một chuỗi."""
        merged: Dict[str, List[str]] = defaultdict(list)
        for ent in entities:
            label = self._normalize_span_label(ent.get("entity_group") or ent.get("entity"))
            if not label or label.upper() == "O":
                continue
            word = (ent.get("word") or "").replace("@@ ", "").strip()
            if not word:
                continue
            merged[label].append(word)
        return {k: " ".join(v) for k, v in merged.items()}

    def _regex_fallback(self, text: str) -> Dict[str, str]:
        """Bộ lọc thô bằng Regex khi chưa có AI model."""
        import re
        result = {}
        # Tìm số nhà (đầu chuỗi)
        num_match = re.match(r'^(Số\s)?([\d\w/.\-]+)', text, re.I)
        if num_match:
            result['NUM'] = num_match.group(2)
            # Giả định phần còn lại là đường
            street_part = text[num_match.end():].strip().strip(',')
            if street_part:
                result['STR'] = street_part
        else:
            result['STR'] = text
        return result
