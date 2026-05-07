"""Load HF NER address dataset → prq.address_clean_corpus.

Phase 1.3 of the production playbook. Streams the
``dathuynh1108/ner-address-standard-dataset`` (or compatible) corpus, walks
``tokens`` + ``ner_tags`` to recover BIO spans, and inserts unique
(STREET, WARD, DISTRICT, PROVINCE) tuples into the corpus with
``source_type='HF_NER_DERIVED'``.

Usage:
    python scripts/data/load_hf_ner_to_corpus.py \
        --dataset dathuynh1108/ner-address-standard-dataset \
        --train-limit 50000 --test-limit 5000 --streaming

If ``--snapshot-dir`` is provided, reads ``train.jsonl`` / ``test.jsonl`` from
disk instead of hitting the HF Hub.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from itertools import islice
from pathlib import Path
from typing import Any, Iterable, Iterator

from sqlalchemy import text

from app.core.database import SessionLocal
from scripts.migration.migrate_ground_truth_to_clean_corpus import _extract_components

# Reuse the same HF→project label mapping as train_ner.py to stay consistent.
from app.ai.train_ner import HF_STANDARD_BIO_TO_PROJECT, HF_STANDARD_ID_TO_BIO

LOGGER = logging.getLogger("load_hf_ner_to_corpus")

# We only need the four "wide" components to compose a standardized address;
# FLOOR/ROOM are not part of the unique key requested by the playbook.
KEY_LABELS = ("STR", "WDS", "DST", "PRO")


def _tags_to_strings(raw_tags: list[Any], features) -> list[str]:
    """Convert int-encoded tags to BIO strings using ClassLabel feature when available."""
    class_label = getattr(getattr(features, "feature", None), "names", None)
    out: list[str] = []
    for t in raw_tags:
        if isinstance(t, int):
            if class_label is not None and 0 <= t < len(class_label):
                out.append(class_label[t])
            else:
                out.append(HF_STANDARD_ID_TO_BIO.get(t, "O"))
        else:
            out.append(str(t))
    return out


def _extract_spans(tokens: list[str], bio_tags: list[str]) -> dict[str, str]:
    """Aggregate contiguous BIO spans into a label→text map.

    For each label we keep the *first* occurrence in the sentence (HF dataset
    samples are short; multi-occurrence is rare).
    """
    spans: dict[str, str] = {}
    cur_label: str | None = None
    cur_tokens: list[str] = []

    def _flush() -> None:
        if cur_label and cur_tokens and cur_label not in spans:
            spans[cur_label] = " ".join(cur_tokens).strip()

    for tok, raw_tag in zip(tokens, bio_tags):
        mapped = HF_STANDARD_BIO_TO_PROJECT.get(raw_tag, "O")
        if mapped == "O":
            _flush()
            cur_label = None
            cur_tokens = []
            continue
        prefix, _, base = mapped.partition("-")
        if prefix == "B" or base != cur_label:
            _flush()
            cur_label = base
            cur_tokens = [tok]
        else:  # I-tag continuing same label
            cur_tokens.append(tok)
    _flush()
    return spans


def _iter_hf_records(
    dataset: str,
    split: str,
    limit: int,
    streaming: bool,
) -> Iterator[dict[str, Any]]:
    from datasets import load_dataset

    LOGGER.info("Loading HF %s split=%s limit=%d streaming=%s", dataset, split, limit, streaming)
    try:
        ds = load_dataset(dataset, split=split, streaming=streaming)
    except Exception as exc:  # pragma: no cover - network/HF issues
        if streaming:
            raise
        LOGGER.warning("HF load failed (%s); retrying with streaming=True", exc)
        ds = load_dataset(dataset, split=split, streaming=True)

    if hasattr(ds, "features"):
        features = getattr(ds, "features", {}).get("ner_tags")
    else:
        features = None

    if streaming:
        for ex in islice(ds, limit):
            yield {"tokens": ex.get("tokens"), "ner_tags": ex.get("ner_tags"), "_features": features}
    else:
        for i in range(min(limit, len(ds))):
            ex = ds[i]
            yield {"tokens": ex.get("tokens"), "ner_tags": ex.get("ner_tags"), "_features": features}


def _iter_snapshot_records(snapshot_dir: Path, split: str, limit: int) -> Iterator[dict[str, Any]]:
    path = snapshot_dir / f"{split}.jsonl"
    if not path.exists():
        LOGGER.warning("Snapshot file missing: %s", path)
        return
    with path.open("r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= limit:
                break
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield {"tokens": obj.get("tokens"), "ner_tags": obj.get("ner_tags"), "_features": None}


def _aggregate_unique_pairs(records: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Walk samples and aggregate unique (STR, WDS) pairs with majority DST/PRO context."""
    bucket: dict[tuple[str, str], dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    skipped = 0
    seen = 0

    for rec in records:
        tokens = rec.get("tokens") or []
        raw_tags = rec.get("ner_tags") or []
        features = rec.get("_features")
        if len(tokens) != len(raw_tags) or not tokens:
            skipped += 1
            continue
        seen += 1
        bio = _tags_to_strings(raw_tags, features) if features is not None else [
            (t if isinstance(t, str) else HF_STANDARD_ID_TO_BIO.get(t, "O")) for t in raw_tags
        ]
        spans = _extract_spans(tokens, bio)
        street = spans.get("STR", "").strip()
        ward = spans.get("WDS", "").strip()
        if not street or not ward:
            continue
        key = (street.lower(), ward.lower())
        bucket[key]["STR"][street] += 1
        bucket[key]["WDS"][ward] += 1
        for ctx_label in ("DST", "PRO"):
            v = spans.get(ctx_label, "").strip()
            if v:
                bucket[key][ctx_label][v] += 1

    LOGGER.info("HF samples seen=%d skipped=%d unique_pairs=%d", seen, skipped, len(bucket))

    out: list[dict[str, str]] = []
    for counters in bucket.values():
        row = {label: (counters[label].most_common(1)[0][0] if counters[label] else "") for label in KEY_LABELS}
        out.append(row)
    return out


def _compose_address(row: dict[str, str]) -> str:
    parts = [row[k] for k in KEY_LABELS if row.get(k)]
    return ", ".join(p.strip() for p in parts if p and p.strip())


def upsert_corpus(
    rows: list[dict[str, str]],
    admin_epoch: str = "2025",
    quality_score: float = 0.85,
    batch_size: int = 500,
) -> tuple[int, int, int]:
    """Idempotent upsert into prq.address_clean_corpus.

    Returns (inserted, updated, skipped).
    """
    if not rows:
        return (0, 0, 0)

    upsert_sql = text(
        """
        INSERT INTO prq.address_clean_corpus (
            standardized_address,
            address_components,
            source_type,
            source_id,
            quality_score,
            province_name,
            district_name,
            ward_name,
            admin_epoch,
            admin_version,
            created_by
        ) VALUES (
            :standardized_address,
            CAST(:address_components AS jsonb),
            'HF_NER_DERIVED',
            NULL,
            :quality_score,
            :province_name,
            :district_name,
            :ward_name,
            :admin_epoch,
            2,
            'HF_IMPORT'
        )
        ON CONFLICT (standardized_address, admin_epoch, source_type)
        DO UPDATE SET
            address_components = EXCLUDED.address_components,
            quality_score = GREATEST(prq.address_clean_corpus.quality_score, EXCLUDED.quality_score),
            province_name = COALESCE(EXCLUDED.province_name, prq.address_clean_corpus.province_name),
            district_name = COALESCE(EXCLUDED.district_name, prq.address_clean_corpus.district_name),
            ward_name = COALESCE(EXCLUDED.ward_name, prq.address_clean_corpus.ward_name),
            updated_at = now()
        RETURNING (xmax = 0) AS inserted_flag
        """
    )

    inserted = updated = skipped = 0
    session = SessionLocal()
    try:
        batch_buf = 0
        for row in rows:
            standardized = _compose_address(row)
            if not standardized or len(standardized) < 6:
                skipped += 1
                continue
            comps = _extract_components(
                standardized,
                province=row.get("PRO"),
                district=row.get("DST"),
                ward=row.get("WDS"),
            )
            # Make sure STR/WDS reflect the spans we extracted (override the heuristic).
            if row.get("STR"):
                comps["STR"] = row["STR"]
            if row.get("WDS"):
                comps["WDS"] = row["WDS"]
            try:
                flag = session.execute(
                    upsert_sql,
                    {
                        "standardized_address": standardized,
                        "address_components": json.dumps(comps, ensure_ascii=False),
                        "quality_score": quality_score,
                        "province_name": row.get("PRO") or None,
                        "district_name": row.get("DST") or None,
                        "ward_name": row.get("WDS") or None,
                        "admin_epoch": admin_epoch,
                    },
                ).scalar()
            except Exception as exc:
                LOGGER.warning("Upsert failed for %r: %s", standardized[:80], exc)
                session.rollback()
                skipped += 1
                continue
            if flag:
                inserted += 1
            else:
                updated += 1
            batch_buf += 1
            if batch_buf >= batch_size:
                session.commit()
                batch_buf = 0
        session.commit()
    finally:
        session.close()
    return inserted, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Load HF NER dataset into prq.address_clean_corpus")
    parser.add_argument("--dataset", default="dathuynh1108/ner-address-standard-dataset")
    parser.add_argument("--train-limit", type=int, default=50000)
    parser.add_argument("--test-limit", type=int, default=5000)
    parser.add_argument("--streaming", action="store_true", help="Force HF streaming mode")
    parser.add_argument(
        "--snapshot-dir",
        default=None,
        help="Optional: read train.jsonl/test.jsonl from a previous snapshot folder",
    )
    parser.add_argument("--admin-epoch", default="2025")
    parser.add_argument("--quality-score", type=float, default=0.85)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="Aggregate but skip DB upsert")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.snapshot_dir:
        snap = Path(args.snapshot_dir)
        records = list(_iter_snapshot_records(snap, "train", args.train_limit)) + list(
            _iter_snapshot_records(snap, "test", args.test_limit)
        )
    else:
        records = list(_iter_hf_records(args.dataset, "train", args.train_limit, args.streaming)) + list(
            _iter_hf_records(args.dataset, "test", args.test_limit, args.streaming)
        )

    rows = _aggregate_unique_pairs(records)
    LOGGER.info("Aggregated %d unique (street, ward) pairs", len(rows))

    if args.dry_run:
        for r in rows[:5]:
            LOGGER.info("sample: %s", _compose_address(r))
        LOGGER.info("Dry-run; skipping DB upsert")
        return

    inserted, updated, skipped = upsert_corpus(
        rows,
        admin_epoch=args.admin_epoch,
        quality_score=args.quality_score,
        batch_size=args.batch_size,
    )
    LOGGER.info("Upsert done | inserted=%d updated=%d skipped=%d", inserted, updated, skipped)


if __name__ == "__main__":
    main()
