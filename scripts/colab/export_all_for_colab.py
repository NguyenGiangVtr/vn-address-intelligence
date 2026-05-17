"""
Export tất cả files cần thiết cho Google Colab vào folder colab_vnai/.

Usage:
    python scripts/colab/export_all_for_colab.py
"""

import os
import shutil
from pathlib import Path

# Import các export functions
import sys
sys.path.insert(0, str(Path(__file__).parent))

from export_ground_truth_sqlite import export_ground_truth_sqlite
from export_noise_profiles import export_noise_profiles
from export_src_for_colab import export_src_zip


def export_all():
    """Export tất cả files vào folder colab_vnai/."""
    
    # Tạo folder colab_vnai
    output_dir = Path("colab_vnai")
    output_dir.mkdir(exist_ok=True)
    print(f"[OK] Created folder: {output_dir}/\n")
    
    # 1. Export ground_truth.db
    print("=" * 60)
    print("1/4: Exporting ground_truth.db...")
    print("=" * 60)
    export_ground_truth_sqlite(15000, str(output_dir / "ground_truth.db"))
    
    # 2. Export noise_profiles.json
    print("\n" + "=" * 60)
    print("2/4: Exporting noise_profiles.json...")
    print("=" * 60)
    export_noise_profiles(str(output_dir / "noise_profiles.json"))
    
    # 3. Export vnai_src.zip
    print("\n" + "=" * 60)
    print("3/4: Exporting vnai_src.zip...")
    print("=" * 60)
    export_src_zip(str(output_dir / "vnai_src.zip"))
    
    # 4. Copy notebook
    print("\n" + "=" * 60)
    print("4/4: Copying vnai_ablation_study.ipynb...")
    print("=" * 60)
    notebook_src = Path(__file__).parent / "vnai_ablation_study.ipynb"
    notebook_dst = output_dir / "vnai_ablation_study.ipynb"
    shutil.copy(notebook_src, notebook_dst)
    print(f"[OK] Copied to {notebook_dst}")
    
    # Summary
    print("\n" + "=" * 60)
    print("EXPORT COMPLETED")
    print("=" * 60)
    
    total_size = sum(f.stat().st_size for f in output_dir.iterdir() if f.is_file())
    print(f"\nFolder: {output_dir}/")
    print(f"Files: {len(list(output_dir.iterdir()))}")
    print(f"Total size: {total_size / (1024 * 1024):.2f} MB")
    
    print("\nFiles ready for upload:")
    for f in sorted(output_dir.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            if size_mb < 0.1:
                size_str = f"{f.stat().st_size / 1024:.1f} KB"
            else:
                size_str = f"{size_mb:.2f} MB"
            print(f"  - {f.name} ({size_str})")
    
    print("\nNext step:")
    print("  Upload folder 'colab_vnai/' to Google Drive at /MyDrive/")


if __name__ == "__main__":
    export_all()
