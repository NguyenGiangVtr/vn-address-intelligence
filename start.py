import sys
import os

# PYTHONPATH: src layout → .../src contains package `app`; else repo root (legacy).
project_root = os.path.dirname(os.path.abspath(__file__))
_src = os.path.join(project_root, "src")
if os.path.isfile(os.path.join(_src, "app", "__init__.py")):
    if _src not in sys.path:
        sys.path.insert(0, _src)
elif project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve-ui":
        import uvicorn
        uvicorn.run("app.api.server:app", host="0.0.0.0", port=8081, reload=False)
    else:
        from app.main import cli
        cli()
