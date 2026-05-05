"""
utils/address_cleaner.py
========================
Module tiền xử lý địa chỉ, tích hợp thư viện vnaddress và quy tắc tùy chỉnh.

Ví dụ thực thi mẫu:
------------------
from app.ai.utils.address_cleaner import AddressCleaner
cleaner = AddressCleaner()
print(cleaner.clean_noise("Số 102 Phan Văn Hớn, P. Tân Thới Nhất, Q. 12"))
"""

import logging
import sys
import io
import os
from vnaddress import VNAddressStandardizer

# Fix encoding issues on Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

logger = logging.getLogger(__name__)

class AddressCleaner:
    def __init__(self):
        # Khởi tạo các quy tắc bổ sung nếu cần
        self.abbreviations = {
            "TP.": "Thành phố ",
            "TP ": "Thành phố ",
            "Q.": "Quận ",
            "H.": "Huyện ",
            "P.": "Phường ",
            "X.": "Xã ",
            "TT.": "Thị trấn ",
        }

    def clean_noise(self, text: str) -> str:
        """Làm sạch các ký tự lạ và chuẩn hóa viết tắt cơ bản."""
        if not text:
            return ""
            
        cleaned = text
        for abbr, full in self.abbreviations.items():
            cleaned = cleaned.replace(abbr, full)
            
        return cleaned.strip()

    def standardize_admin_units(self, text: str) -> dict:
        """
        Sử dụng vnaddress để bóc tách và chuẩn hóa các cấp hành chính.
        Trả về dict chứa kết quả chuẩn và các cấp chi tiết.
        """
        try:
            # Capture stdout to prevent encoding issues with vnaddress print statements
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            
            try:
                std = VNAddressStandardizer(raw_address=text, comma_handle=True, detail=True)
                res = std.execute() 
            finally:
                # Restore stdout
                sys.stdout = old_stdout
                captured = captured_output.getvalue()
                
            # Log captured output if needed for debugging
            if captured.strip():
                logger.debug(f"vnaddress output: {captured[:200]}...")
                
            return res
        except UnicodeEncodeError as e:
            logger.warning(f"vnaddress Unicode encoding error: {e}")
            return None
        except Exception as e:
            logger.warning(f"vnaddress error: {e}")
            return None

    def pre_process_for_labeling(self, text: str) -> str:
        """Quy trình tổng thể để làm sạch địa chỉ trước khi gán nhãn."""
        # 1. Clean viết tắt
        text = self.clean_noise(text)
        
        # 2. Bạn có thể bổ sung thêm các logic sửa lỗi chính tả ở đây
        
        return text
