"""
services/synthetic_mixer.py
==========================
Engine sinh dữ liệu NER tổng hợp từ dữ liệu OSM.

Ví dụ thực thi mẫu:
------------------
from app.services.synthetic_mixer import SyntheticMixerPro
mixer = SyntheticMixerPro()
mixer.generate_batch(10)
"""
import random
import logging
import re
from sqlalchemy import text as sql_text
from app.core.database import SessionLocal, TrainingDataset, OSMStreet, OSMBuilding, OSMPoi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SyntheticMixer")

class SyntheticMixerPro:
    """
    Engine sinh dữ liệu NER siêu chất lượng.
    Tối ưu cho quy mô 100.000+ dòng dữ liệu OSM.
    """
    def __init__(self):
        self.session = SessionLocal()
        self.noise_prefixes = [
            "Đối diện", "Cạnh", "Kế bên", "Gần", "Nằm gần", "Phía sau", 
            "Cổng phụ", "Lối vào", "Gần chung cư", "Ngay sát"
        ]
        self.nbh_types = ["Khu phố", "Thôn", "Ấp", "Xóm", "Tổ", "Khu công nghiệp", "Cụm CN"]
        self.floor_units = ["Tầng", "Lầu", "Phòng", "Căn hộ", "P.", "A", "B", "C"]

    def _get_random_entities(self, table_name, limit=100):
        """Lấy mẫu ngẫu nhiên từ Database hiệu quả."""
        query = f"SELECT name FROM {table_name} ORDER BY random() LIMIT {limit}"
        res = self.session.execute(sql_text(query))
        return [r[0] for r in res]

    def _apply_typos(self, text):
        """Mô phỏng lỗi gõ phím và viết tắt ngẫu nhiên."""
        if random.random() > 0.8: # 20% khả năng có lỗi
            # Viết thường toàn bộ
            return text.lower()
        if random.random() > 0.9:
            # Bỏ dấu ngẫu nhiên (chỉ mô phỏng một phần)
            return text.replace("đ", "d").replace("ê", "e")
        return text

    def generate_complex_sample(self, streets, buildings, pois):
        """Sinh mẫu địa chỉ đa tầng phức tạp."""
        tokens = []
        tags = []
        
        # Chọn Template ngẫu nhiên
        scenario = random.randint(1, 5)
        
        if scenario == 1: # Tòa nhà + Phòng + Đường
            bld = random.choice(buildings)
            self._add_tokens(bld, "BLD", tokens, tags)
            
            floor = f"{random.choice(self.floor_units)} {random.randint(1, 30)}"
            self._add_tokens(floor, "NUM", tokens, tags)
            
            street = random.choice(streets)
            self._add_tokens(street, "STR", tokens, tags)

        elif scenario == 2: # POI + Hướng dẫn + Đường
            poi = random.choice(pois)
            self._add_tokens(poi, "POI", tokens, tags)
            
            noise = random.choice(self.noise_prefixes)
            self._add_tokens(noise, "O", tokens, tags)
            
            street = random.choice(streets)
            self._add_tokens(street, "STR", tokens, tags)

        elif scenario == 3: # Số nhà + Ngõ + Hẻm + Đường
            num = f"{random.randint(1, 999)}"
            self._add_tokens(num, "NUM", tokens, tags)
            
            aly = f"Ngõ {random.randint(1, 500)}"
            self._add_tokens(aly, "ALY", tokens, tags)
            
            hem = f"Hẻm {random.randint(1, 100)}"
            self._add_tokens(hem, "ALY", tokens, tags)
            
            street = random.choice(streets)
            self._add_tokens(street, "STR", tokens, tags)

        elif scenario == 4: # Khu công nghiệp / Khu phố (NBH)
            nbh = f"{random.choice(self.nbh_types)} {random.choice(streets)}"
            self._add_tokens(nbh, "NBH", tokens, tags)
            
            self._add_tokens("Đường số", "O", tokens, tags)
            self._add_tokens(str(random.randint(1, 100)), "STR", tokens, tags)

        else: # Địa chỉ cực ngắn (Nhiễu cao)
            self._add_tokens(random.choice(streets), "STR", tokens, tags)
            self._add_tokens(str(random.randint(1, 100)), "NUM", tokens, tags)

        # Trộn ngẫu nhiên viết hoa/thường
        final_text = " ".join(tokens)
        if random.random() > 0.5:
            final_text = self._apply_typos(final_text)
            
        return final_text, {"tokens": tokens, "tags": tags}

    def _add_tokens(self, text, label, tokens_list, tags_list):
        words = text.split()
        for i, word in enumerate(words):
            tokens_list.append(word)
            if label == "O":
                tags_list.append("O")
            else:
                prefix = "B-" if i == 0 else "I-"
                tags_list.append(f"{prefix}{label}")

    def generate_batch(self, count=5000):
        logger.info(f"🧪 [PRO MIXER] Đang chuẩn bị sinh {count} mẫu siêu chất lượng...")
        
        # Lấy thực thể từ DB
        streets = self._get_random_entities("osm.streets", 500)
        buildings = self._get_random_entities("osm.buildings", 200)
        pois = self._get_random_entities("osm.pois", 200)
        
        samples = []
        for _ in range(count):
            raw_text, ner_data = self.generate_complex_sample(streets, buildings, pois)
            # Kiểm tra tính hợp lệ (Số lượng tokens phải bằng tags)
            if len(ner_data["tokens"]) == len(ner_data["tags"]):
                samples.append(TrainingDataset(
                    raw_text=raw_text,
                    ner_tags_json=ner_data,
                    is_synthetic=True,
                    noise_level=random.choice(["low", "medium", "high"])
                ))
        
        self.session.bulk_save_objects(samples)
        self.session.commit()
        logger.info(f"✅ Đã nạp {len(samples)} mẫu huấn luyện Pro vào DB.")

if __name__ == "__main__":
    mixer = SyntheticMixerPro()
    mixer.generate_batch(100)
