"""
Export noise profiles sang JSON cho Google Colab.

Usage:
    python scripts/colab/export_noise_profiles.py --output noise_profiles.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.ai.noise_profiles import NOISE_PROFILES


def export_noise_profiles(output_path: str):
    """Export NOISE_PROFILES sang JSON."""
    
    print(f"Exporting {len(NOISE_PROFILES)} noise profiles...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(NOISE_PROFILES, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Exported to {output_path}")
    
    # Verify
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    
    print(f"✓ Verified: {len(loaded)} profiles")
    for profile_name in loaded.keys():
        print(f"  - {profile_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export noise profiles to JSON")
    parser.add_argument("--output", type=str, default="noise_profiles.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    export_noise_profiles(args.output)
