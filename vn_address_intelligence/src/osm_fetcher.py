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
        self.servers = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.osm.ch/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter"
        ]
        self.headers = {'User-Agent': 'VNAI-Bot/2.0 (contact: admin@vnai.com)'}

    def fetch_all_provinces(self, limit_provinces=63, target_total=5000000):
        """Crawl toan bo 63 tinh thanh cho den khi dat target."""
        session = SessionLocal()
        try:
            # Lay danh sach quan huyen de crawl sau hon
            from .database import District
            districts = session.query(District, Province.province_name)\
                .join(Province, District.province_id == Province.province_id)\
                .order_by(District.district_id).all()
            
            task_list = [(d.District.district_id, d.District.district_name, d.province_name, d.District.province_id) for d in districts]
        finally:
            session.close()

        logger.info(f"Starting aggressive crawl for {len(task_list)} districts...")
        
        current_count = self.get_current_count()
        logger.info(f"Initial count: {current_count}")

        max_workers = 5
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for d_id, d_name, p_name, p_id in task_list:
                if current_count >= target_total:
                    logger.info("Target 5M reached. Stopping.")
                    break
                
                futures.append(executor.submit(self.fetch_district, d_id, d_name, p_name, p_id))
                
                # Check count periodically
                if len(futures) % 20 == 0:
                    current_count = self.get_current_count()
                    logger.info(f"---> Progress: {current_count}/{target_total} entities in DB")

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Task error: {e}")

    def get_current_count(self):
        session = SessionLocal()
        try:
            from sqlalchemy import func
            return session.query(func.count(OSMRawEntity.id)).scalar()
        finally:
            session.close()

    def fetch_district(self, district_id, district_name, province_name, province_id):
        """Crawl theo cap District de lay du lieu chi tiet hon."""
        search_name = f"{district_name}, {province_name}"
        return self.fetch_by_area(search_name, province_id, province_name)

    def fetch_by_area(self, area_name, province_id, province_name):
        """Gui request voi query mo rong va limit cao hon."""
        query = f"""
        [out:json][timeout:900];
        area["name"~"{area_name}"]->.searchArea;
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
                logger.info(f"[FETCH] Starting: {area_name} ...")
                response = requests.post(server_url, data={'data': query}, headers=self.headers, timeout=180)
                
                if response.status_code == 429:
                    logger.warning(f"Server {server_url} busy (429), waiting 15s...")
                    time.sleep(15)
                    continue
                
                response.raise_for_status()
                data = response.json()
                elements = data.get("elements", [])
                if not elements: 
                    logger.info(f"[EMPTY] {area_name} returned no relevant elements.")
                    return False

                self.process_and_save(elements, province_id, province_name)
                return True

            except Exception as e:
                # logger.warning(f"Server {server_url} failed for {area_name}")
                continue
        
        return False

    def process_and_save(self, elements, province_id, province_name):
        """Xu ly va luu du lieu vao DB theo tung batch nho, bao gom province info."""
        raw_entities, streets, buildings, pois = [], [], [], []

        for el in elements:
            # ... (logic mapping el to lists)
            tags = el.get("tags", {})
            osm_id = el["id"]
            raw_entities.append({
                "id": osm_id, 
                "osm_type": el["type"], 
                "tags": json.dumps(tags, ensure_ascii=False),
                "province_id": province_id,
                "province_name": province_name
            })
            
            name = tags.get("name") or tags.get("addr:street")
            if not name: continue
            
            if "highway" in tags or "addr:street" in tags:
                streets.append({
                    "id": osm_id, "name": name, 
                    "province_id": province_id, "province_name": province_name
                })
            if "building" in tags:
                buildings.append({
                    "id": osm_id, "name": name, "type": tags.get("building"),
                    "province_id": province_id, "province_name": province_name
                })
            poi_type = tags.get("amenity") or tags.get("shop") or tags.get("tourism") or tags.get("office")
            if poi_type:
                pois.append({
                    "id": osm_id, "name": name, "type": poi_type,
                    "province_id": province_id, "province_name": province_name
                })

        # Luu vao Database
        session = SessionLocal()
        try:
            self._save_batch(session, "osm.raw_entities", raw_entities, 
                           ["id", "osm_type", "tags", "province_id", "province_name"])
            self._save_batch(session, "osm.streets", streets, 
                           ["id", "name", "province_id", "province_name"])
            self._save_batch(session, "osm.buildings", buildings, 
                           ["id", "name", "type", "province_id", "province_name"])
            self._save_batch(session, "osm.pois", pois, 
                           ["id", "name", "type", "province_id", "province_name"])
            logger.info(f"[SUCCESS] {province_name}: Saved {len(raw_entities)} entities.")
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
