"""
test_vnaddress.py
=================
Đánh giá hiệu quả của thư viện vnaddress trên dữ liệu địa chỉ Việt Nam.
"""

from vnaddress import VNAddressStandardizer
import time

test_cases = [
    "Dicjh Vongj Haaju",
    "60 Võ Nguyên Giáp, Mân Thái, Sơn Trà, Đà Nẵng",
    "76 Đ. Phan Khiêm Ích, Phường Tân Phong, Quận 7, TP.HCM",
    "Số 10, Ngõ 123, P. Dịch Vọng, Q. Cầu Giấy, HN",
    "123 Lê Lợi Phường 1 Quận 1",
]

def run_test():
    print(f"{'Original':<60} | {'Standardized':<60}")
    print("-" * 125)
    
    for addr in test_cases:
        try:
            start_time = time.time()
            # Khởi tạo bộ chuẩn hóa với detail=True
            standardizer = VNAddressStandardizer(raw_address=addr, comma_handle=True, detail=True)
            res_dict = standardizer.execute()
            result = res_dict.get('result', 'N/A')
            
            # Kiểm tra xem có giữ được street address không
            detail = res_dict.get('detail', {})
            latency = (time.time() - start_time) * 1000
            
            print(f"{addr:<60} | {result:<60} ({latency:.2f}ms)")
            print(f"  > Detail: {detail}")
        except Exception as e:
            print(f"{addr:<60} | Error: {e}")

if __name__ == "__main__":
    run_test()
