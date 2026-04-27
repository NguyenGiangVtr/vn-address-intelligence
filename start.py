import sys
import os

# Thêm thư mục dự án vào PYTHONPATH
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve-ui":
        import uvicorn
        uvicorn.run("app.api.server:app", host="0.0.0.0", port=8081, reload=True)
    else:
        from app.main import cli
        cli()
