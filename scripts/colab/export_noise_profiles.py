"""
Export noise profiles sang JSON cho Google Colab.

Usage:
    python scripts/colab/export_noise_profiles.py --output noise_profiles.json
"""

import argparse
import json


def export_noise_profiles(output_path: str):
    """Export noise profile definitions sang JSON."""
    
    # Noise profiles defined in scripts/experiments/supa_benchmark.py
    noise_profiles = {
        "SUP-1.0.0": {
            "name": "SUP-1.0.0",
            "description": "Standard noise: Common abbreviations, some slang, light typos",
            "parameters": {
                "prefix_prob": 0.40,
                "suffix_prob": 0.20,
                "abbreviate_prob": 0.65,
                "slang_prob": 0.30,
                "ime_error_prob": 0.15,
                "upper_case_prob": 0.05,
                "lower_case_prob": 0.05,
                "spacing_noise_prob": 0.25,
                "double_space_prob": 0.15
            },
            "prefixes": ["Gần ", "Đối diện ", "Khu vực ", "Chỗ ", "Ngay ", "Sau lưng ", ""],
            "suffixes": ["", " (liên hệ)", " - ghi chú", " (tầng 2)"]
        },
        "SUP-D2-1.0.0": {
            "name": "SUP-D2-1.0.0",
            "description": "High noise: Aggressive abbreviations, slang, severe typos, and NO ACCENTS",
            "parameters": {
                "prefix_prob": 0.60,
                "abbreviate_prob": 0.90,
                "slang_prob": 0.60,
                "transpose_prob": 0.50,
                "stutter_prob": 0.30,
                "strip_accents": True,
                "upper_case_prob": 0.15,
                "comma_spacing_prob": 0.60,
                "triple_space_prob": 0.30
            },
            "prefixes": ["Gần ", "Đối diện ", "Chỗ ", "Ngay ", "Sau lưng ", "Cạnh ", "Phía sau ", "Tầng trệt ", ""]
        }
    }
    
    print(f"Exporting {len(noise_profiles)} noise profiles...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(noise_profiles, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Exported to {output_path}")
    
    # Verify
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    
    print(f"[OK] Verified: {len(loaded)} profiles")
    for profile_name in loaded.keys():
        print(f"  - {profile_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export noise profiles to JSON")
    parser.add_argument("--output", type=str, default="colab_vnai/noise_profiles.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    export_noise_profiles(args.output)
