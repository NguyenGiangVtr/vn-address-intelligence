import sys
from pathlib import Path
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

import os
import sys
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, aliased

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import Config
from app.core.database import Province, District, Ward, WardMapping

# Setup DB
engine = create_engine(Config.SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def test_lookup_mapping():
    district_id = 79
    version = 2
    
    ProvV1 = aliased(Province)
    ProvV2 = aliased(Province)
    WardV1 = aliased(Ward)
    WardV2 = aliased(Ward)
    DistV1 = aliased(District)
    DistV2 = aliased(District)

    try:
        query = db.query(
            WardMapping.ward_mapping_id.label("id"),
            WardMapping.ward_id_old,
            WardMapping.ward_id_new,
            WardMapping.province_id_old,
            WardMapping.province_id_new,
            WardMapping.updated_note,
            WardMapping.effective_date_from,
            WardMapping.effective_date_to,
            WardMapping.relationship_type,
            WardMapping.mapping_total,
            
            WardV1.ward_name.label("ward_name_old"),
            WardV2.ward_name.label("ward_name_new"),
            ProvV1.province_name.label("province_name_old"),
            ProvV2.province_name.label("province_name_new"),
            WardV1.district_id.label("district_id_old"),
            DistV1.district_name.label("district_name_old"),
            WardV2.district_id.label("district_id_new"),
            DistV2.district_name.label("district_name_new")
        ).outerjoin(
            WardV1, and_(WardV1.ward_id == WardMapping.ward_id_old, WardV1.admin_version == 1) 
        ).outerjoin(
            WardV2, and_(WardV2.ward_id == WardMapping.ward_id_new, WardV2.is_deleted == False, WardV2.admin_version == 2)
        ).outerjoin(
            DistV1, and_(DistV1.district_id == func.coalesce(WardV1.district_id, WardMapping.district_id_old), DistV1.admin_version == 1)
        ).outerjoin(
            DistV2, and_(DistV2.district_id == WardV2.district_id, DistV2.is_deleted == False, DistV2.admin_version == 2)
        ).outerjoin(
            ProvV1, and_(ProvV1.province_id == func.coalesce(DistV1.province_id, WardMapping.province_id_old), ProvV1.admin_version == 1)
        ).outerjoin(
            ProvV2, and_(ProvV2.province_id == func.coalesce(DistV2.province_id, WardMapping.province_id_new), ProvV2.is_deleted == False, ProvV2.admin_version == 2)
        )

        filters = []
        if district_id:
            if version == 2:
                filters.append(or_(WardV2.district_id == district_id, DistV2.district_id == district_id))
        
        if filters:
            query = query.filter(and_(*filters))
            
        print("SQL Query Generated:")
        print(query.statement.compile(compile_kwargs={"literal_binds": True}))
        
        results = query.all()
        print(f"\nSuccess! Found {len(results)} results.")
        
    except Exception as e:
        print("\nError occurred:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lookup_mapping()
    db.close()
