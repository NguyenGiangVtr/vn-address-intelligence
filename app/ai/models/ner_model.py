"""
ner_model.py
============
Mô hình Named Entity Recognition (NER) dựa trên PhoBERT.
Dùng để bóc tách: Số nhà, Tên đường, Tòa nhà, Hẻm...
"""

import logging
import torch
import json
from typing import List, Dict, Any
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

logger = logging.getLogger(__name__)

from constants import get_label_count

class AddressNER:
    """
    Sử dụng PhoBERT Fine-tuned để bóc tách thành phần địa chỉ.
    Nhãn hỗ trợ: Xem chi tiết tại app/ai/constants.py
    """
    
    def __init__(self, model_path: str = "vinai/phobert-base", device: str = "auto"):
        self.device = 0 if (device == "auto" and torch.cuda.is_available()) else -1
        self.model_path = model_path
        
        try:
            logger.info(f"🔄 Loading NER Model from {model_path}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            self.model = AutoModelForTokenClassification.from_pretrained(model_path)
            
            # Khởi tạo pipeline NER của HuggingFace
            self.ner_pipeline = pipeline(
                "ner", 
                model=self.model, 
                tokenizer=self.tokenizer, 
                device=self.device,
                aggregation_strategy="simple" # Gộp các sub-tokens thành word
            )
            logger.info("✅ NER Model loaded.")
        except Exception as e:
            logger.warning(f"⚠️ Chưa có model Fine-tuned tại {model_path}. Hệ thống sẽ dùng Regex-fallback. Lỗi: {e}")
            self.ner_pipeline = None

    def extract(self, text: str) -> Dict[str, str]:
        """
        Bóc tách địa chỉ thành các thực thể.
        """
        if not text:
            return {}
            
        if self.ner_pipeline:
            entities = self.ner_pipeline(text)
            return self._format_entities(entities)
        else:
            return self._regex_fallback(text)

    def _format_entities(self, entities: List[Any]) -> Dict[str, str]:
        """Convert HuggingFace NER output to friendly Dict."""
        result = {}
        for ent in entities:
            label = ent['entity_group']
            word = ent['word'].replace("@@ ", "") # Khử wordpiece của PhoBERT
            result[label] = word.strip()
        return result

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
