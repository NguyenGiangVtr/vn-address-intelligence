from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- PROVINCE ---
class ProvinceBase(BaseModel):
    province_no: Optional[str] = None
    province_name: str
    type_name: str
    province_name_en: Optional[str] = None
    is_default: Optional[bool] = True
    is_deleted: Optional[bool] = False
    admin_version: Optional[int] = 1

class ProvinceCreate(ProvinceBase):
    pass

class ProvinceUpdate(BaseModel):
    province_no: Optional[str] = None
    province_name: Optional[str] = None
    type_name: Optional[str] = None
    province_name_en: Optional[str] = None
    is_default: Optional[bool] = None
    is_deleted: Optional[bool] = None
    admin_version: Optional[int] = None

class ProvinceResponse(ProvinceBase):
    province_id: int
    created_date: datetime
    updated_date: datetime

    class Config:
        from_attributes = True

# --- DISTRICT ---
class DistrictBase(BaseModel):
    province_id: int
    district_no: Optional[str] = None
    district_name: str
    type_name: Optional[str] = None
    location: Optional[str] = None
    is_default: Optional[bool] = True
    is_deleted: Optional[bool] = False
    is_active: Optional[bool] = True
    admin_version: Optional[int] = 1

class DistrictCreate(DistrictBase):
    pass

class DistrictUpdate(BaseModel):
    province_id: Optional[int] = None
    district_no: Optional[str] = None
    district_name: Optional[str] = None
    type_name: Optional[str] = None
    location: Optional[str] = None
    is_default: Optional[bool] = None
    is_deleted: Optional[bool] = None
    is_active: Optional[bool] = None
    admin_version: Optional[int] = None

class DistrictResponse(DistrictBase):
    district_id: int
    created_date: datetime
    updated_date: datetime

    class Config:
        from_attributes = True

# --- WARD ---
class WardBase(BaseModel):
    district_id: int
    ward_no: Optional[str] = None
    province_no: Optional[str] = None
    ward_name: str
    type_name: Optional[str] = None
    location: Optional[str] = None
    is_default: Optional[bool] = True
    is_deleted: Optional[bool] = False
    is_active: Optional[bool] = True
    admin_version: Optional[int] = 1

class WardCreate(WardBase):
    pass

class WardUpdate(BaseModel):
    district_id: Optional[int] = None
    ward_no: Optional[str] = None
    province_no: Optional[str] = None
    ward_name: Optional[str] = None
    type_name: Optional[str] = None
    location: Optional[str] = None
    is_default: Optional[bool] = None
    is_deleted: Optional[bool] = None
    is_active: Optional[bool] = None
    admin_version: Optional[int] = None

class WardResponse(WardBase):
    ward_id: int
    created_date: datetime
    updated_date: datetime

    class Config:
        from_attributes = True
