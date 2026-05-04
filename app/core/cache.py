"""
Redis Cache Module - VN Address Intelligence
============================================
Cung cấp:
- Kết nối Redis với graceful degradation (fallback no-op khi Redis offline).
- Hash cache cho đơn vị hành chính: province, district, ward.
- Cache key namespace rõ ràng, TTL cấu hình qua .env.
- Cơ chế auto-clear cache theo entity level khi có chỉnh sửa/đồng bộ dữ liệu.
"""

import json
import logging
import hashlib
from typing import Any, Optional, List
from functools import wraps

import redis
from redis.exceptions import RedisError

from app.core.config import Config

logger = logging.getLogger("VNAI_Cache")

# ─── Key Namespaces ────────────────────────────────────────────────────────────
# Hash key: lưu toàn bộ danh sách theo version
# vn:admin:provinces:{version}       -> HSET field=province_id  value=json
# vn:admin:districts:{version}:{province_id}  -> HSET field=district_id value=json
# vn:admin:wards:{version}:{district_id}      -> HSET field=ward_id     value=json
# vn:admin:unit:{level}:{version}:{unit_id}   -> STRING (single entity)
# vn:admin:ward_mapping:{query_hash}          -> STRING (mapping search results)

NS_PROVINCES    = "vn:admin:provinces:{version}"
NS_DISTRICTS    = "vn:admin:districts:{version}:{province_id}"
NS_WARDS        = "vn:admin:wards:{version}:{district_id}"
NS_UNIT         = "vn:admin:unit:{level}:{version}:{unit_id}"
NS_WARD_MAPPING = "vn:admin:ward_mapping:{hash}"

# Pattern để xóa theo nhóm
PATTERN_ALL_ADMIN     = "vn:admin:*"
PATTERN_PROVINCES     = "vn:admin:provinces:*"
PATTERN_DISTRICTS     = "vn:admin:districts:*"
PATTERN_WARDS         = "vn:admin:wards:*"
PATTERN_UNIT          = "vn:admin:unit:*"
PATTERN_WARD_MAPPING  = "vn:admin:ward_mapping:*"


# ─── Connection ────────────────────────────────────────────────────────────────

class _NullRedis:
    """No-op Redis stub khi Redis không khả dụng hoặc bị tắt."""

    def hget(self, *a, **kw):      return None
    def hset(self, *a, **kw):      return 0
    def hgetall(self, *a, **kw):   return {}
    def get(self, *a, **kw):       return None
    def set(self, *a, **kw):       return None
    def setex(self, *a, **kw):     return None
    def delete(self, *a, **kw):    return 0
    def scan_iter(self, *a, **kw): return iter([])
    def expire(self, *a, **kw):    return 0
    def exists(self, *a, **kw):    return 0
    def ping(self):                return False
    def pipeline(self):            return _NullPipeline()
    @property
    def available(self):           return False


class _NullPipeline:
    def hset(self, *a, **kw):   return self
    def expire(self, *a, **kw): return self
    def execute(self):          return []
    def __enter__(self):        return self
    def __exit__(self, *a):     pass


def _build_redis_client():
    if not Config.REDIS_ENABLED:
        logger.info("Redis cache disabled via REDIS_ENABLED=false")
        return _NullRedis()
    try:
        client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            password=Config.REDIS_PASSWORD,
            db=Config.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=False,
        )
        client.ping()
        logger.info(
            f"Redis connected: {Config.REDIS_HOST}:{Config.REDIS_PORT} db={Config.REDIS_DB} "
            f"TTL={Config.REDIS_CACHE_TTL}s"
        )
        # Gắn flag để bên ngoài có thể kiểm tra
        client.available = True
        return client
    except (RedisError, Exception) as e:
        logger.warning(f"Redis unavailable ({e}). Running without cache (graceful degradation).")
        return _NullRedis()


# Singleton client – khởi tạo một lần khi import module
_redis_client = None


def get_redis() -> redis.Redis:
    """Trả về Redis client (hoặc NullRedis nếu không kết nối được)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = _build_redis_client()
    return _redis_client


def reconnect_redis():
    """Tái khởi tạo kết nối Redis (dùng sau khi cấu hình thay đổi)."""
    global _redis_client
    _redis_client = _build_redis_client()
    return _redis_client


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _ttl() -> int:
    return Config.REDIS_CACHE_TTL


def _serialize(obj: Any) -> str:
    """Serialize SQLAlchemy row hoặc dict/list thành JSON string."""
    if obj is None:
        return "null"
    if isinstance(obj, (dict, list, str, int, float, bool)):
        return json.dumps(obj, ensure_ascii=False, default=str)
    # SQLAlchemy model instance → __dict__
    if hasattr(obj, "__dict__"):
        data = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return json.dumps(data, ensure_ascii=False, default=str)
    return json.dumps(str(obj), ensure_ascii=False)


def _deserialize(raw: str) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def _query_hash(*args, **kwargs) -> str:
    """Tạo hash ngắn từ bộ tham số để làm cache key."""
    key_str = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()[:12]


def _delete_pattern(pattern: str) -> int:
    """Xóa toàn bộ key khớp pattern. Trả về số key đã xóa."""
    rc = get_redis()
    keys = list(rc.scan_iter(pattern))
    if not keys:
        return 0
    deleted = 0
    # Delete theo batch 100 để tránh blocking
    for i in range(0, len(keys), 100):
        batch = keys[i:i + 100]
        deleted += rc.delete(*batch)
    return deleted


# ─── Cache API: Province ───────────────────────────────────────────────────────

def cache_provinces_set(version: int, rows: List[Any]) -> None:
    """Lưu danh sách province vào hash cache."""
    rc = get_redis()
    key = NS_PROVINCES.format(version=version)
    pipe = rc.pipeline()
    for row in rows:
        field = str(row.province_id if hasattr(row, "province_id") else row.get("province_id", ""))
        pipe.hset(key, field, _serialize(row))
    pipe.expire(key, _ttl())
    pipe.execute()
    logger.debug(f"Cache SET provinces v{version}: {len(rows)} entries")


def cache_provinces_get(version: int) -> Optional[List[dict]]:
    """Lấy danh sách province từ cache. Trả về None nếu cache miss."""
    rc = get_redis()
    key = NS_PROVINCES.format(version=version)
    raw = rc.hgetall(key)
    if not raw:
        return None
    return [_deserialize(v) for v in raw.values()]


# ─── Cache API: District ───────────────────────────────────────────────────────

def cache_districts_set(version: int, province_id: Optional[int], rows: List[Any]) -> None:
    prov_key = province_id if province_id is not None else "all"
    key = NS_DISTRICTS.format(version=version, province_id=prov_key)
    rc = get_redis()
    pipe = rc.pipeline()
    for row in rows:
        field = str(row.district_id if hasattr(row, "district_id") else row.get("district_id", ""))
        pipe.hset(key, field, _serialize(row))
    pipe.expire(key, _ttl())
    pipe.execute()
    logger.debug(f"Cache SET districts v{version} province={prov_key}: {len(rows)} entries")


def cache_districts_get(version: int, province_id: Optional[int]) -> Optional[List[dict]]:
    prov_key = province_id if province_id is not None else "all"
    key = NS_DISTRICTS.format(version=version, province_id=prov_key)
    rc = get_redis()
    raw = rc.hgetall(key)
    if not raw:
        return None
    return [_deserialize(v) for v in raw.values()]


# ─── Cache API: Ward ──────────────────────────────────────────────────────────

def cache_wards_set(version: int, district_id: Optional[int], rows: List[Any]) -> None:
    dist_key = district_id if district_id is not None else "all"
    key = NS_WARDS.format(version=version, district_id=dist_key)
    rc = get_redis()
    pipe = rc.pipeline()
    for row in rows:
        field = str(row.ward_id if hasattr(row, "ward_id") else row.get("ward_id", ""))
        pipe.hset(key, field, _serialize(row))
    pipe.expire(key, _ttl())
    pipe.execute()
    logger.debug(f"Cache SET wards v{version} district={dist_key}: {len(rows)} entries")


def cache_wards_get(version: int, district_id: Optional[int]) -> Optional[List[dict]]:
    dist_key = district_id if district_id is not None else "all"
    key = NS_WARDS.format(version=version, district_id=dist_key)
    rc = get_redis()
    raw = rc.hgetall(key)
    if not raw:
        return None
    return [_deserialize(v) for v in raw.values()]


# ─── Cache API: Single Unit ───────────────────────────────────────────────────

def cache_unit_set(level: str, version: int, unit_id: int, obj: Any) -> None:
    key = NS_UNIT.format(level=level, version=version, unit_id=unit_id)
    rc = get_redis()
    rc.setex(key, _ttl(), _serialize(obj))
    logger.debug(f"Cache SET unit {level}/{unit_id} v{version}")


def cache_unit_get(level: str, version: int, unit_id: int) -> Optional[dict]:
    key = NS_UNIT.format(level=level, version=version, unit_id=unit_id)
    rc = get_redis()
    raw = rc.get(key)
    return _deserialize(raw)


# ─── Cache API: Ward Mapping Search ───────────────────────────────────────────

def cache_mapping_set(params: dict, rows: List[Any]) -> None:
    h = _query_hash(**params)
    key = NS_WARD_MAPPING.format(hash=h)
    rc = get_redis()
    rc.setex(key, _ttl(), _serialize(rows))
    logger.debug(f"Cache SET ward_mapping hash={h}")


def cache_mapping_get(params: dict) -> Optional[list]:
    h = _query_hash(**params)
    key = NS_WARD_MAPPING.format(hash=h)
    rc = get_redis()
    raw = rc.get(key)
    return _deserialize(raw)


# ─── Auto-Clear: Invalidation by Level ────────────────────────────────────────

def invalidate_provinces() -> int:
    """Xóa cache province + unit province. Gọi khi province được cập nhật."""
    n = _delete_pattern(PATTERN_PROVINCES)
    n += _delete_pattern("vn:admin:unit:province:*")
    logger.info(f"Cache INVALIDATED provinces: {n} keys deleted")
    return n


def invalidate_districts(province_id: Optional[int] = None) -> int:
    """Xóa cache district. Nếu province_id=None thì xóa toàn bộ district cache."""
    if province_id is not None:
        pattern = f"vn:admin:districts:*:{province_id}"
    else:
        pattern = PATTERN_DISTRICTS
    n = _delete_pattern(pattern)
    n += _delete_pattern("vn:admin:unit:district:*")
    logger.info(f"Cache INVALIDATED districts province_id={province_id}: {n} keys deleted")
    return n


def invalidate_wards(district_id: Optional[int] = None) -> int:
    """Xóa cache ward. Nếu district_id=None thì xóa toàn bộ ward cache."""
    if district_id is not None:
        pattern = f"vn:admin:wards:*:{district_id}"
    else:
        pattern = PATTERN_WARDS
    n = _delete_pattern(pattern)
    n += _delete_pattern("vn:admin:unit:ward:*")
    logger.info(f"Cache INVALIDATED wards district_id={district_id}: {n} keys deleted")
    return n


def invalidate_ward_mapping() -> int:
    """Xóa cache ward mapping search."""
    n = _delete_pattern(PATTERN_WARD_MAPPING)
    logger.info(f"Cache INVALIDATED ward_mapping: {n} keys deleted")
    return n


def invalidate_all_admin() -> int:
    """Xóa toàn bộ admin unit cache (province + district + ward + mapping)."""
    n = _delete_pattern(PATTERN_ALL_ADMIN)
    logger.info(f"Cache INVALIDATED all admin: {n} keys deleted")
    return n


# ─── Convenience Decorator ────────────────────────────────────────────────────

def cached_admin(key_template: str, ttl: Optional[int] = None):
    """
    Decorator đơn giản cho các hàm trả về JSON-serializable.
    key_template có thể dùng {arg_name} để bind từ kwargs.

    Ví dụ:
        @cached_admin("vn:admin:my_key:{version}")
        def get_something(version=1): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                k = key_template.format(**kwargs)
                rc = get_redis()
                cached = rc.get(k)
                if cached is not None:
                    return _deserialize(cached)
                result = fn(*args, **kwargs)
                rc.setex(k, ttl or _ttl(), _serialize(result))
                return result
            except RedisError as e:
                logger.warning(f"Redis error in cached_admin decorator: {e}")
                return fn(*args, **kwargs)
        return wrapper
    return decorator


# ─── Health / Info ────────────────────────────────────────────────────────────

def cache_health() -> dict:
    """Trả về trạng thái Redis và thống kê cache key admin."""
    rc = get_redis()
    if isinstance(rc, _NullRedis):
        return {
            "redis_enabled": Config.REDIS_ENABLED,
            "redis_available": False,
            "ttl_default": _ttl(),
        }
    try:
        info = rc.info("server")
        key_counts = {
            "provinces": len(list(rc.scan_iter(PATTERN_PROVINCES))),
            "districts": len(list(rc.scan_iter(PATTERN_DISTRICTS))),
            "wards":     len(list(rc.scan_iter(PATTERN_WARDS))),
            "units":     len(list(rc.scan_iter(PATTERN_UNIT))),
            "mapping":   len(list(rc.scan_iter(PATTERN_WARD_MAPPING))),
        }
        return {
            "redis_enabled": Config.REDIS_ENABLED,
            "redis_available": True,
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "ttl_default": _ttl(),
            "host": Config.REDIS_HOST,
            "port": Config.REDIS_PORT,
            "db": Config.REDIS_DB,
            "cache_key_counts": key_counts,
        }
    except RedisError as e:
        return {"redis_enabled": Config.REDIS_ENABLED, "redis_available": False, "error": str(e)}
