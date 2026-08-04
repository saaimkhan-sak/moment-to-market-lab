"""Archive and validate a GDELT GKG BigQuery daily-volume CSV export."""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import shutil
import uuid

from common import ROOT, now_utc, write_json
from analysis_window import ANALYSIS_START, ANALYSIS_END

START = date.fromisoformat(ANALYSIS_START)
END = date.fromisoformat(ANALYSIS_END)
REQUIRED_COLUMNS = {
    "mapping_id", "club_id", "entity_id", "entity_label", "date_utc",
    "article_count", "daily_gkg_web_article_count",
}


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_keys() -> tuple[set[tuple[str, str]], dict[str, dict]]:
    expected = set()
    mappings = {}
    with (ROOT / "config/entity_dictionary.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "confirmed":
                continue
            valid_from = max(date.fromisoformat(row.get("valid_from") or START.isoformat()), START)
            valid_to = min(date.fromisoformat(row.get("valid_to") or END.isoformat()), END)
            if valid_from > valid_to:
                continue
            mappings[row["mapping_id"]] = row
            cursor = valid_from
            while cursor <= valid_to:
                expected.add((row["mapping_id"], cursor.isoformat()))
                cursor += timedelta(days=1)
    return expected, mappings


def archive_source(source: Path, archive_dir: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = archive_dir / source.name
    if archived.exists() and checksum(archived) != checksum(source):
        raise ValueError(f"Conflicting GDELT export already archived: {archived}")
    if not archived.exists():
        shutil.copyfile(source, archived)
    return archived


def build_audit_candidates(audit_export: Path, stl_correction: Path, retrieved_at: str) -> list[dict]:
    with audit_export.open(newline="") as handle:
        candidates = list(csv.DictReader(handle))
    with stl_correction.open(newline="") as handle:
        stl_candidates = [row for row in csv.DictReader(handle) if row.get("audit_candidate_url")]
    stl_candidates.sort(key=lambda row: hashlib.sha256(row["audit_candidate_url"].encode()).hexdigest())
    for rank, row in enumerate(stl_candidates[:5], 1):
        candidates.append({
            "mapping_id": "STL-current",
            "club_id": "STL",
            "entity_id": "Q207735",
            "entity_label": "St. Louis Blues",
            "article_date": row["article_date"],
            "article_url": row["audit_candidate_url"],
            "source_common_name": "",
            "source_locations": "",
            "matched_all_names": "",
            "sample_rank": str(rank),
        })
    if len(candidates) != 170 or len({row["mapping_id"] for row in candidates}) != 34:
        raise ValueError("GDELT GKG audit must contain exactly five rows for each of 34 validity-aware mappings")
    if any(sum(row["mapping_id"] == mapping for row in candidates) != 5 for mapping in {r["mapping_id"] for r in candidates}):
        raise ValueError("GDELT GKG audit mapping sample sizes are not five")

    output_rows = []
    for row in sorted(candidates, key=lambda item: (item["club_id"], item["mapping_id"], int(item["sample_rank"]))):
        output_rows.append({
            "audit_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"gdelt-gkg|{row['mapping_id']}|{row['article_url']}")),
            **row,
            "query_method": "gkg_allnames_exact_validity_aware",
            "retrieved_at": retrieved_at,
            "reviewer": "",
            "is_true_club_match": "",
            "exclusion_reason": "",
            "reviewed_at": "",
            "review_basis": "",
        })
    output = ROOT / "data/evidence/gdelt_gkg_article_audit.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    return output_rows


def ingest(
    source: Path,
    job_id: str,
    bytes_processed: str,
    bytes_billed: str,
    duration: str,
    stl_correction_path: Path | None = None,
    audit_export_path: Path | None = None,
    audit_job_id: str | None = None,
    audit_bytes_processed: str | None = None,
    audit_duration: str | None = None,
    correction_job_id: str | None = None,
    correction_bytes_processed: str | None = None,
    correction_duration: str | None = None,
) -> Path:
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    archive_dir = ROOT / "data/raw/gdelt/gkg"
    archived = archive_source(source, archive_dir)

    with archived.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing GDELT export columns: {sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))}")
        raw_rows = list(reader)

    correction_archive = None
    audit_archive = None
    audit_candidates = []
    if stl_correction_path:
        correction_archive = archive_source(stl_correction_path, archive_dir)
        with correction_archive.open(newline="") as handle:
            correction_rows = {row["article_date"]: row for row in csv.DictReader(handle)}
        if len(correction_rows) != 1018:
            raise ValueError(f"Expected 1,018 available St. Louis dates, found {len(correction_rows)}")
        for row in raw_rows:
            if row["mapping_id"] != "STL-current":
                continue
            correction = correction_rows.get(row["date_utc"])
            if correction:
                if row["daily_gkg_web_article_count"] and row["daily_gkg_web_article_count"] != correction["daily_gkg_web_article_count"]:
                    raise ValueError(f"St. Louis correction denominator mismatch on {row['date_utc']}")
                row["article_count"] = correction["article_count"]
                row["daily_gkg_web_article_count"] = correction["daily_gkg_web_article_count"]
            elif row["daily_gkg_web_article_count"]:
                raise ValueError(f"St. Louis correction unexpectedly missing available date {row['date_utc']}")
    if audit_export_path:
        if not correction_archive:
            raise ValueError("The GKG audit export requires the St. Louis correction export")
        audit_archive = archive_source(audit_export_path, archive_dir)

    expected, mappings = expected_keys()
    retrieved_at = now_utc()
    if audit_archive and correction_archive:
        audit_candidates = build_audit_candidates(audit_archive, correction_archive, retrieved_at)
    observed = set()
    curated = []
    missing_source_dates = set()
    missing_source_rows = 0
    for raw in raw_rows:
        key = (raw["mapping_id"], raw["date_utc"])
        if key in observed:
            raise ValueError(f"Duplicate GDELT mapping/date key: {key}")
        if key not in expected:
            raise ValueError(f"Unexpected GDELT mapping/date key: {key}")
        observed.add(key)
        mapping = mappings[raw["mapping_id"]]
        if raw["club_id"] != mapping["club_id"] or raw["entity_id"] != mapping["entity_id"]:
            raise ValueError(f"Entity mapping mismatch: {key}")
        article_count = int(raw["article_count"])
        denominator_text = raw["daily_gkg_web_article_count"].strip()
        if article_count < 0:
            raise ValueError(f"Invalid negative GDELT article count: {key}")

        row = {
            "club_id": raw["club_id"],
            "entity_id": raw["entity_id"],
            "mapping_id": raw["mapping_id"],
            "date_utc": raw["date_utc"].replace("-", ""),
            "channel": "gdelt_earned_media",
            "metric_name": "exact_name_article_observations",
            "project_or_platform": "GDELT GKG 2.1",
            "source_url": f"https://console.cloud.google.com/bigquery?project=rugged-research-448616-n3&j=bq:US:{job_id.split(':')[-1]}",
            "retrieved_at": retrieved_at,
            "unit": "distinct GKG web-source article URLs",
            "source_language": "unavailable_in_gkg_aggregate_export",
        }
        if not denominator_text:
            # A missing daily denominator means the upstream GKG partition had no
            # web records. It is not evidence that the club had zero coverage.
            if article_count != 0:
                raise ValueError(f"GDELT article count exists without a daily denominator: {key}")
            missing_source_dates.add(raw["date_utc"])
            missing_source_rows += 1
            row.update({
                "metric_value": None,
                "evidence_quality": "unavailable_source_partition_gap",
                "daily_gkg_web_article_count": None,
                "normalized_articles_per_100k": None,
                "unavailable_reason": "gdelt_gkg_no_web_records_for_date",
            })
        else:
            denominator = int(denominator_text)
            if denominator <= 0 or article_count > denominator:
                raise ValueError(f"Invalid GDELT count/denominator: {key}")
            row.update({
                "metric_value": article_count,
                "evidence_quality": "confirmed_exact_name_entity_extraction_pending_gkg_specific_precision_audit",
                "daily_gkg_web_article_count": denominator,
                "normalized_articles_per_100k": article_count / denominator * 100000,
            })
        curated.append(row)

    missing = sorted(expected - observed)
    if missing:
        raise ValueError(f"GDELT export is missing {len(missing)} mapping/date keys; first={missing[0]}")
    if len(curated) != len(expected):
        raise ValueError("GDELT export row count does not match validity-aware date spine")

    curated.sort(key=lambda row: (row["club_id"], row["mapping_id"], row["date_utc"]))
    write_json("data/curated/gdelt_attention_daily.json", curated)
    query_path = ROOT / "data/manifests/gdelt_gkg_daily_volume.sql"
    manifest = {
        "source_id": "gdelt-gkg-bigquery",
        "evidence_status": "confirmed_with_visible_source_gaps_pending_gkg_specific_precision_audit",
        "retrieved_at": retrieved_at,
        "source_table": "gdelt-bq.gdeltv2.gkg_partitioned",
        "source_documentation": "https://www.gdeltproject.org/data.html#googlebigquery",
        "raw_export_path": str(archived.relative_to(ROOT)),
        "raw_export_bytes": archived.stat().st_size,
        "raw_export_checksum": checksum(archived),
        "query_path": str(query_path.relative_to(ROOT)),
        "query_checksum": checksum(query_path),
        "job_id": job_id,
        "bytes_processed": bytes_processed,
        "bytes_billed": bytes_billed,
        "duration": duration,
        "maximum_bytes_billed": 150000000000,
        "supplemental_correction": ({
            "club_id": "STL",
            "reason": "dynamic_regex_period_escape_defect",
            "raw_export_path": str(correction_archive.relative_to(ROOT)),
            "raw_export_checksum": checksum(correction_archive),
            "query_path": "data/manifests/gdelt_gkg_stl_correction.sql",
            "query_checksum": checksum(ROOT / "data/manifests/gdelt_gkg_stl_correction.sql"),
            "job_id": correction_job_id,
            "bytes_processed": correction_bytes_processed,
            "duration": correction_duration,
        } if correction_archive else None),
        "precision_audit_sample": ({
            "raw_export_path": str(audit_archive.relative_to(ROOT)),
            "raw_export_checksum": checksum(audit_archive),
            "query_path": "data/manifests/gdelt_gkg_precision_audit.sql",
            "query_checksum": checksum(ROOT / "data/manifests/gdelt_gkg_precision_audit.sql"),
            "job_id": audit_job_id,
            "bytes_processed": audit_bytes_processed,
            "duration": audit_duration,
            "sample_rows": len(audit_candidates),
            "review_status": "pending_manual_review",
        } if audit_archive else None),
        "daily_rows": len(curated),
        "mapping_count": len({row["mapping_id"] for row in curated}),
        "club_identity_count": len({row["club_id"] for row in curated}),
        "date_min": min(row["date_utc"] for row in curated),
        "date_max": max(row["date_utc"] for row in curated),
        "zero_observation_rows": sum(row["metric_value"] == 0 for row in curated),
        "confirmed_rows": len(curated) - missing_source_rows,
        "missing_source_rows": missing_source_rows,
        "missing_source_dates": sorted(missing_source_dates),
        "missing_source_date_count": len(missing_source_dates),
        "limitations": [
            "AllNames is GDELT's extracted named-entity field, not full article text.",
            "The series measures article observations, not readership, sentiment, or fan behavior.",
            "GKG-specific article precision must pass the registered audit before quantified modeling.",
            "Dates with no GKG web records are retained as unavailable and are never converted to zero.",
        ],
    }
    return write_json("data/manifests/gdelt_gkg_acquisition.json", manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--bytes-processed", required=True)
    parser.add_argument("--bytes-billed", required=True)
    parser.add_argument("--duration", required=True)
    parser.add_argument("--stl-correction", type=Path)
    parser.add_argument("--audit-export", type=Path)
    parser.add_argument("--audit-job-id")
    parser.add_argument("--audit-bytes-processed")
    parser.add_argument("--audit-duration")
    parser.add_argument("--correction-job-id")
    parser.add_argument("--correction-bytes-processed")
    parser.add_argument("--correction-duration")
    args = parser.parse_args()
    print(ingest(
        args.csv_path, args.job_id, args.bytes_processed, args.bytes_billed, args.duration,
        stl_correction_path=args.stl_correction,
        audit_export_path=args.audit_export,
        audit_job_id=args.audit_job_id,
        audit_bytes_processed=args.audit_bytes_processed,
        audit_duration=args.audit_duration,
        correction_job_id=args.correction_job_id,
        correction_bytes_processed=args.correction_bytes_processed,
        correction_duration=args.correction_duration,
    ))


if __name__ == "__main__":
    main()
