"""
services/osm_fetcher.py
=======================
Crawl dữ liệu địa điểm, đường xá từ OpenStreetMap (OSM) qua Overpass API.

Ví dụ thực thi mẫu:
------------------
from app.services.osm_fetcher import OSMFetcher
fetcher = OSMFetcher()
# fetcher.fetch_by_area("Quận 1", 1, "Thành phố Hồ Chí Minh")
"""
import requests
import logging
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.core.database import SessionLocal, OSMStreet, OSMBuilding, OSMPoi, Province, OSMRawEntity
from app.core.config import Config
from sqlalchemy import text as sql_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("OSMFetcher")

class OSMFetcher:
    def __init__(self):
        self.servers = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.osm.ch/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter"
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }

    def fetch_all_provinces(self, limit_provinces=63, target_total=5000000):
        """Crawl toan bo 63 tinh thanh cho den khi dat target."""
        target_total = max(0, int(target_total))
        session = SessionLocal()
        try:
            from app.core.database import District
            # Lay quan huyen, uu tien cac khu vuc chua co nhieu du lieu
            districts = session.query(District, Province.province_name)\
                .join(Province, District.province_id == Province.province_id)\
                .order_by(District.district_id).all()
            
            task_list = [(d.District.district_id, d.District.district_name, d.province_name, d.District.province_id) for d in districts]
            task_list = task_list[:max(0, int(limit_provinces))]
        finally:
            session.close()

        logger.info(f"Starting aggressive crawl for {len(task_list)} district areas...")
        
        current_count = self.get_current_count()
        logger.info(f"Initial count: {current_count}")

        # Giam concurrency de tranh bi 429
        max_workers = 3 
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for d_id, d_name, p_name, p_id in task_list:
                if current_count >= target_total:
                    logger.info(f"Target {target_total:,} reached. Stopping.")
                    break
                
                futures.append(executor.submit(self.fetch_district, d_id, d_name, p_name, p_id))
                
                if len(futures) % 20 == 0:
                    current_count = self.get_current_count()
                    logger.info(f"---> Current Progress: {current_count}/{target_total}")

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    pass

    def get_current_count(self):
        session = SessionLocal()
        try:
            from sqlalchemy import func
            return session.query(func.count(OSMRawEntity.id)).scalar()
        finally:
            session.close()

    def fetch_district(self, district_id, district_name, province_name, province_id):
        """Crawl theo cap District."""
        # Clean ten district (vi du: "Quan Ba Dinh" -> "Ba Dinh")
        clean_name = district_name.replace("Quận ", "").replace("Huyện ", "").replace("Thành phố ", "").replace("Thị xã ", "")
        return self.fetch_by_area(clean_name, province_id, province_name)

    def fetch_by_area(self, area_name, province_id, province_name):
        """Query Area linh hoat hon voi admin_level."""
        query = f"""
        [out:json][timeout:900];
        area["name"~"{area_name}"]["admin_level"~"4|6|7|8"]->.searchArea;
        (
          node["addr:street"](area.searchArea);
          way["addr:street"](area.searchArea);
          way["highway"](area.searchArea);
          node["amenity"](area.searchArea);
          node["shop"](area.searchArea);
          node["office"](area.searchArea);
          node["tourism"](area.searchArea);
          way["building"](area.searchArea);
        );
        out body 50000;
        """

        for server_url in self.servers:
            try:
                logger.info(f"[FETCH] {area_name} ({province_name}) via {server_url.split('/')[2]}")
                response = requests.get(server_url, params={'data': query}, headers=self.headers, timeout=300)
                
                if response.status_code == 429:
                    time.sleep(30)
                    continue
                
                if response.status_code != 200:
                    continue

                data = response.json()
                elements = data.get("elements", [])
                if not elements: 
                    # Thu lai voi query rong hon neu can
                    return False

                self.process_and_save(elements, province_id, province_name)
                return True

            except Exception:
                continue
        
        return False

    def process_and_save(self, elements, province_id, province_name):
        """Luu batch du lieu."""
        raw_entities, streets, buildings, pois = [], [], [], []

        for el in elements:
            tags = el.get("tags", {})
            osm_id = el["id"]
            
            # Map raw entity
            raw_entities.append({
                "id": osm_id, 
                "osm_type": el["type"], 
                "tags": json.dumps(tags, ensure_ascii=False),
                "province_id": province_id,
                "province_name": province_name
            })
            
            # Map specialized tables
            name = tags.get("name") or tags.get("addr:street")
            if not name: continue
            
            if "highway" in tags or "addr:street" in tags:
                streets.append({"id": osm_id, "name": name, "province_id": province_id, "province_name": province_name})
            if "building" in tags:
                buildings.append({"id": osm_id, "name": name, "type": tags.get("building"), "province_id": province_id, "province_name": province_name})
            poi_type = tags.get("amenity") or tags.get("shop") or tags.get("tourism") or tags.get("office")
            if poi_type:
                pois.append({"id": osm_id, "name": name, "type": poi_type, "province_id": province_id, "province_name": province_name})

        # DB Persist
        session = SessionLocal()
        try:
            self._save_batch(session, "osm.raw_entities", raw_entities, ["id", "osm_type", "tags", "province_id", "province_name"])
            self._save_batch(session, "osm.streets", streets, ["id", "name", "province_id", "province_name"])
            self._save_batch(session, "osm.buildings", buildings, ["id", "name", "type", "province_id", "province_name"])
            self._save_batch(session, "osm.pois", pois, ["id", "name", "type", "province_id", "province_name"])
            logger.info(f"[SUCCESS] {province_name}: +{len(raw_entities)} records.")
        finally:
            session.close()

    def _save_batch(self, session, table_name, data, columns):
        if not data: return
        batch_size = 500
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            col_names = ", ".join(columns)
            placeholders = ", ".join([f":{c}" for c in columns])
            query = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            session.execute(sql_text(query), batch)
            session.commit()
