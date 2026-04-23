"""
models/llm_model.py
===================
Qwen3 LLM Zero-shot: nhận query + top-5 candidates từ retriever,
suy luận và chọn hoặc tạo địa chỉ chuẩn cuối cùng.
"""

import logging
import re
import time
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

import torch

logger = logging.getLogger(__name__)


_PROMPT_TEMPLATE = """Bạn là chuyên gia chuẩn hóa địa chỉ Việt Nam.

Địa chỉ cần chuẩn hóa: {query}

Danh sách địa chỉ ứng viên (chọn hoặc điều chỉnh một trong các ứng viên này):
{candidates}

Yêu cầu:
1. Phân tích địa chỉ gốc
2. Chọn hoặc tạo địa chỉ chuẩn 4 tầng (Số nhà + Đường, Phường/Xã, Quận/Huyện, Tỉnh/Thành phố)
3. Chỉ trả về 1 dòng theo đúng format:
KET_QUA: <địa chỉ chuẩn>
"""


class LLMQwen3:
    """
    Qwen3 LLM dùng để chuẩn hóa địa chỉ zero-shot.
    Có thể dùng kết hợp với bất kỳ retriever nào để lấy candidates.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-4B",
        use_quantization: bool = True,
        max_new_tokens: int = 256,
        temperature: float = 0.3,
        device: str = "auto",
    ):
        self.model_name     = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature    = temperature
        self.device         = device

        logger.info("🔄 Loading Qwen3 LLM: %s ...", model_name)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )

            if use_quantization:
                bnb_cfg = BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=bnb_cfg,
                    device_map="auto",
                    trust_remote_code=True,
                )
                logger.info("   📦 8-bit quantization enabled.")
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    trust_remote_code=True,
                )

            self.model.eval()
            logger.info("✅ Qwen3 loaded successfully.")

        except Exception as exc:
            logger.warning("⚠️ Không load được Qwen3: %s — sẽ dùng rule-based fallback.", exc)
            self.model     = None
            self.tokenizer = None

    # ------------------------------------------------------------------
    # Candidate retrieval helper (simple mGTE cosine if candidates not given)
    # ------------------------------------------------------------------
    @staticmethod
    def _build_candidate_str(candidates: List[str]) -> str:
        return "\n".join(f"  {i+1}. {c}" for i, c in enumerate(candidates[:5]))

    # ------------------------------------------------------------------
    def normalize(
        self,
        query: str,
        candidates: List[str],
    ) -> Tuple[str, float, float]:
        """
        Parameters
        ----------
        query      : địa chỉ thô
        candidates : top-k từ retriever (mGTE/PhoBERT)

        Returns
        -------
        (normalized_address, confidence_score, latency_ms)
        """
        t0 = time.time()

        if self.model is None:
            result = self._rule_fallback(query, candidates)
        else:
            result = self._llm_infer(query, candidates)

        latency_ms = (time.time() - t0) * 1000
        return result[0], result[1], latency_ms

    # ------------------------------------------------------------------
    def _llm_infer(self, query: str, candidates: List[str]) -> Tuple[str, float]:
        prompt = _PROMPT_TEMPLATE.format(
            query=query,
            candidates=self._build_candidate_str(candidates),
        )
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(
                next(self.model.parameters()).device
            )
            with torch.no_grad():
                out = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    top_p=0.95,
                    do_sample=True,
                )
            response = self.tokenizer.decode(out[0], skip_special_tokens=True)

            # Parse "KET_QUA: ..."
            match = re.search(r"KET_QUA\s*:\s*(.+)", response, re.IGNORECASE)
            if match:
                addr = match.group(1).strip()
                # Confidence: similarity với candidate gần nhất
                conf = max(
                    SequenceMatcher(None, addr.lower(), c.lower()).ratio()
                    for c in candidates
                ) if candidates else 0.5
                return addr, conf
            else:
                return self._rule_fallback(query, candidates)

        except Exception as exc:
            logger.warning("⚠️ LLM inference lỗi: %s", exc)
            return self._rule_fallback(query, candidates)

    # ------------------------------------------------------------------
    @staticmethod
    def _rule_fallback(query: str, candidates: List[str]) -> Tuple[str, float]:
        """String similarity fallback."""
        if not candidates:
            return query, 0.0
        scored = sorted(
            candidates,
            key=lambda c: SequenceMatcher(None, query.lower(), c.lower()).ratio(),
            reverse=True,
        )
        best = scored[0]
        conf = SequenceMatcher(None, query.lower(), best.lower()).ratio()
        return best, conf

    # ------------------------------------------------------------------
    def normalize_batch(
        self,
        queries: List[str],
        candidates_list: List[List[str]],
    ) -> List[Tuple[str, float, float]]:
        """Batch normalize, mỗi query kèm danh sách candidates riêng."""
        assert len(queries) == len(candidates_list)
        return [
            self.normalize(q, cands)
            for q, cands in zip(queries, candidates_list)
        ]
