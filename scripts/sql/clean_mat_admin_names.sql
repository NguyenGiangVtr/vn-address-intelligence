-- Làm sạch tên đơn vị: bỏ mọi chuỗi (type_name || ' ') trong cột tên,
-- khớp logic Python: clean_admin_unit_name / NSO sync.
-- Chạy sau khi import Excel/CSV cũ hoặc một lần trước khi build corpus.

BEGIN;

UPDATE mat.province
SET province_name = trim(both FROM replace(province_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> '';

UPDATE mat.district
SET district_name = trim(both FROM replace(district_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> '';

UPDATE mat.ward
SET ward_name = trim(both FROM replace(ward_name, coalesce(type_name, '') || ' ', ''))
WHERE coalesce(type_name, '') <> '';

COMMIT;
