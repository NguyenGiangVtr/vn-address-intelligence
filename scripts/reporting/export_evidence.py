"""Legacy export wrapper that now emits the real evidence package.

This script used to export the old fake evidence bundle into `evidence/`.
It now delegates to `app.ai.generate_evidence.EvidenceGenerator` and writes
into `reports/evidence_real` by default.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai.generate_evidence import EvidenceGenerator  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the real evidence package")
    parser.add_argument("--output", default="reports/evidence_real", help="Output directory for the real evidence package")
    args = parser.parse_args()

    generator = EvidenceGenerator(output_dir=args.output)
    output_files = generator.build()

    print("Real evidence package generated:")
    for name, path in output_files.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
