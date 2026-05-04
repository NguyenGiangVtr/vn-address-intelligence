"""
generate_evidence.py
====================
Pipeline tạo evidence thật từ dữ liệu đã ghi trong database và sample artifacts có sẵn.

Nguồn dữ liệu:
1. `ath.training_history` cho lịch sử training PhoBERT
2. `ath.benchmark_model_baselines` cho benchmark baseline thật
3. `ath.training_datasets` và `prq.address_cleansing_queue` cho inventory dữ liệu
4. `evidence/ward_mapping_2025_samples.csv` cho sample mapping thật đã lưu sẵn

Cách chạy:
    python app/ai/generate_evidence.py --output reports/evidence_real
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import (  # noqa: E402
    AddressCleansingQueue,
    BenchmarkModelBaseline,
    SessionLocal,
    TrainingDataset,
    TrainingHistory,
    seed_training_metadata,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EvidenceGenerator")


@dataclass
class TrainingHistoryRow:
    version: str
    accuracy: float
    f1_score: float
    loss: float
    samples_count: int
    created_at: str | None
    notes: str | None
    source: str


@dataclass
class BenchmarkBaselineRow:
    model_key: str
    model_name: str
    f1: float
    throughput: float
    cost_per_million: float
    google_match: float
    sample_size: int
    notes: str | None
    source: str


@dataclass
class InventoryRow:
    bucket: str
    count: int
    detail: str
    source: str


def _dt_to_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class EvidenceGenerator:
    def __init__(self, output_dir: str = "reports/evidence_real") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _open_session(self):
        seed_training_metadata()
        return SessionLocal()

    def fetch_training_history(self) -> list[TrainingHistoryRow]:
        session = self._open_session()
        try:
            rows = (
                session.query(TrainingHistory)
                .order_by(TrainingHistory.created_at.asc(), TrainingHistory.id.asc())
                .all()
            )
            return [
                TrainingHistoryRow(
                    version=row.version or "unknown",
                    accuracy=float(row.accuracy or 0.0),
                    f1_score=float(row.f1_score or 0.0),
                    loss=float(row.loss or 0.0),
                    samples_count=int(row.samples_count or 0),
                    created_at=_dt_to_str(row.created_at),
                    notes=row.notes,
                    source="ath.training_history",
                )
                for row in rows
            ]
        finally:
            session.close()

    def fetch_benchmark_baselines(self) -> list[BenchmarkBaselineRow]:
        session = self._open_session()
        try:
            rows = session.query(BenchmarkModelBaseline).order_by(BenchmarkModelBaseline.id.asc()).all()
            return [
                BenchmarkBaselineRow(
                    model_key=row.model_key,
                    model_name=row.model_name,
                    f1=float(row.f1 or 0.0),
                    throughput=float(row.throughput or 0.0),
                    cost_per_million=float(row.cost_per_million or 0.0),
                    google_match=float(row.google_match or 0.0),
                    sample_size=int(row.sample_size or 0),
                    notes=row.notes,
                    source="ath.benchmark_model_baselines",
                )
                for row in rows
            ]
        finally:
            session.close()

    def fetch_inventory(self) -> list[InventoryRow]:
        session = self._open_session()
        try:
            inventory: list[InventoryRow] = []

            training_total = session.query(TrainingDataset).count()
            inventory.append(
                InventoryRow(
                    bucket="ath.training_datasets.total",
                    count=int(training_total),
                    detail="Tổng số mẫu huấn luyện đã lưu trong ath.training_datasets",
                    source="ath.training_datasets",
                )
            )

            noise_rows = (
                session.query(TrainingDataset.noise_level, func.count(TrainingDataset.id))
                .group_by(TrainingDataset.noise_level)
                .order_by(TrainingDataset.noise_level.asc())
                .all()
            )
            for noise_level, count in noise_rows:
                inventory.append(
                    InventoryRow(
                        bucket=f"ath.training_datasets.noise_level:{noise_level or 'unknown'}",
                        count=int(count or 0),
                        detail=f"Phân bổ theo noise_level = {noise_level or 'unknown'}",
                        source="ath.training_datasets",
                    )
                )

            queue_total = session.query(AddressCleansingQueue).count()
            inventory.append(
                InventoryRow(
                    bucket="prq.address_cleansing_queue.total",
                    count=int(queue_total),
                    detail="Tổng số bản ghi trong hàng đợi chuẩn hóa địa chỉ",
                    source="prq.address_cleansing_queue",
                )
            )

            queue_rows = (
                session.query(AddressCleansingQueue.processing_status, func.count(AddressCleansingQueue.id))
                .group_by(AddressCleansingQueue.processing_status)
                .order_by(AddressCleansingQueue.processing_status.asc())
                .all()
            )
            for status, count in queue_rows:
                inventory.append(
                    InventoryRow(
                        bucket=f"prq.address_cleansing_queue.status:{status or 'unknown'}",
                        count=int(count or 0),
                        detail=f"Phân bổ theo processing_status = {status or 'unknown'}",
                        source="prq.address_cleansing_queue",
                    )
                )

            return inventory
        finally:
            session.close()

    def fetch_ward_mapping_sample(self) -> list[dict[str, Any]]:
        sample_path = PROJECT_ROOT / "evidence" / "ward_mapping_2025_samples.csv"
        if not sample_path.exists():
            raise FileNotFoundError(f"Ward mapping sample not found: {sample_path}")

        normalized_rows: list[dict[str, Any]] = []
        with sample_path.open("r", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                summary = row.get("updated_note") or ""
                if not summary:
                    parts = [row.get("old_ward", ""), row.get("new_ward", "")]
                    summary = " -> ".join(part for part in parts if part)
                normalized_rows.append({
                    **row,
                    "mapping_summary": summary,
                })
        return normalized_rows

    def generate_phobert_training_evidence(self) -> list[TrainingHistoryRow]:
        logger.info("Fetching real training history from ath.training_history...")
        rows = self.fetch_training_history()
        if not rows:
            raise RuntimeError("No rows found in ath.training_history")

        csv_path = self.output_dir / f"phobert_training_history_{self.timestamp}.csv"
        _write_csv(csv_path, [asdict(row) for row in rows])
        logger.info("Saved training history: %s", csv_path)
        return rows

    def generate_benchmark_evidence(self) -> list[BenchmarkBaselineRow]:
        logger.info("Fetching real benchmark baselines from ath.benchmark_model_baselines...")
        rows = self.fetch_benchmark_baselines()
        if not rows:
            raise RuntimeError("No rows found in ath.benchmark_model_baselines")

        csv_path = self.output_dir / f"benchmark_baselines_{self.timestamp}.csv"
        _write_csv(csv_path, [asdict(row) for row in rows])
        logger.info("Saved benchmark baselines: %s", csv_path)
        return rows

    def generate_inventory_evidence(self) -> list[InventoryRow]:
        logger.info("Fetching real inventory counts from ath.training_datasets and prq.address_cleansing_queue...")
        rows = self.fetch_inventory()
        csv_path = self.output_dir / f"data_inventory_{self.timestamp}.csv"
        _write_csv(csv_path, [asdict(row) for row in rows])
        logger.info("Saved inventory evidence: %s", csv_path)
        return rows

    def generate_ward_mapping_evidence(self) -> list[dict[str, Any]]:
        logger.info("Loading real ward mapping sample evidence...")
        rows = self.fetch_ward_mapping_sample()
        csv_path = self.output_dir / f"ward_mapping_sample_{self.timestamp}.csv"
        _write_csv(csv_path, rows)
        logger.info("Saved ward mapping sample: %s", csv_path)
        return rows

    def _render_summary_markdown(
        self,
        training_rows: list[TrainingHistoryRow],
        benchmark_rows: list[BenchmarkBaselineRow],
        inventory_rows: list[InventoryRow],
        ward_rows: list[dict[str, Any]],
    ) -> str:
        latest_training = training_rows[-1]
        benchmark_by_key = {row.model_key: row for row in benchmark_rows}
        pho = benchmark_by_key.get("phobert")
        siamese = benchmark_by_key.get("siamese")
        llm = benchmark_by_key.get("llm")

        total_inventory = sum(row.count for row in inventory_rows)
        queue_total = sum(row.count for row in inventory_rows if row.bucket == "prq.address_cleansing_queue.total")
        training_total = sum(row.count for row in inventory_rows if row.bucket == "ath.training_datasets.total")

        ward_sample_count = len(ward_rows)
        ward_preview = ward_rows[:5]

        md = [
            "# REAL EVIDENCE REPORT",
            "",
            f"**Generated at:** {datetime.now().isoformat(timespec='seconds')}",
            "**Source truth:** database tables and existing sample artifacts",
            "",
            "---",
            "",
            "## 1. Training History",
            "",
            f"- Source: `ath.training_history`",
            f"- Records: {len(training_rows)}",
            f"- Latest version: {latest_training.version}",
            f"- Latest accuracy: {latest_training.accuracy:.2f}%",
            f"- Latest F1: {latest_training.f1_score:.2f}%",
            f"- Latest loss: {latest_training.loss:.3f}",
            f"- Latest samples: {latest_training.samples_count:,}",
            "",
            "### History",
            "",
            "| Version | Accuracy | F1 | Loss | Samples | Created At | Notes |",
            "|---|---:|---:|---:|---:|---|---|",
        ]

        for row in training_rows:
            md.append(
                f"| {row.version} | {row.accuracy:.2f}% | {row.f1_score:.2f}% | {row.loss:.3f} | {row.samples_count:,} | {row.created_at or ''} | {row.notes or ''} |"
            )

        md += [
            "",
            "## 2. Benchmark Baselines",
            "",
            f"- Source: `ath.benchmark_model_baselines`",
            f"- Records: {len(benchmark_rows)}",
            "",
            "| Model | F1 | Throughput | Cost / Million | Google Match | Sample Size | Notes |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]

        for row in benchmark_rows:
            md.append(
                f"| {row.model_name} | {row.f1:.2f}% | {row.throughput:.2f} | {row.cost_per_million:.2f} | {row.google_match:.2f}% | {row.sample_size:,} | {row.notes or ''} |"
            )

        md += [
            "",
            "## 3. Inventory Snapshot",
            "",
            f"- Total inventory rows: {len(inventory_rows)}",
            f"- Training datasets count: {training_total:,}",
            f"- Queue total: {queue_total:,}",
            f"- Aggregate counted records: {total_inventory:,}",
            "",
            "| Bucket | Count | Detail | Source |",
            "|---|---:|---|---|",
        ]

        for row in inventory_rows:
            md.append(f"| {row.bucket} | {row.count:,} | {row.detail} | {row.source} |")

        md += [
            "",
            "## 4. Ward Mapping Sample",
            "",
            f"- Source file: `evidence/ward_mapping_2025_samples.csv`",
            f"- Rows: {ward_sample_count}",
            "",
            "| mapping_summary |",
            "|---|",
        ]

        for row in ward_preview:
            md.append(f"| {row.get('mapping_summary', '')} |")

        md += [
            "",
            "## 5. Notes",
            "",
            "This report does not fabricate metrics. It is built only from live DB rows and existing sample artifacts.",
            f"PhoBERT baseline F1 from DB: {pho.f1:.2f}%" if pho else "PhoBERT baseline unavailable.",
            f"Siamese baseline throughput from DB: {siamese.throughput:.2f}" if siamese else "Siamese baseline unavailable.",
            f"LLM baseline throughput from DB: {llm.throughput:.2f}" if llm else "LLM baseline unavailable.",
        ]

        return "\n".join(md)

    def _render_html_report(
        self,
        training_rows: list[TrainingHistoryRow],
        benchmark_rows: list[BenchmarkBaselineRow],
        inventory_rows: list[InventoryRow],
        ward_rows: list[dict[str, Any]],
    ) -> str:
        latest_training = training_rows[-1]
        benchmark_lookup = {row.model_key: row for row in benchmark_rows}
        pho = benchmark_lookup.get("phobert")
        siamese = benchmark_lookup.get("siamese")
        llm = benchmark_lookup.get("llm")

        training_table = "".join(
            f"<tr><td>{row.version}</td><td>{row.accuracy:.2f}%</td><td>{row.f1_score:.2f}%</td><td>{row.loss:.3f}</td><td>{row.samples_count:,}</td><td>{row.created_at or ''}</td></tr>"
            for row in training_rows
        )

        benchmark_table = "".join(
            f"<tr><td>{row.model_name}</td><td>{row.f1:.2f}%</td><td>{row.throughput:.2f}</td><td>{row.cost_per_million:.2f}</td><td>{row.google_match:.2f}%</td><td>{row.sample_size:,}</td></tr>"
            for row in benchmark_rows
        )

        inventory_table = "".join(
            f"<tr><td>{row.bucket}</td><td>{row.count:,}</td><td>{row.detail}</td><td>{row.source}</td></tr>"
            for row in inventory_rows
        )

        ward_table = "".join(
            f"<tr><td>{row.get('mapping_summary', '')}</td></tr>"
            for row in ward_rows[:10]
        )

        return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Real Evidence Report</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; background: #f4f6f8; color: #1f2937; }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }}
.hero {{ background: linear-gradient(135deg, #0f172a, #1d4ed8); color: #fff; padding: 28px; border-radius: 18px; }}
.hero h1 {{ margin: 0 0 8px; font-size: 2rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-top: 18px; }}
.card {{ background: #fff; border-radius: 14px; padding: 18px; box-shadow: 0 8px 24px rgba(15,23,42,.08); }}
.section {{ margin-top: 22px; }}
.section h2 {{ margin: 0 0 12px; font-size: 1.25rem; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 24px rgba(15,23,42,.08); }}
th, td {{ text-align: left; padding: 12px 14px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
th {{ background: #e8eefc; }}
.muted {{ color: #6b7280; font-size: .95rem; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <h1>Real Evidence Report</h1>
    <div>Generated at {datetime.now().isoformat(timespec='seconds')}</div>
    <div class="muted" style="color:#dbeafe; margin-top:6px;">Built from live DB rows and existing sample artifacts only</div>
  </div>

  <div class="grid">
    <div class="card"><strong>Training records</strong><div class="muted">{len(training_rows)} rows from ath.training_history</div><div>Latest F1: {latest_training.f1_score:.2f}%</div></div>
    <div class="card"><strong>Benchmark baselines</strong><div class="muted">{len(benchmark_rows)} rows from ath.benchmark_model_baselines</div><div>PhoBERT throughput: {pho.throughput:.2f}</div></div>
    <div class="card"><strong>Inventory rows</strong><div class="muted">{len(inventory_rows)} rows from DB counts</div><div>Queue total: {sum(row.count for row in inventory_rows if row.bucket == 'prq.address_cleansing_queue.total'):,}</div></div>
    <div class="card"><strong>Ward sample</strong><div class="muted">{len(ward_rows)} rows from evidence/ward_mapping_2025_samples.csv</div><div>Preview rows normalized into a readable summary</div></div>
  </div>

  <div class="section">
    <h2>Training History</h2>
    <table>
      <tr><th>Version</th><th>Accuracy</th><th>F1</th><th>Loss</th><th>Samples</th><th>Created At</th></tr>
      {training_table}
    </table>
  </div>

  <div class="section">
    <h2>Benchmark Baselines</h2>
    <table>
      <tr><th>Model</th><th>F1</th><th>Throughput</th><th>Cost / Million</th><th>Google Match</th><th>Sample Size</th></tr>
      {benchmark_table}
    </table>
  </div>

  <div class="section">
    <h2>Inventory Counts</h2>
    <table>
      <tr><th>Bucket</th><th>Count</th><th>Detail</th><th>Source</th></tr>
      {inventory_table}
    </table>
  </div>

  <div class="section">
    <h2>Ward Mapping Sample</h2>
    <table>
            <tr><th>Mapping Summary</th></tr>
      {ward_table}
    </table>
  </div>

  <p class="muted" style="margin-top:16px;">PhoBERT DB F1: {pho.f1:.2f}% | Siamese DB throughput: {siamese.throughput:.2f} | LLM DB throughput: {llm.throughput:.2f}</p>
</div>
</body>
</html>"""

    def build(self) -> dict[str, Path]:
        logger.info("Starting real evidence generation")
        training_rows = self.generate_phobert_training_evidence()
        benchmark_rows = self.generate_benchmark_evidence()
        inventory_rows = self.generate_inventory_evidence()
        ward_rows = self.generate_ward_mapping_evidence()

        summary_text = self._render_summary_markdown(training_rows, benchmark_rows, inventory_rows, ward_rows)
        summary_path = self.output_dir / "evidence_summary.md"
        summary_path.write_text(summary_text, encoding="utf-8")

        html_text = self._render_html_report(training_rows, benchmark_rows, inventory_rows, ward_rows)
        html_path = self.output_dir / "evidence_report.html"
        html_path.write_text(html_text, encoding="utf-8")

        manifest_path = self.output_dir / f"evidence_manifest_{self.timestamp}.json"
        manifest = {
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "sourceTables": [
                "ath.training_history",
                "ath.benchmark_model_baselines",
                "ath.training_datasets",
                "prq.address_cleansing_queue",
                "evidence/ward_mapping_2025_samples.csv",
            ],
            "files": {
                "training_history": str((self.output_dir / f"phobert_training_history_{self.timestamp}.csv").as_posix()),
                "benchmark_baselines": str((self.output_dir / f"benchmark_baselines_{self.timestamp}.csv").as_posix()),
                "data_inventory": str((self.output_dir / f"data_inventory_{self.timestamp}.csv").as_posix()),
                "ward_mapping_sample": str((self.output_dir / f"ward_mapping_sample_{self.timestamp}.csv").as_posix()),
                "summary": str(summary_path.as_posix()),
                "html": str(html_path.as_posix()),
            },
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info("Real evidence generation completed")
        return {
            "summary": summary_path,
            "html": html_path,
            "manifest": manifest_path,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate real evidence files from DB-backed logs")
    parser.add_argument("--output", default="reports/evidence_real", help="Output directory")
    args = parser.parse_args()

    generator = EvidenceGenerator(output_dir=args.output)
    output_files = generator.build()

    logger.info("Output files:")
    for name, path in output_files.items():
        logger.info("  %s: %s", name, path)


if __name__ == "__main__":
    main()
