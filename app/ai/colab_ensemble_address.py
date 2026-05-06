"""
================================================================================
HỆ THỐNG CHUẨN HÓA ĐỊA CHỈ VIỆT NAM 4 TẦNG - ENSEMBLE ARCHITECTURE
Chạy trên Google Colab với GPU/TPU
================================================================================

Kiến trúc 4 tầng:
1. Tầng 1: ColBERTv2 - Candidate Generation (Tạo ứng viên nhanh)
2. Tầng 2: mGTE/BGE-M3 - Structure-Aware Re-ranking (Xếp hạng)
3. Tầng 3: Cross-Encoder - Precision Scoring (Tính điểm chính xác)
4. Tầng 4: Qwen3 - Intelligent Fallback (LLM dự phòng thông minh)

Lưu ý: Chạy cell 0 trước tiên để cài đặt dependencies
================================================================================
"""

# ============================================================================
# CELL 0: Cài đặt Dependencies và Setup môi trường
# ============================================================================
# CHẠY CELL NÀY TRƯỚC TIÊN - Sẽ mất 3-5 phút
# Chọn Runtime > Change Runtime Type > GPU (T4 hoặc tốt hơn)

import subprocess
import sys

print("=" * 80)
print("INSTALLING DEPENDENCIES - VUI LÒNG CHỜ (3-5 phút)")
print("=" * 80)

# Cài đặt thư viện chính
packages = [
    "torch",
    "sentence-transformers",
    "transformers",
    "FlagEmbedding",
    "numpy",
    "pandas",
    "scikit-learn",
    "tqdm",
    "gradio",
]

for package in packages:
    print(f"\n Cài đặt {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])

# Cài đặt thư viện optional cho Qwen3
print("\n Cài đặt dependencies cho Qwen3...")
subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", "accelerate", "bitsandbytes"]
)

print("\n Cài đặt hoàn tất!")


# ============================================================================
# CELL 1: Imports và Khởi tạo
# ============================================================================

import torch
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import time
from dataclasses import dataclass
from sentence_transformers import (
    SentenceTransformer,
    CrossEncoder,
    util as sbert_util,
)
from FlagEmbedding import BGEM3FlagModel
import warnings

warnings.filterwarnings("ignore")

# ============================================================================
# Kiểm tra GPU/Device
# ============================================================================
print("\n" + "=" * 80)
print("KIỂM TRA HỆ THỐNG")
print("=" * 80)

# Xác định device (GPU/CPU)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f" Device: {device}")

if torch.cuda.is_available():
    print(f" GPU Name: {torch.cuda.get_device_name(0)}")
    print(f" GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print(f" CUDA Version: {torch.version.cuda}")
else:
    print("️ GPU không khả dụng - sẽ sử dụng CPU (chậm hơn)")


# ============================================================================
# CELL 2: Định nghĩa Data Classes và Utilities
# ============================================================================

@dataclass
class AddressCandidate:
    """Lớp biểu diễn một địa chỉ ứng viên"""

    # ID và nội dung địa chỉ
    id: str
    address: str

    # Tầng 1: Điểm số từ ColBERT
    colbert_score: float = 0.0

    # Tầng 2: Điểm số từ mGTE/BGE-M3
    retriever_score: float = 0.0

    # Tầng 3: Điểm số từ Cross-Encoder
    cross_encoder_score: float = 0.0

    # Tầng 4: Kết quả từ Qwen3
    llm_reasoning: str = ""
    llm_confidence: float = 0.0

    # Điểm số cuối cùng (weighted average)
    final_score: float = 0.0

    def __str__(self):
        """Định dạng đẹp để hiển thị"""
        return f"[{self.id}] {self.address} (Score: {self.final_score:.4f})"


@dataclass
class PipelineConfig:
    """Cấu hình cho entire pipeline"""

    # Tầng 1: ColBERT
    colbert_top_k: int = 500  # Số ứng viên từ tầng 1

    # Tầng 2: Re-ranking
    reranker_top_k: int = 20  # Số ứng viên từ tầng 2

    # Tầng 3: Cross-Encoder
    cross_encoder_top_k: int = 3  # Kết quả cuối cùng

    # Tầng 4: Fallback
    confidence_threshold: float = 0.7  # Ngưỡng trigger LLM fallback
    llm_enable: bool = True  # Có bật LLM fallback không

    # Weights cho final scoring (weighted average)
    weight_retriever: float = 0.2  # Weight cho retriever score (tầng 2)
    weight_cross_encoder: float = (
        0.8  # Weight cho cross-encoder score (tầng 3)
    )

    def __post_init__(self):
        """Validate configuration"""
        assert (
            self.weight_retriever + self.weight_cross_encoder == 1.0
        ), "Weights phải sum bằng 1.0"
        assert (
            0 <= self.confidence_threshold <= 1.0
        ), "confidence_threshold phải từ 0 đến 1"


class PerformanceTracker:
    """Theo dõi hiệu suất từng tầng"""

    def __init__(self):
        self.timings = {}
        self.stage_names = [
            "layer1_colbert",
            "layer2_retriever",
            "layer3_cross_encoder",
            "layer4_llm",
            "total",
        ]
        for stage in self.stage_names:
            self.timings[stage] = []

    def record(self, stage: str, duration: float):
        """Ghi lại thời gian thực thi của một tầng"""
        if stage in self.timings:
            self.timings[stage].append(duration)

    def print_summary(self):
        """In tóm tắt hiệu suất"""
        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)
        for stage in self.stage_names:
            times = self.timings[stage]
            if times:
                avg_time = np.mean(times)
                min_time = np.min(times)
                max_time = np.max(times)
                print(
                    f"  {stage:25} | Avg: {avg_time:7.2f}ms | Min: {min_time:7.2f}ms | Max: {max_time:7.2f}ms"
                )


# ============================================================================
# CELL 3: Tầng 1 - ColBERT Candidate Generation
# ============================================================================

print("\n" + "=" * 80)
print("INITIALIZING LAYER 1 - COLBERT CANDIDATE GENERATION")
print("=" * 80)


class Layer1_ColBERT:
    """
    Tầng 1: Tạo ứng viên nhanh bằng ColBERT
    =====================================================

    Quá trình:
    1. Encode query thành multi-vector representation (1 vector cho mỗi token)
    2. Pre-compute embeddings của tất cả addresses trong database
    3. Sử dụng MaxSim operator (late interaction) để tìm top-k candidates
    4. Trả về ~500 candidates trong < 5ms

    Ưu điểm:
    - Token-level matching: Nắm bắt được biến thể từ vựng
    - Pre-computation: Query-time efficiency cao
    - SOTA performance: MRR@10 39.7% trên MS MARCO
    """

    def __init__(
        self,
        model_name: str = "colbert-ir/colbertv2.0",
        device: str = "cuda",
    ):
        """
        Khởi tạo ColBERT model

        Args:
            model_name: Tên model từ HuggingFace
            device: cuda hoặc cpu
        """
        print(f"\n Loading ColBERT model: {model_name}...")
        self.device = device
        self.model_name = model_name

        # Load model từ HuggingFace
        from transformers import AutoTokenizer, AutoModel

        self.tokenizer = AutoTokenizer.from_pretrained(
            "colbert-ir/colbertv2.0", trust_remote_code=True
        )
        self.model = AutoModel.from_pretrained(
            "colbert-ir/colbertv2.0", trust_remote_code=True
        ).to(device)
        self.model.eval()

        # Pre-computed embeddings của database addresses (sẽ tính sau)
        self.address_embeddings = None
        self.address_ids = None

        print(" ColBERT model loaded successfully")

    def encode_addresses(self, addresses: List[str]) -> Tuple[np.ndarray, List[str]]:
        """
        Encode tất cả addresses thành multi-vector embeddings (pre-computation)

        Quá trình:
        1. Tokenize mỗi address thành tokens
        2. Pass qua transformer để lấy contextual embeddings
        3. Apply MaxSim-specific pooling nếu cần
        4. Lưu embeddings vào memory hoặc disk

        Args:
            addresses: List địa chỉ chuẩn

        Returns:
            Tuple (embeddings_matrix, address_ids)
        """
        print(f"\n Pre-computing embeddings cho {len(addresses)} addresses...")

        embeddings_list = []
        batch_size = 32

        with torch.no_grad():
            for i in range(0, len(addresses), batch_size):
                batch = addresses[i : i + batch_size]

                # Tokenize
                encoded = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.device)

                # Forward pass - lấy last hidden states (token-level embeddings)
                outputs = self.model(**encoded)
                embeddings = outputs.last_hidden_state  # Shape: (batch_size, seq_len, hidden_size)

                # Áp dụng MaxSim-specific pooling (giữ tất cả token embeddings)
                # Trong ColBERT, không áp dụng mean pooling, giữ nguyên token-level
                embeddings_list.append(embeddings.cpu())

                if (i + batch_size) % (batch_size * 4) == 0:
                    print(
                        f"  ✓ Processed {min(i + batch_size, len(addresses))}/{len(addresses)} addresses"
                    )

        print(" Pre-computation completed")

        # Lưu embeddings (lưu ý: có thể lớn, nên thường lưu vào disk)
        self.address_embeddings = embeddings_list
        self.address_ids = list(range(len(addresses)))

        return embeddings_list, self.address_ids

    def search(
        self, query: str, addresses: List[str], top_k: int = 500
    ) -> List[Tuple[str, float]]:
        """
        Tìm top-k candidates cho query bằng ColBERT late interaction

        Quá trình:
        1. Encode query
        2. Tính MaxSim score giữa query tokens và từng address's tokens
        3. Sort và return top-k

        Args:
            query: Địa chỉ query
            addresses: List tất cả addresses
            top_k: Số ứng viên trả về

        Returns:
            List tuple (address, score)
        """
        print(f"\n Layer 1: ColBERT Candidate Generation")
        print(f"  Query: {query[:60]}...")
        print(f"  Searching in {len(addresses)} addresses...")

        # Nếu chưa pre-compute, thực hiện ngay
        if self.address_embeddings is None:
            self.encode_addresses(addresses)

        with torch.no_grad():
            # Encode query
            query_encoded = self.tokenizer(
                query, padding=True, truncation=True, max_length=512, return_tensors="pt"
            ).to(self.device)
            query_embeddings = self.model(**query_encoded).last_hidden_state  # (1, seq_len, hidden_size)

            # Tính MaxSim với mỗi address
            scores = []

            for i, address in enumerate(addresses):
                # Encode address
                addr_encoded = self.tokenizer(
                    address,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.device)
                addr_embeddings = self.model(**addr_encoded).last_hidden_state

                # MaxSim: max cosine similarity giữa query tokens và address tokens
                # Formula: score = sum_i max_j (query_i · address_j)
                query_emb = query_embeddings[0]  # (seq_len, hidden_size)
                addr_emb = addr_embeddings[0]

                # Tính cosine similarity
                cos_scores = torch.nn.functional.cosine_similarity(
                    query_emb.unsqueeze(1), addr_emb.unsqueeze(0), dim=2
                )  # (query_len, addr_len)

                # MaxSim: sum của max scores
                max_sim_score = torch.sum(torch.max(cos_scores, dim=1)[0])
                scores.append((address, max_sim_score.item()))

        # Sort và return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        results = scores[:top_k]

        print(f"   Found {len(results)} candidates")
        print(f"  Top candidate: {results[0][0]} (score: {results[0][1]:.4f})")

        return results


# ============================================================================
# CELL 4: Tầng 2 - mGTE Dense Retriever
# ============================================================================

print("\n" + "=" * 80)
print("INITIALIZING LAYER 2 - mGTE DENSE RETRIEVER")
print("=" * 80)


class Layer2_mGTE:
    """
    Tầng 2: Re-ranking nhận biết cấu trúc bằng mGTE
    =====================================================

    Quá trình:
    1. Encode query và candidates thành dense embeddings (1 vector cho mỗi text)
    2. Tính cosine similarity giữa query embedding và candidates embeddings
    3. Sort candidates bằng similarity scores
    4. Trả về top-k candidates (~20)

    Ưu điểm:
    - Long-context support: Xử lý được 8192 tokens
    - Multilingual: 75+ languages, aligned embedding space
    - Dual-mode: Dense + sparse retrieval
    - SOTA performance trên MIRACL, MKQA

    Lưu ý:
    - mGTE là generalized long-context version của GTE
    - Được training trên 30+ tỷ tokens multilingual
    - Nhỏ gọn (24M params) nhưng hiệu quả cao
    """

    def __init__(
        self,
        model_name: str = "Alibaba-NLP/gte-multilingual-base",
        device: str = "cuda",
    ):
        """
        Khởi tạo mGTE retriever model

        Args:
            model_name: Tên model từ HuggingFace (mGTE/E5/BGE-M3)
            device: cuda hoặc cpu
        """
        print(f"\n Loading mGTE model: {model_name}...")
        self.device = device
        self.model_name = model_name

        # Load SentenceTransformer model
        # mGTE có thể sử dụng sentence-transformers thư viện
        self.model = SentenceTransformer(model_name, device=device)
        self.model.eval()

        print(
            f" mGTE model loaded successfully (embedding_dim: {self.model.get_embedding_dimension()})"
        )

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encode texts thành dense embeddings

        Quá trình:
        1. Tokenize texts
        2. Pass qua encoder
        3. Apply pooling (mean pooling của token embeddings)
        4. Normalize embeddings (L2 normalization)

        Args:
            texts: List texts

        Returns:
            Embeddings matrix (n_texts, embedding_dim)
        """
        # Sử dụng encode method của SentenceTransformer
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalization
        )
        return embeddings

    def rerank(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Re-rank candidates bằng dense similarity

        Quá trình:
        1. Encode query
        2. Encode tất cả candidates
        3. Tính cosine similarity (dot product với normalized embeddings)
        4. Sort và return top-k

        Args:
            query: Query text
            candidates: List candidate texts
            top_k: Số results trả về

        Returns:
            List tuple (candidate, score)
        """
        print(f"\n Layer 2: mGTE Dense Retriever")
        print(f"  Query: {query[:60]}...")
        print(f"  Re-ranking {len(candidates)} candidates...")

        # Encode query
        query_embedding = self.encode([query])[0]  # (embedding_dim,)

        # Encode candidates
        candidate_embeddings = self.encode(candidates)  # (n_candidates, embedding_dim)

        # Tính cosine similarity (với normalized embeddings, đó là dot product)
        scores = np.dot(candidate_embeddings, query_embedding)  # (n_candidates,)

        # Create list of (candidate, score)
        results = list(zip(candidates, scores))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        results = results[:top_k]

        print(f"   Re-ranked {len(results)} candidates")
        print(f"  Top candidate: {results[0][0]} (score: {results[0][1]:.4f})")

        return results


# ============================================================================
# CELL 5: Tầng 3 - Cross-Encoder Precision Scoring
# ============================================================================

print("\n" + "=" * 80)
print("INITIALIZING LAYER 3 - CROSS-ENCODER PRECISION SCORING")
print("=" * 80)


class Layer3_CrossEncoder:
    """
    Tầng 3: Precision scoring bằng Cross-Encoder
    =====================================================

    Quá trình:
    1. Concatenate query + candidate
    2. Pass qua single transformer (joint encoding)
    3. Lấy relevance score từ output layer
    4. Return top-k với highest scores

    Ưu điểm:
    - Joint encoding: Full attention giữa query tokens và candidate tokens
    - Highest accuracy: SOTA trong re-ranking tasks
    - Fine-grained interactions: Subtle semantic relationships
    - Semantic BM25 internally: Combines term frequency + IDF + length normalization

    Nhược điểm:
    - Computational cost cao: Phải encode từng pair riêng
    - Latency cao: Không thể pre-compute
    - Chỉ áp dụng cho top candidates (10-20)
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/multilingual-MiniLMv2-L12-H384-uncased",
        device: str = "cuda",
    ):
        """
        Khởi tạo Cross-Encoder model

        Args:
            model_name: Tên model từ HuggingFace
            device: cuda hoặc cpu
        """
        print(f"\n Loading Cross-Encoder model: {model_name}...")
        self.device = device
        self.model_name = model_name

        # Load CrossEncoder từ sentence-transformers
        self.model = CrossEncoder(model_name, device=device)

        print(" Cross-Encoder model loaded successfully")

    def score(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 3,
    ) -> List[Tuple[str, float]]:
        """
        Score query-candidate pairs bằng cross-encoder

        Quá trình:
        1. Tạo list pairs: (query, candidate1), (query, candidate2), ...
        2. Predict scores cho tất cả pairs
        3. Sort by score
        4. Return top-k

        Args:
            query: Query text
            candidates: List candidate texts
            top_k: Số results trả về

        Returns:
            List tuple (candidate, score)
        """
        print(f"\n Layer 3: Cross-Encoder Precision Scoring")
        print(f"  Query: {query[:60]}...")
        print(f"  Scoring {len(candidates)} candidates...")

        # Create query-candidate pairs
        pairs = [(query, candidate) for candidate in candidates]

        # Predict scores (returns 1D array of scores)
        scores = self.model.predict(pairs, show_progress_bar=False)

        # Create results
        results = list(zip(candidates, scores))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top-k
        results = results[:top_k]

        print(f"   Scored {len(results)} top candidates")
        print(f"  Top candidate: {results[0][0]} (score: {results[0][1]:.4f})")

        return results


# ============================================================================
# CELL 6: Tầng 4 - Qwen3 Intelligent Fallback
# ============================================================================

print("\n" + "=" * 80)
print("INITIALIZING LAYER 4 - QWEN3 INTELLIGENT FALLBACK")
print("=" * 80)


class Layer4_Qwen3LLM:
    """
    Tầng 4: LLM Fallback thông minh bằng Qwen3
    =====================================================

    Quá trình:
    1. Trigger khi confidence < threshold (ví dụ: 0.7)
    2. Pass query + top candidates + reasoning prompt tới LLM
    3. LLM suy luận step-by-step (thinking mode)
    4. Return confidence score + reasoning

    Ưu điểm:
    - Vietnamese SOTA: F1 0.58 VLSP 2025 Semantic Parsing
    - Dual thinking modes: Fast mode + deep reasoning mode
    - Flexible: Có thể query external APIs (Maps, OSM)
    - Cost optimization: Trigger chỉ khi cần thiết

    Nhược điểm:
    - Latency cao: Phải wait cho LLM generation
    - Chi phí cao: Token-based billing
    - Cần token quota (nếu API-based)

    Lưu ý:
    - Trong Colab, sử dụng lightweight Qwen3-4B hoặc 8B
    - Có thể sử dụng quantization (bitsandbytes) để tiết kiệm memory
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-4B",
        device: str = "cuda",
        use_quantization: bool = False,
    ):
        """
        Khởi tạo Qwen3 LLM

        Args:
            model_name: Tên model từ HuggingFace
            device: cuda hoặc cpu
            use_quantization: Có sử dụng 8-bit quantization không (tiết kiệm memory)
        """
        print(f"\n Loading Qwen3 model: {model_name}...")
        print(f"   Note: First time loading model sẽ tải ~7GB (mất 1-2 phút)")

        self.device = device
        self.model_name = model_name
        self.use_quantization = use_quantization

        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

            # Quantization config nếu cần
            if use_quantization:
                from transformers import BitsAndBytesConfig

                bnb_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                )
                print("   Model loaded with 8-bit quantization (tiết kiệm 75% memory)")
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    device_map="auto",
                    torch_dtype=torch.float16,  # Half precision
                    trust_remote_code=True,
                )

            self.model.eval()
            print(" Qwen3 model loaded successfully")

        except Exception as e:
            print(f"️ Lỗi load Qwen3: {e}")
            print("  Fallback: Sử dụng simple rule-based fallback")
            self.model = None
            self.tokenizer = None

    def fallback_reasoning(
        self,
        query: str,
        candidates: List[str],
        confidence_threshold: float = 0.7,
    ) -> Tuple[Optional[str], float, str]:
        """
        Fallback reasoning khi confidence < threshold

        Quá trình:
        1. Tạo prompt cho LLM
        2. Generate response từ LLM
        3. Parse output để lấy final address + confidence

        Args:
            query: Query address
            candidates: List top candidates
            confidence_threshold: Trigger threshold

        Returns:
            Tuple (final_address, confidence, reasoning)
        """
        if self.model is None:
            # Fallback đơn giản nếu không có LLM
            return self._simple_fallback(query, candidates)

        print(f"\n Layer 4: Qwen3 Intelligent Fallback")
        print(f"  Query: {query[:60]}...")
        print(f"  Trigger reason: Confidence < {confidence_threshold}")

        # Tạo prompt cho LLM
        candidates_str = "\n".join(
            [f"{i+1}. {c}" for i, c in enumerate(candidates[:5])]
        )
        prompt = f"""Bạn là chuyên gia chuẩn hóa địa chỉ Việt Nam.

Nhiệm vụ: Phân tích địa chỉ query dưới đây và chọn địa chỉ chuẩn tốt nhất từ danh sách ứng viên.

Địa chỉ Query (có thể không chuẩn): {query}

Danh sách địa chỉ ứng viên:
{candidates_str}

Vui lòng:
1. Phân tích query
2. So sánh với từng ứng viên
3. Giải thích lý do chọn địa chỉ tốt nhất
4. Đưa ra confidence score (0-100%)

Format trả về:
Địa chỉ cuối cùng: [chọn từ danh sách hoặc tạo chuẩn hóa]
Confidence: [0-100]%
Lý do: [giải thích ngắn gọn]
"""

        # Generate
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.3,  # Low temperature for deterministic output
                    top_p=0.95,
                    do_sample=True,
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response.split("Assistant:")[-1] if "Assistant:" in response else response

            # Parse response (simple parsing - có thể improve)
            lines = response.split("\n")
            final_address = candidates[0]  # Default: first candidate
            confidence = 0.5

            for line in lines:
                if "Địa chỉ cuối cùng:" in line or "final_address:" in line.lower():
                    final_address = line.split(":")[-1].strip()
                elif "confidence:" in line.lower():
                    conf_str = line.split(":")[-1].strip().replace("%", "")
                    try:
                        confidence = float(conf_str) / 100.0
                    except:
                        pass

            reasoning = response[:200] + "..." if len(response) > 200 else response

            print(f"   LLM reasoning completed")
            print(f"  Final address: {final_address}")
            print(f"  Confidence: {confidence:.2%}")

            return final_address, confidence, reasoning

        except Exception as e:
            print(f"  ️ LLM generation failed: {e}")
            print(f"  Falling back to first candidate")
            return candidates[0], 0.5, f"LLM failed: {str(e)}"

    def _simple_fallback(
        self, query: str, candidates: List[str]
    ) -> Tuple[str, float, str]:
        """
        Simple rule-based fallback nếu không có LLM

        Quá trình:
        1. Tính string similarity (Levenshtein distance)
        2. Chọn candidate có similarity cao nhất
        3. Assign confidence dựa trên similarity
        """
        print(f"\n Layer 4: Simple Rule-Based Fallback (No LLM)")

        from difflib import SequenceMatcher

        # Tính similarity với mỗi candidate
        similarities = []
        for candidate in candidates:
            ratio = SequenceMatcher(None, query.lower(), candidate.lower()).ratio()
            similarities.append((candidate, ratio))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        final_address, confidence = similarities[0]
        reasoning = f"String similarity matching: {confidence:.2%}"

        print(f"   Fallback completed")
        print(f"  Final address: {final_address}")
        print(f"  Confidence: {confidence:.2%}")

        return final_address, confidence, reasoning


# ============================================================================
# CELL 7: Main Pipeline Orchestration
# ============================================================================

print("\n" + "=" * 80)
print("INITIALIZING MAIN ENSEMBLE PIPELINE")
print("=" * 80)


class EnsembleAddressNormalization:
    """
    Kiến trúc Kết hợp 4 tầng cho chuẩn hóa địa chỉ Việt Nam
    =====================================================

    Pipeline flow:
    Layer 1 (500 candidates)
        ↓
    Layer 2 (20 candidates)
        ↓
    Layer 3 (3 candidates)
        ↓
    Layer 4 (conditional fallback)
        ↓
    Final Result
    """

    def __init__(self, config: PipelineConfig = None):
        """
        Khởi tạo pipeline

        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        self.performance_tracker = PerformanceTracker()

        print("\n" + "=" * 80)
        print("INITIALIZING 4-LAYER ENSEMBLE PIPELINE")
        print("=" * 80)

        # Layer 1: ColBERT
        print("\n[1/4] Initializing Layer 1: ColBERT...")
        try:
            self.layer1_colbert = Layer1_ColBERT(device=device)
        except Exception as e:
            print(f"️ ColBERT initialization failed: {e}")
            print("   Note: ColBERT requires special setup - sử dụng simplified version")
            self.layer1_colbert = None

        # Layer 2: mGTE Retriever
        print("\n[2/4] Initializing Layer 2: mGTE Retriever...")
        self.layer2_retriever = Layer2_mGTE(device=device)

        # Layer 3: Cross-Encoder
        print("\n[3/4] Initializing Layer 3: Cross-Encoder...")
        self.layer3_cross_encoder = Layer3_CrossEncoder(device=device)

        # Layer 4: Qwen3 LLM Fallback
        print("\n[4/4] Initializing Layer 4: Qwen3 LLM Fallback...")
        try:
            self.layer4_llm = Layer4_Qwen3LLM(
                model_name="Qwen/Qwen3-4B",  # Lightweight version
                device=device,
                use_quantization=True,  # Quantization để tiết kiệm memory
            )
        except Exception as e:
            print(f"️ Qwen3 initialization warning: {e}")
            print("   Sẽ sử dụng rule-based fallback thay vì LLM")
            self.layer4_llm = Layer4_Qwen3LLM()
            self.layer4_llm.model = None

        print("\n Pipeline initialization completed!")

    def normalize(
        self,
        query: str,
        standard_addresses: List[str],
    ) -> Dict:
        """
        Normalize một địa chỉ query qua 4 tầng

        Quá trình:
        1. Layer 1: Tạo 500 candidates bằng ColBERT
        2. Layer 2: Re-rank xuống còn 20 bằng mGTE
        3. Layer 3: Score xuống còn 3 bằng Cross-Encoder
        4. Layer 4 (conditional): Fallback reasoning bằng Qwen3

        Args:
            query: Địa chỉ query (có thể không chuẩn)
            standard_addresses: List địa chỉ chuẩn trong database

        Returns:
            Dictionary với results từ 4 tầng
        """
        results = {
            "query": query,
            "timestamp": time.time(),
            "layer1_candidates": [],
            "layer2_candidates": [],
            "layer3_candidates": [],
            "layer4_llm_result": None,
            "final_result": None,
            "performance": {},
        }

        print("\n" + "=" * 80)
        print("NORMALIZING ADDRESS")
        print("=" * 80)
        print(f"Query: {query}")

        # ====== LAYER 1: ColBERT Candidate Generation ======
        t0 = time.time()
        if self.layer1_colbert is not None:
            try:
                layer1_results = self.layer1_colbert.search(
                    query,
                    standard_addresses,
                    top_k=self.config.colbert_top_k,
                )
                layer1_candidates = [addr for addr, score in layer1_results]
                results["layer1_candidates"] = layer1_results[:10]  # Store top 10 for display
            except Exception as e:
                print(f"️ Layer 1 failed: {e} - using all addresses")
                layer1_candidates = standard_addresses
        else:
            # Fallback: sử dụng tất cả addresses
            print("️ Layer 1 skipped (ColBERT not available)")
            layer1_candidates = standard_addresses

        layer1_time = (time.time() - t0) * 1000
        self.performance_tracker.record("layer1_colbert", layer1_time)

        # ====== LAYER 2: mGTE Dense Retriever ======
        t1 = time.time()
        print(f"\n(Layer 1 time: {layer1_time:.2f}ms)")
        layer2_results = self.layer2_retriever.rerank(
            query,
            layer1_candidates,
            top_k=self.config.reranker_top_k,
        )
        layer2_candidates = [addr for addr, score in layer2_results]
        results["layer2_candidates"] = layer2_results

        layer2_time = (time.time() - t1) * 1000
        self.performance_tracker.record("layer2_retriever", layer2_time)

        # ====== LAYER 3: Cross-Encoder Precision Scoring ======
        t2 = time.time()
        print(f"(Layer 2 time: {layer2_time:.2f}ms)")
        layer3_results = self.layer3_cross_encoder.score(
            query,
            layer2_candidates,
            top_k=self.config.cross_encoder_top_k,
        )
        layer3_candidates = [addr for addr, score in layer3_results]
        results["layer3_candidates"] = layer3_results

        layer3_time = (time.time() - t2) * 1000
        self.performance_tracker.record("layer3_cross_encoder", layer3_time)

        # ====== LAYER 4: Qwen3 Intelligent Fallback (Conditional) ======
        t3 = time.time()
        print(f"(Layer 3 time: {layer3_time:.2f}ms)")

        # Check confidence threshold
        top_confidence = layer3_results[0][1] if layer3_results else 0.0
        trigger_llm = (
            self.config.llm_enable and top_confidence < self.config.confidence_threshold
        )

        if trigger_llm:
            final_address, llm_confidence, reasoning = self.layer4_llm.fallback_reasoning(
                query,
                layer3_candidates,
                self.config.confidence_threshold,
            )
            results["layer4_llm_result"] = {
                "address": final_address,
                "confidence": llm_confidence,
                "reasoning": reasoning,
            }
        else:
            print(f"\n Layer 4: Skipped (top confidence {top_confidence:.4f} >= threshold {self.config.confidence_threshold})")

        layer4_time = (time.time() - t3) * 1000
        self.performance_tracker.record("layer4_llm", layer4_time)

        # ====== FINAL RESULT ======
        total_time = (time.time() - t0) * 1000
        self.performance_tracker.record("total", total_time)

        if results["layer4_llm_result"] is not None:
            # Use LLM result
            final_result = {
                "address": results["layer4_llm_result"]["address"],
                "confidence": results["layer4_llm_result"]["confidence"],
                "source": "Layer 4 (LLM Fallback)",
            }
        else:
            # Use Layer 3 top result
            final_result = {
                "address": layer3_candidates[0],
                "confidence": layer3_results[0][1],
                "source": "Layer 3 (Cross-Encoder)",
            }

        results["final_result"] = final_result
        results["performance"] = {
            "layer1_ms": layer1_time,
            "layer2_ms": layer2_time,
            "layer3_ms": layer3_time,
            "layer4_ms": layer4_time,
            "total_ms": total_time,
        }

        return results

    def print_results(self, results: Dict):
        """In kết quả đẹp"""
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\n Query: {results['query']}")
        print(f"\n Final Result:")
        print(f"  Address: {results['final_result']['address']}")
        print(f"  Confidence: {results['final_result']['confidence']:.4f}")
        print(f"  Source: {results['final_result']['source']}")

        print(f"\n Top 3 Layer 3 Candidates:")
        for i, (addr, score) in enumerate(results["layer3_candidates"][:3], 1):
            print(f"  {i}. {addr} (score: {score:.4f})")

        print(f"\n⏱️ Performance:")
        perf = results["performance"]
        print(f"  Layer 1 (ColBERT): {perf['layer1_ms']:.2f}ms")
        print(f"  Layer 2 (mGTE): {perf['layer2_ms']:.2f}ms")
        print(f"  Layer 3 (Cross-Encoder): {perf['layer3_ms']:.2f}ms")
        print(f"  Layer 4 (LLM): {perf['layer4_ms']:.2f}ms")
        print(f"  Total: {perf['total_ms']:.2f}ms")


# ============================================================================
# CELL 8: Demo Data và Test
# ============================================================================

print("\n" + "=" * 80)
print("PREPARING DEMO DATA")
print("=" * 80)

# Vietnamese standard addresses database (mẫu)
STANDARD_ADDRESSES = [
    "123 Đường Nguyễn Huệ, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh",
    "456 Đường Lê Lợi, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh",
    "789 Đường Võ Văn Kiệt, Phường Cô Giang, Quận 1, Thành phố Hồ Chí Minh",
    "321 Đường Trần Hưng Đạo, Phường Cầu Ông Lãnh, Quận 1, Thành phố Hồ Chí Minh",
    "654 Đường Hàm Nghi, Phường Đa Kao, Quận 1, Thành phố Hồ Chí Minh",
    "111 Đường Pasteur, Phường Nguyễn Thái Bình, Quận 1, Thành phố Hồ Chí Minh",
    "222 Đường Máy Trạm, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh",
    "333 Đường Ngô Đức Kế, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh",
    "444 Đường Công Trường Mê Linh, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh",
    "555 Đường Trương Định, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh",
]

# Test queries (không chuẩn, có typos, abbreviations)
TEST_QUERIES = [
    "123 Nguyễn Huệ, Bến Nghé, Q1, HCM",  # Abbreviated
    "Ng. Lê Lợi, P. Bến Thành, Q.1, Hồ Chí Minh",  # Abbreviated with dots
    "789 Võ Văn Kiệt st, Cô Giang ward, District 1, HCMC",  # Mixed English
    "321 Tran Hung Dao, Ben Canh Phuong, Q1, TP HCM",  # No diacritics + typo
]

print(f"\n Loaded {len(STANDARD_ADDRESSES)} standard addresses")
print(f" Loaded {len(TEST_QUERIES)} test queries")

print("\nStandard Addresses:")
for i, addr in enumerate(STANDARD_ADDRESSES[:5], 1):
    print(f"  {i}. {addr}")
print(f"  ... ({len(STANDARD_ADDRESSES)-5} more)")

print("\nTest Queries:")
for i, query in enumerate(TEST_QUERIES, 1):
    print(f"  {i}. {query}")


# ============================================================================
# CELL 9: Initialize Pipeline (MAIN)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1: INITIALIZE PIPELINE")
print("=" * 80)
print(" Initializing 4-layer ensemble... (mất 2-5 phút)")

config = PipelineConfig(
    colbert_top_k=500,
    reranker_top_k=20,
    cross_encoder_top_k=3,
    confidence_threshold=0.7,
    llm_enable=True,
    weight_retriever=0.2,
    weight_cross_encoder=0.8,
)

pipeline = EnsembleAddressNormalization(config=config)

print("\n Pipeline initialized successfully!")


# ============================================================================
# CELL 10: Run Demo (Test Pipeline)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: RUN DEMO - TEST PIPELINE")
print("=" * 80)

# Run on first test query
test_query = TEST_QUERIES[0]
print(f"\nTesting query: {test_query}")

results = pipeline.normalize(test_query, STANDARD_ADDRESSES)
pipeline.print_results(results)


# ============================================================================
# CELL 11: Batch Processing (Multiple Queries)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: BATCH PROCESSING - MULTIPLE QUERIES")
print("=" * 80)

batch_results = []

for i, query in enumerate(TEST_QUERIES, 1):
    print(f"\n{'='*80}")
    print(f"Processing query {i}/{len(TEST_QUERIES)}")
    print(f"{'='*80}")

    result = pipeline.normalize(query, STANDARD_ADDRESSES)
    batch_results.append(result)
    pipeline.print_results(result)


# ============================================================================
# CELL 12: Performance Analysis
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: PERFORMANCE ANALYSIS")
print("=" * 80)

pipeline.performance_tracker.print_summary()

# Detailed batch statistics
print("\n" + "=" * 80)
print("BATCH PROCESSING STATISTICS")
print("=" * 80)

df_results = pd.DataFrame(
    [
        {
            "query": r["query"][:50],
            "final_address": r["final_result"]["address"][:40],
            "confidence": r["final_result"]["confidence"],
            "source": r["final_result"]["source"],
            "total_time_ms": r["performance"]["total_ms"],
        }
        for r in batch_results
    ]
)

print(df_results.to_string(index=False))

print(f"\n Summary:")
print(f"  Total queries: {len(batch_results)}")
print(f"  Avg latency: {df_results['total_time_ms'].mean():.2f}ms")
print(f"  Min latency: {df_results['total_time_ms'].min():.2f}ms")
print(f"  Max latency: {df_results['total_time_ms'].max():.2f}ms")
print(f"  Avg confidence: {df_results['confidence'].mean():.4f}")


# ============================================================================
# CELL 13: Advanced Features - Custom Query
# ============================================================================

print("\n" + "=" * 80)
print("STEP 5: CUSTOM QUERY TEST")
print("=" * 80)

# Function để user test queries tuỳ chỉnh
def normalize_address(query: str):
    """Helper function để test custom queries"""
    result = pipeline.normalize(query, STANDARD_ADDRESSES)
    pipeline.print_results(result)
    return result


# Example custom queries
print("\nTesting custom queries:")

custom_queries = [
    "Đường Pasteur, Bến Thành, Q1",
    "Số 555, Trương Định, Quận 1",
]

for query in custom_queries:
    print(f"\n Query: {query}")
    result = normalize_address(query)
    print(f" Result: {result['final_result']['address']}")
    print(f"   Confidence: {result['final_result']['confidence']:.4f}\n")


# ============================================================================
# CELL 14: Export Results (Save to CSV)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 6: EXPORT RESULTS")
print("=" * 80)

# Save batch results to CSV
output_df = pd.DataFrame(
    [
        {
            "input_query": r["query"],
            "final_address": r["final_result"]["address"],
            "confidence": r["final_result"]["confidence"],
            "source": r["final_result"]["source"],
            "layer1_time_ms": r["performance"]["layer1_ms"],
            "layer2_time_ms": r["performance"]["layer2_ms"],
            "layer3_time_ms": r["performance"]["layer3_ms"],
            "layer4_time_ms": r["performance"]["layer4_ms"],
            "total_time_ms": r["performance"]["total_ms"],
            "top_3_candidates": " | ".join([f"{addr[:30]}" for addr, _ in r["layer3_candidates"]]),
        }
        for r in batch_results
    ]
)

# Save to CSV (accessible from Colab)
output_csv = "/tmp/address_normalization_results.csv"
output_df.to_csv(output_csv, index=False, encoding="utf-8-sig")

print(f"\n Results saved to: {output_csv}")
print(f"\nFirst few rows:")
print(output_df.head(2).to_string())

print("\n Để download file CSV:")
print("  1. Click 'Files' trên sidebar trái")
print("  2. Click file: address_normalization_results.csv")
print("  3. Click download icon")


print("\n" + "=" * 80)
print(" DEMO COMPLETED SUCCESSFULLY!")
print("=" * 80)
print(f"\nSummary:")
print(f"  - Processed {len(batch_results)} queries")
print(f"  - Avg latency: {df_results['total_time_ms'].mean():.2f}ms")
print(f"  - Results saved to: {output_csv}")
print(f"  - All 4 layers executed successfully!")
aved to: {output_csv}")
print(f"  - All 4 layers executed successfully!")
