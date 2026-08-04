"""Archive and validate the 2015–2026 precision-qualified GDELT GKG export."""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import shutil

from analysis_window import ANALYSIS_END, ANALYSIS_START
from common import ROOT, now_utc, write_json

REQUIRED = {"mapping_id", "club_id", "entity_id", "entity_label", "date_utc", "article_count", "daily_gkg_web_article_count"}
RECOVERY_MAPPINGS = {"BOS-current", "CHI-current", "NSH-current", "WPG-current"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected() -> tuple[set[tuple[str, str]], dict[str, dict]]:
    start = date.fromisoformat(ANALYSIS_START)
    end = date.fromisoformat(ANALYSIS_END)
    keys = set()
    mappings = {}
    with (ROOT / "config/entity_dictionary.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "confirmed":
                continue
            valid_from = max(date.fromisoformat(row.get("valid_from") or ANALYSIS_START), start)
            valid_to = min(date.fromisoformat(row.get("valid_to") or ANALYSIS_END), end)
            if valid_from > valid_to:
                continue
            mappings[row["mapping_id"]] = row
            cursor = valid_from
            while cursor <= valid_to:
                keys.add((row["mapping_id"], cursor.isoformat()))
                cursor += timedelta(days=1)
    return keys, mappings


def ingest(source: Path, job_id: str, bytes_processed: str, bytes_billed: str, duration: str):
    source = source.expanduser().resolve()
    archive_dir = ROOT / "data/raw/gdelt/gkg_historical_release"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / source.name
    if archived.exists() and sha256(archived) != sha256(source):
        raise ValueError(f"Conflicting archived export: {archived}")
    if not archived.exists():
        shutil.copyfile(source, archived)
    with archived.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns: {sorted(REQUIRED - set(reader.fieldnames or []))}")
        raw = list(reader)

    expected_keys, mappings = expected()
    observed = set()
    missing_dates = set()
    rows = []
    retrieved_at = now_utc()
    for item in raw:
        key = (item["mapping_id"], item["date_utc"])
        if key in observed or key not in expected_keys:
            raise ValueError(f"Duplicate or unexpected key: {key}")
        observed.add(key)
        mapping = mappings[item["mapping_id"]]
        if item["club_id"] != mapping["club_id"] or item["entity_id"] != mapping["entity_id"]:
            raise ValueError(f"Mapping mismatch: {key}")
        count = int(item["article_count"])
        denominator_text = item["daily_gkg_web_article_count"].strip()
        row = {
            "club_id": item["club_id"],
            "entity_id": item["entity_id"],
            "mapping_id": item["mapping_id"],
            "date_utc": item["date_utc"].replace("-", ""),
            "channel": "gdelt_earned_media",
            "metric_name": "precision_qualified_article_observations",
            "project_or_platform": "GDELT GKG 2.1",
            "source_url": f"https://console.cloud.google.com/bigquery?project=rugged-research-448616-n3&j=bq:US:{job_id.split(':')[-1]}",
            "retrieved_at": retrieved_at,
            "unit": "distinct GKG web-source article URLs",
            "extraction_rule": "exact_allnames_plus_club_url_subject" if item["mapping_id"] in RECOVERY_MAPPINGS else "exact_allnames",
        }
        if not denominator_text:
            if count != 0:
                raise ValueError(f"Count without denominator: {key}")
            missing_dates.add(item["date_utc"])
            row.update({
                "metric_value": None,
                "daily_gkg_web_article_count": None,
                "normalized_articles_per_100k": None,
                "evidence_quality": "unavailable_source_partition_gap",
                "unavailable_reason": "gdelt_gkg_no_web_records_for_date",
            })
        else:
            denominator = int(denominator_text)
            if count < 0 or denominator <= 0 or count > denominator:
                raise ValueError(f"Invalid count or denominator: {key}")
            row.update({
                "metric_value": count,
                "daily_gkg_web_article_count": denominator,
                "normalized_articles_per_100k": count / denominator * 100000,
                "evidence_quality": "confirmed_precision_qualified_gkg_extraction",
            })
        rows.append(row)
    missing_keys = expected_keys - observed
    if missing_keys:
        raise ValueError(f"Missing {len(missing_keys)} mapping/date keys; first={sorted(missing_keys)[0]}")
    rows.sort(key=lambda row: (row["club_id"], row["mapping_id"], row["date_utc"]))
    write_json("data/curated/gdelt_gkg_attention_daily.json", rows)
    precision = json.loads((ROOT / "data/curated/gdelt_gkg_release_precision.json").read_text())
    if precision.get("clubs_eligible_for_quantification") != 32:
        raise ValueError("The registered GKG extraction audit does not qualify all 32 current clubs")
    query = ROOT / "data/manifests/gdelt_gkg_daily_volume.sql"
    return write_json("data/manifests/gdelt_gkg_release_acquisition.json", {
        "source_id": "gdelt-gkg-bigquery-historical-release",
        "evidence_status": "confirmed_with_visible_source_gaps" if missing_dates else "confirmed",
        "retrieved_at": retrieved_at,
        "source_table": "gdelt-bq.gdeltv2.gkg_partitioned",
        "source_documentation": "https://www.gdeltproject.org/data.html#googlebigquery",
        "raw_export_path": str(archived.relative_to(ROOT)),
        "raw_export_checksum": sha256(archived),
        "query_path": str(query.relative_to(ROOT)),
        "query_checksum": sha256(query),
        "job_id": job_id,
        "bytes_processed": bytes_processed,
        "bytes_billed": bytes_billed,
        "duration": duration,
        "daily_rows": len(rows),
        "mapping_count": len({row["mapping_id"] for row in rows}),
        "club_identity_count": len({row["club_id"] for row in rows}),
        "current_clubs_eligible_for_quantification": precision["clubs_eligible_for_quantification"],
        "active_extraction_reviewed_articles": precision["active_extraction_reviewed_articles"],
        "recovered_clubs": ["BOS", "CHI", "NSH", "WPG"],
        "date_min": min(row["date_utc"] for row in rows),
        "date_max": max(row["date_utc"] for row in rows),
        "missing_source_dates": sorted(missing_dates),
        "missing_source_date_count": len(missing_dates),
        "limitations": [
            "AllNames is GDELT's extracted named-entity field, not full article text.",
            "Boston, Chicago, Nashville, and Winnipeg use the separately audited exact-name-plus-club-URL-subject extraction.",
            "The series measures earned-media article observations, not readership, sentiment, or fan behavior.",
            "Dates without a source denominator remain unavailable rather than zero.",
        ],
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--bytes-processed", required=True)
    parser.add_argument("--bytes-billed", required=True)
    parser.add_argument("--duration", required=True)
    args = parser.parse_args()
    print(ingest(args.csv_path, args.job_id, args.bytes_processed, args.bytes_billed, args.duration))


if __name__ == "__main__":
    main()
