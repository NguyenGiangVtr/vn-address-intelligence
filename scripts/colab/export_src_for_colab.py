"""
Export src code sang ZIP cho Google Colab.

Usage:
    python scripts/colab/export_src_for_colab.py --output vnai_src.zip
"""

import argparse
import zipfile
from pathlib import Path


def export_src_zip(output_path: str):
    """Export src directory to ZIP, excluding unnecessary files."""
    
    src_dir = Path(__file__).parent.parent.parent / "src"
    
    if not src_dir.exists():
        print(f"[ERROR] Source directory not found: {src_dir}")
        return
    
    print(f"Creating ZIP from {src_dir}...")
    
    # Files to exclude
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache",
        ".mypy_cache",
        "*.egg-info",
        ".DS_Store",
    ]
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0
        for file_path in src_dir.rglob("*"):
            if file_path.is_file():
                # Check if should exclude
                should_exclude = False
                for pattern in exclude_patterns:
                    if pattern.startswith("*"):
                        if file_path.name.endswith(pattern[1:]):
                            should_exclude = True
                            break
                    elif pattern in str(file_path):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    arcname = file_path.relative_to(src_dir.parent)
                    zipf.write(file_path, arcname)
                    file_count += 1
        
        print(f"[OK] Added {file_count} files to ZIP")
    
    # Check size
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"[OK] Created {output_path} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export src to ZIP for Colab")
    parser.add_argument("--output", type=str, default="colab_vnai/vnai_src.zip", help="Output ZIP file")
    
    args = parser.parse_args()
    
    export_src_zip(args.output)
