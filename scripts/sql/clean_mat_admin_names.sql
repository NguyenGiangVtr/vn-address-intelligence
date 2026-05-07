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

UPDATE mat.province
SET province_name = trim(both FROM regexp_replace(province_name, '^Thành phố[[:space:]]+', ''))
WHERE trim(both FROM coalesce(type_name, '')) = 'Thành phố Trung ương'
  AND province_name ~ '^Thành phố[[:space:]]+';

UPDATE mat.district
SET district_name = trim(both FROM regexp_replace(district_name, '^Thành phố[[:space:]]+', ''))
WHERE trim(both FROM coalesce(type_name, '')) = 'Thành phố Trung ương'
  AND district_name ~ '^Thành phố[[:space:]]+';

UPDATE mat.ward
SET ward_name = trim(both FROM regexp_replace(ward_name, '^Thành phố[[:space:]]+', ''))
WHERE trim(both FROM coalesce(type_name, '')) = 'Thành phố Trung ương'
  AND ward_name ~ '^Thành phố[[:space:]]+';

-- Thu gọn nhãn LoaiHinh sang "Thành phố" (sau khi đã strip tên đúng vai trò Trung ương ở trên).
UPDATE mat.province
SET type_name = 'Thành phố'
WHERE trim(both FROM coalesce(type_name, '')) = 'Thành phố Trung ương';

UPDATE mat.district
SET type_name = 'Thành phố'
WHERE trim(both FROM coalesce(type_name, '')) = 'Thành phố Trung ương';

-- Cột *_name_en / type_name_en: chạy `python -m app.main admin:clean-names` (bước Python, remove_vietnamese_marks).

COMMIT;
