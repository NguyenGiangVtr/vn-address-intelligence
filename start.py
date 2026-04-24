import sys
import os

# Thêm thư mục dự án vào PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
vnai_dir = os.path.join(project_root, "vn_address_intelligence")
if vnai_dir not in sys.path:
    sys.path.append(vnai_dir)

if __name__ == "__main__":
    from vn_address_intelligence.main import cli
    cli()
