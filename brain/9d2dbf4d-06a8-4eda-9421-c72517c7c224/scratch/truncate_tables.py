# from app.core.database import engine
# from sqlalchemy import text

# with engine.begin() as conn:
#     conn.execute(text("TRUNCATE TABLE mat.ward_mapping RESTART IDENTITY CASCADE"))
#     conn.execute(text("TRUNCATE TABLE mat.ward RESTART IDENTITY CASCADE"))
#     conn.execute(text("TRUNCATE TABLE mat.district RESTART IDENTITY CASCADE"))
#     conn.execute(text("TRUNCATE TABLE mat.province RESTART IDENTITY CASCADE"))
#     print("Truncated all tables.")
from app.core.database import engine
from sqlalchemy import text

# Sử dụng engine.begin() để tự động commit nếu không có lỗi
with engine.begin() as conn:
    # RESTART IDENTITY: Tự động reset sequence (ID) về 1
    # CASCADE: Tự động xóa các bảng con có liên kết khóa ngoại (Foreign Key)
    conn.execute(text("TRUNCATE TABLE mat.ward_mapping RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE TABLE mat.ward RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE TABLE mat.district RESTART IDENTITY CASCADE"))
    conn.execute(text("TRUNCATE TABLE mat.province RESTART IDENTITY CASCADE"))
    
    print("Đã xóa toàn bộ dữ liệu và reset ID về 1.")