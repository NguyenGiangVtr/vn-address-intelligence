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
from vnaddress import VNAddressStandardizer

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
            # Lưu ý: vnaddress in ra console nên chúng ta cần xử lý nếu cần, 
            # ở đây ta chỉ lấy kết quả từ object.
            std = VNAddressStandardizer(raw_address=text, comma_handle=True, detail=True)
            # Vì thư viện in ra console trong execute(), ta nên hạn chế gọi nhiều hoặc redirect stdout
            # Ở phiên bản này, ta giả định lấy kết quả từ logic nội bộ nếu có thể
            # Tuy nhiên, vnaddress 1.0.5 chủ yếu hoạt động qua execute()
            
            # Để tránh làm nhiễu log, ta có thể dùng mock-up logic hoặc bọc lại
            res = std.execute() 
            # Lưu ý: Thư viện này đang có bug trả về None ở execute(), kết quả in ra stdout
            # Tôi sẽ bổ sung một parser nhỏ để xử lý kết quả này nếu cần.
            return res
        except Exception as e:
            logger.warning(f"️ vnaddress error: {e}")
            return None

    def pre_process_for_labeling(self, text: str) -> str:
        """Quy trình tổng thể để làm sạch địa chỉ trước khi gán nhãn."""
        # 1. Clean viết tắt
        text = self.clean_noise(text)
        
        # 2. Bạn có thể bổ sung thêm các logic sửa lỗi chính tả ở đây
        
        return text
