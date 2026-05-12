"""
Đọc tài liệu Markdown trong thư mục docs/ của repo — một nguồn duy nhất cho UI và Git.

Đường dẫn API có prefix `/api/repo-docs` để không trùng Swagger UI (`/api/docs`).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.paths import docs_dir

router = APIRouter(prefix="/repo-docs", tags=["Repository docs"])

_DOCS_ROOT = docs_dir().resolve()

# Không đưa thư mục private hoặc file quá lớn không phải tài liệu đọc được vào browse.
_EXCLUDED_PATH_PREFIXES: tuple[str, ...] = (
    "private/",
    "__pycache__/",
)


def _is_under_docs(path: Path) -> bool:
    try:
        path.resolve().relative_to(_DOCS_ROOT)
    except ValueError:
        return False
    return True


def _safe_resolve_md(relative_path: str) -> Path:
    raw = (relative_path or "").replace("\\", "/").strip().lstrip("/")
    if not raw:
        raise HTTPException(status_code=400, detail="Thiếu đường dẫn")
    if not raw.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Đường dẫn phải là tệp .md")

    segments = raw.split("/")
    if any(s in ("..", "") for s in segments):
        raise HTTPException(status_code=400, detail="Đường dẫn không hợp lệ")

    target = (_DOCS_ROOT / Path(*segments)).resolve()
    if not _is_under_docs(target):
        raise HTTPException(status_code=400, detail="Đường dẫn không nằm trong docs/")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp")
    if target.suffix.lower() != ".md":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tệp .md")

    path_posix = target.relative_to(_DOCS_ROOT).as_posix()
    if any(
        path_posix == p.rstrip("/") or path_posix.startswith(f"{p.rstrip('/')}/")
        for p in _EXCLUDED_PATH_PREFIXES
    ):
        raise HTTPException(status_code=403, detail="Đường dẫn không được phép")

    return target


def _first_heading_title(md_path: Path, fallback: str) -> str:
    try:
        with md_path.open(encoding="utf-8") as fh:
            for line in fh:
                s = line.strip()
                if s.startswith("#"):
                    return s.lstrip("#").strip() or fallback
                if s:
                    break
    except OSError:
        pass
    return fallback


@router.get("/list", summary="Danh sách file .md trong docs/")
def list_md_documents():
    """Trả về đường dẫn POSIX tương đối và tiêu đề (từ dòng heading đầu tiên)."""
    if not _DOCS_ROOT.is_dir():
        return {"documents": [], "warning": "Thư mục docs/ không tồn tại"}

    docs: list[dict[str, str]] = []
    for md in sorted(_DOCS_ROOT.rglob("*.md")):
        rel_posix = md.relative_to(_DOCS_ROOT).as_posix()
        rl = rel_posix.lower()
        if rl.startswith("__pycache__/"):
            continue
        if any(rel_posix.startswith(p) or f"/{p}" in rel_posix for p in _EXCLUDED_PATH_PREFIXES):
            continue

        docs.append(
            {
                "path": rel_posix,
                "title": _first_heading_title(md_path=md, fallback=rel_posix),
                "folder": md.parent.relative_to(_DOCS_ROOT).as_posix(),
            }
        )

    docs.sort(key=lambda x: x["path"].lower())
    return {"documents": docs}


@router.get("/raw/{path:path}", summary="Nội dung Markdown thô")
def raw_markdown(path: str):
    target = _safe_resolve_md(path)
    body = target.read_text(encoding="utf-8")
    return PlainTextResponse(body, media_type="text/markdown; charset=utf-8")


@router.head("/raw/{path:path}", summary="Kiểm tra file .md có tồn tại", include_in_schema=False)
def head_markdown(path: str):
    _safe_resolve_md(path)
    return PlainTextResponse("", media_type="text/markdown; charset=utf-8")
