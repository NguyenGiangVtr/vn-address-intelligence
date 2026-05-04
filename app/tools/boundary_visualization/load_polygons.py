from sqlalchemy import text
from app.core.database import engine


def fetch_area_polygons(scope, province_id=None, district_id=None, ward_id=None):
    if scope not in {"province", "district", "ward"}:
        raise ValueError("scope must be one of: province, district, ward")

    base_sql = """
        SELECT area_polygon_id, area_name, province_id, district_id, ward_id, partner_name, coordinates
        FROM mat.area_polygon
        WHERE COALESCE(is_deleted, false) = false
    """

    params = {}

    if scope == "province":
        if province_id is None:
            raise ValueError("province_id is required for province scope")
        base_sql += " AND province_id = :province_id AND district_id IS NULL AND ward_id IS NULL"
        params["province_id"] = province_id
    elif scope == "district":
        if district_id is None:
            raise ValueError("district_id is required for district scope")
        base_sql += " AND district_id = :district_id AND ward_id IS NULL"
        params["district_id"] = district_id
        if province_id is not None:
            base_sql += " AND province_id = :province_id"
            params["province_id"] = province_id
    elif scope == "ward":
        if ward_id is None:
            raise ValueError("ward_id is required for ward scope")
        base_sql += " AND ward_id = :ward_id"
        params["ward_id"] = ward_id
        if district_id is not None:
            base_sql += " AND district_id = :district_id"
            params["district_id"] = district_id
        if province_id is not None:
            base_sql += " AND province_id = :province_id"
            params["province_id"] = province_id

    with engine.connect() as conn:
        result = conn.execute(text(base_sql), params)
        rows = [dict(row._mapping) for row in result]
    return rows
