-- DROP FUNCTION scm.update_address_smart();

CREATE OR REPLACE FUNCTION scm.update_address_smart()
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    r RECORD;
    arr TEXT[];
    len INT;
    v_street_address TEXT;
    v_postal_code TEXT;
    v_idx_pointer INT;
    v_current_element TEXT;
    count_updated INT := 0;
BEGIN
    FOR r IN
        SELECT 
            id, address_raw, 
            ward_name, district_name, province_name
        FROM scm.address
        -- Chỉ xử lý dòng chưa có street_address và address_raw không bị trống
        WHERE street_address IS NULL 
          AND NULLIF(TRIM(address_raw), '') IS NOT NULL
    LOOP
        -- 1. Tiền xử lý: Chuyển chuỗi thành mảng
        arr := string_to_array(regexp_replace(r.address_raw, ',\s+', ',', 'g'), ',');
        len := array_length(arr, 1);
        v_idx_pointer := len;

        IF len >= 2 THEN
            
            -- 2. Bóc Quốc gia (nếu có ở cuối)
            IF arr[v_idx_pointer] ILIKE '%Việt Nam%' OR arr[v_idx_pointer] ILIKE '%Vietnam%' OR arr[v_idx_pointer] ILIKE '%VN%' THEN
                v_idx_pointer := v_idx_pointer - 1;
            END IF;

            -- 3. Bóc Postal Code (nếu dính ở phần tử cuối hiện tại)
            v_current_element := TRIM(arr[v_idx_pointer]);
            IF v_current_element ~ '\d{5,6}$' THEN
                v_postal_code := SUBSTRING(v_current_element FROM '\d{5,6}$');
                -- Nếu phần tử CHỈ là một dãy số (VD đứng riêng: "700000"), lùi con trỏ
                IF v_current_element ~ '^\d{5,6}$' THEN
                    v_idx_pointer := v_idx_pointer - 1;
                ELSE
                    -- Nếu số bưu chính dính vào Tỉnh (VD: "Hồ Chí Minh 700000"), chỉ xóa số
                    arr[v_idx_pointer] := TRIM(REGEXP_REPLACE(v_current_element, '\s+\d{5,6}$', ''));
                END IF;
            ELSE
                v_postal_code := NULL;
            END IF;

            -- 4. Bóc tách ngược: Tỉnh -> Quận -> Phường 
            -- (Đối chiếu chéo với dữ liệu đã có sẵn trong bảng)
            
            -- 4.1. Cấp 1 (Tỉnh/Thành)
            IF v_idx_pointer >= 1 THEN
                v_current_element := TRIM(arr[v_idx_pointer]);
                IF r.province_name IS NOT NULL AND (
                    v_current_element ILIKE '%Tỉnh%' OR v_current_element ILIKE '%Thành phố%' OR v_current_element ILIKE '%TP%' OR
                    r.province_name ILIKE '%' || v_current_element || '%' OR v_current_element ILIKE '%' || r.province_name || '%'
                ) THEN
                    v_idx_pointer := v_idx_pointer - 1;
                ELSIF r.province_name IS NOT NULL AND v_idx_pointer >= 3 THEN
                    -- Vớt lỗi: Nếu mảng dài, tự tin ngầm định phần tử cuối là Tỉnh
                    v_idx_pointer := v_idx_pointer - 1;
                END IF;
            END IF;

            -- 4.2. Cấp 2 (Quận/Huyện)
            IF v_idx_pointer >= 1 THEN
                v_current_element := TRIM(arr[v_idx_pointer]);
                IF r.district_name IS NOT NULL AND (
                    v_current_element ILIKE '%Quận%' OR v_current_element ILIKE '%Huyện%' OR v_current_element ILIKE '%Thị xã%' OR
                    r.district_name ILIKE '%' || v_current_element || '%' OR v_current_element ILIKE '%' || r.district_name || '%'
                ) THEN
                    v_idx_pointer := v_idx_pointer - 1;
                ELSIF r.district_name IS NOT NULL AND v_idx_pointer >= 2 THEN
                    v_idx_pointer := v_idx_pointer - 1;
                END IF;
            END IF;

            -- 4.3. Cấp 3 (Phường/Xã)
            -- LƯU Ý: Điều kiện v_idx_pointer >= 2 để đảm bảo luôn chừa lại ÍT NHẤT 1 phần tử cho street_address
            IF v_idx_pointer >= 2 THEN
                v_current_element := TRIM(arr[v_idx_pointer]);
                IF r.ward_name IS NOT NULL AND (
                    v_current_element ILIKE '%Phường%' OR v_current_element ILIKE '%Xã%' OR v_current_element ILIKE '%Thị trấn%' OR
                    r.ward_name ILIKE '%' || v_current_element || '%' OR v_current_element ILIKE '%' || r.ward_name || '%'
                ) THEN
                    v_idx_pointer := v_idx_pointer - 1;
                ELSIF r.ward_name IS NOT NULL AND v_idx_pointer >= 2 THEN
                    v_idx_pointer := v_idx_pointer - 1;
                END IF;
            END IF;

            -- 5. Gom phần lõi vào street_address
            IF v_idx_pointer >= 1 THEN
                v_street_address := array_to_string(arr[1 : v_idx_pointer], ', ');
            ELSE
                v_street_address := TRIM(arr[1]);
            END IF;

        ELSE
            -- Nếu địa chỉ gõ liền không có dấu phẩy (VD: "123 Lê Lợi Phường 1 Quận 1")
            -- Bê nguyên chuỗi gốc vào street_address để AI (PhoBERT) tự bóc tách sau này.
            v_street_address := TRIM(r.address_raw);
            v_postal_code := NULL;
        END IF;

        -- 6. CẬP NHẬT DATABASE
        UPDATE scm.address
        SET
            street_address = NULLIF(v_street_address, ''),
            postal_code = COALESCE(postal_code, v_postal_code), -- Giữ nguyên nếu đã có, hoặc update từ raw
            is_standardized = true -- Đánh dấu đã chạy qua bộ lọc
        WHERE id = r.id;
        
        count_updated := count_updated + 1;
    END LOOP;
    
    RAISE NOTICE 'Hoàn tất! Đã bóc tách lõi đường (street_address) cho % dòng.', count_updated;
END;
$function$
;
