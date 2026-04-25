"""
test_caohainam_model.py
=======================
Đánh giá mô hình Deep Learning của Cao Hai Nam cho việc chuẩn hóa địa chỉ.
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import time

model_name = "caohainam/vietnamese-address-standardization"

test_cases = [
    "60 Võ Nguyên Giáp, Mân Thái, Sơn Trà, Đà Nẵng",
    "76 Đ. Phan Khiêm Ích, Phường Tân Phong, Quận 7, TP.HCM",
    "Số 10, Ngõ 123, P. Dịch Vọng, Q. Cầu Giấy, HN",
    "123 Lê Lợi Phường 1 Quận 1",
]

def run_test():
    print(f"🔄 Loading model: {model_name}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        
        print(f"{'Original':<60} | {'Standardized':<60}")
        print("-" * 125)
        
        for addr in test_cases:
            inputs = tokenizer(addr, return_tensors="pt", padding=True).to(device)
            start_time = time.time()
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=128)
            result = tokenizer.decode(outputs[0], skip_special_tokens=True)
            latency = (time.time() - start_time) * 1000
            
            print(f"{addr:<60} | {result:<60} ({latency:.2f}ms)")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_test()
