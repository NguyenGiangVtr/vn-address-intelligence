"""
test_vnaddress.py
=================
Đánh giá hiệu quả của thư viện vnaddress trên dữ liệu địa chỉ Việt Nam.
"""

import sys
import io
import os
from vnaddress import VNAddressStandardizer
import time

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    # Set console to UTF-8 encoding
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    # Set environment variable for proper UTF-8 handling
    os.environ['PYTHONIOENCODING'] = 'utf-8'

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
            
            # Capture stdout to prevent encoding issues with vnaddress print statements
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            
            try:
                # Khởi tạo bộ chuẩn hóa với detail=True
                standardizer = VNAddressStandardizer(raw_address=addr, comma_handle=True, detail=True)
                res_dict = standardizer.execute()
            finally:
                # Restore stdout
                sys.stdout = old_stdout
                captured = captured_output.getvalue()
            
            result = res_dict.get('result', 'N/A') if res_dict else 'N/A'
            
            # Kiểm tra xem có giữ được street address không
            detail = res_dict.get('detail', {}) if res_dict else {}
            latency = (time.time() - start_time) * 1000
            
            # Safe printing with encoding handling
            try:
                print(f"{addr:<60} | {result:<60} ({latency:.2f}ms)")
                if detail:
                    print(f"  > Detail: {str(detail)[:100]}...")
            except UnicodeEncodeError:
                print(f"{addr.encode('ascii', 'replace').decode():<60} | {str(result).encode('ascii', 'replace').decode():<60} ({latency:.2f}ms)")
                
        except Exception as e:
            try:
                print(f"{addr:<60} | Error: {str(e)}")
            except UnicodeEncodeError:
                print(f"{addr.encode('ascii', 'replace').decode():<60} | Error: {str(e).encode('ascii', 'replace').decode()}")

if __name__ == "__main__":
    run_test()
