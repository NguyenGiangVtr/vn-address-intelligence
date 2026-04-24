import requests
import logging
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .database import SessionLocal, OSMStreet, OSMBuilding, OSMPoi, Province, OSMRawEntity
from .config import Config
from sqlalchemy import text as sql_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OSMFetcher")

class OSMFetcher:
    def __init__(self):
        # Danh sách các server mirror để chạy song song
        self.servers = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.osm.ch/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter"
        ]
        self.headers = {'User-Agent': 'VNAI-Bot/2.0 (contact: admin@vnai.com)'}

    def fetch_all_provinces(self, limit_provinces=63):
        """Chạy song song việc crawl dữ liệu cho nhiều tỉnh."""
        session = SessionLocal()
        try:
            provinces = session.query(Province).order_by(Province.province_id).limit(limit_provinces).all()
            # Lưu tên các tỉnh ra list để xử lý đa luồng
            province_names = [p.province_name for p in provinces]
        finally:
            session.close()

        logger.info(f"🚀 Bắt đầu Crawl song song cho {len(province_names)} tỉnh thành...")
        
        # Sử dụng tối đa 4 luồng song song để tránh bị block IP diện rộng
        max_workers = 4
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch_with_retry, name): name for name in province_names}
            for future in as_completed(futures):
                p_name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"❌ Lỗi nghiêm trọng khi xử lý {p_name}: {e}")

    def fetch_with_retry(self, province_name):
        """Thử crawl một tỉnh với các biến thể tên và nhiều server khác nhau."""
        variants = [province_name, f"Thành phố {province_name}", f"Tỉnh {province_name}"]
        for name in variants:
            if self.fetch_by_area(name):
                return True
        return False

    def fetch_by_area(self, area_name):
        """Gửi request đến server khả dụng và lưu dữ liệu theo batch."""
        query = f"""
        [out:json][timeout:900];
        area["name"~"{area_name}"]->.searchArea;
        (
          node["addr:street"](area.searchArea);
          way["addr:street"](area.searchArea);
          way["highway"](area.searchArea);
          node["amenity"](area.searchArea);
          way["building"](area.searchArea);
        );
        out body 10000;
        """

        # Thử lần lượt các server cho đến khi thành công hoặc hết server
        for server_url in self.servers:
            try:
                logger.info(f"📡 Request -> {area_name} via {server_url}")
                response = requests.post(server_url, data={'data': query}, headers=self.headers, timeout=120)
                
                if response.status_code == 429:
                    logger.warning(f"⏳ Server {server_url} bận, đổi server...")
                    continue
                
                response.raise_for_status()
                data = response.json()
                elements = data.get("elements", [])
                if not elements: 
                    return False

                self.process_and_save(elements, area_name)
                return True

            except Exception as e:
                logger.warning(f"⚠️ Server {server_url} lỗi: {e}. Thử server tiếp theo...")
                continue
        
        return False

    def process_and_save(self, elements, area_name):
        """Xử lý và lưu dữ liệu vào DB theo từng batch nhỏ."""
        raw_entities, streets, buildings, pois = [], [], [], []

        for el in elements:
            tags = el.get("tags", {})
            osm_id = el["id"]
            raw_entities.append({
                "id": osm_id, 
                "osm_type": el["type"], 
                "tags": json.dumps(tags, ensure_ascii=False)
            })
            
            name = tags.get("name") or tags.get("addr:street")
            if not name: continue
            
            if "highway" in tags or "addr:street" in tags:
                streets.append({"id": osm_id, "name": name})
            if "building" in tags:
                buildings.append({"id": osm_id, "name": name, "type": tags.get("building")})
            poi_type = tags.get("amenity") or tags.get("shop") or tags.get("tourism")
            if poi_type:
                pois.append({"id": osm_id, "name": name, "type": poi_type})

        # Lưu vào Database
        session = SessionLocal()
        try:
            self._save_batch(session, "osm.raw_entities", raw_entities, ["id", "osm_type", "tags"])
            self._save_batch(session, "osm.streets", streets, ["id", "name"])
            self._save_batch(session, "osm.buildings", buildings, ["id", "name", "type"])
            self._save_batch(session, "osm.pois", pois, ["id", "name", "type"])
            logger.info(f"✅ {area_name} hoàn tất! ({len(raw_entities)} records)")
        finally:
            session.close()

    def _save_batch(self, session, table_name, data, columns):
        if not data: return
        batch_size = 500 # Giảm size batch để commit nhanh hơn nữa
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            col_names = ", ".join(columns)
            placeholders = ", ".join([f":{c}" for c in columns])
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            session.execute(sql_text(query), batch)
            session.commit()
