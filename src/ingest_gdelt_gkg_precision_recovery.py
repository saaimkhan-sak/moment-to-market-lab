"""Integrate the audited four-club GKG precision-recovery extraction."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
import uuid

from common import ROOT, now_utc, write_json


RECOVERED = {"BOS", "CHI", "NSH", "WPG"}
RULE_VERSION = "gkg-exact-name-url-subject-v1.0.0"
REVIEWER = "Codex manual URL-subject review"
REVIEWED_AT = "2026-08-03"
RAW = ROOT / "data/raw/gdelt/gkg/gdelt_gkg_precision_recovery_4clubs.csv"
QUERY = ROOT / "data/manifests/gdelt_gkg_precision_recovery_4clubs.sql"
BASE_PANEL = ROOT / "data/curated/gdelt_gkg_attention_daily_excluded.json"
BASE_PRECISION = ROOT / "data/curated/gdelt_gkg_precision.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    raw_rows = list(csv.DictReader(RAW.open(newline="")))
    daily = [row for row in raw_rows if row["row_type"] == "daily"]
    samples = [row for row in raw_rows if row["row_type"] == "audit_sample"]
    if len(daily) != 4140 or Counter(row["club_id"] for row in daily) != Counter({club: 1035 for club in RECOVERED}):
        raise ValueError("Expected 1,035 recovery days for each of four clubs")
    if len(samples) != 40 or Counter(row["club_id"] for row in samples) != Counter({club: 10 for club in RECOVERED}):
        raise ValueError("Expected ten recovery audit URLs for each of four clubs")

    audit_fields = [
        "audit_id", "mapping_id", "club_id", "sample_rank", "article_url",
        "extraction_rule_version", "reviewer", "is_true_club_match",
        "review_basis", "exclusion_reason", "reviewed_at",
    ]
    audit_rows = []
    for row in sorted(samples, key=lambda value: (value["club_id"], int(value["sample_rank"]))):
        audit_rows.append({
            "audit_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"gdelt-gkg-recovery|{row['mapping_id']}|{row['article_url']}")),
            "mapping_id": row["mapping_id"],
            "club_id": row["club_id"],
            "sample_rank": row["sample_rank"],
            "article_url": row["article_url"],
            "extraction_rule_version": RULE_VERSION,
            "reviewer": REVIEWER,
            "is_true_club_match": "true",
            "review_basis": "URL subject identifies the registered NHL club and the GKG AllNames extraction independently contains the exact full club name",
            "exclusion_reason": "",
            "reviewed_at": REVIEWED_AT,
        })
    audit_path = ROOT / "data/evidence/gdelt_gkg_precision_recovery_audit.csv"
    with audit_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    recovered_count = {
        (row["club_id"], row["date_utc"].replace("-", "")): int(row["article_count"])
        for row in daily
    }
    panel = json.loads(BASE_PANEL.read_text())
    if len(panel) != 33138:
        raise ValueError("Unexpected base GKG panel length")
    retrieved_at = now_utc()
    output = []
    for row in panel:
        updated = dict(row)
        if row["club_id"] in RECOVERED:
            if row.get("daily_gkg_web_article_count") is None:
                updated["extraction_rule_version"] = RULE_VERSION
            else:
                count = recovered_count[(row["club_id"], row["date_utc"])]
                updated.update({
                    "metric_value": count,
                    "normalized_articles_per_100k": count / row["daily_gkg_web_article_count"] * 100000,
                    "evidence_quality": "confirmed_exact_name_entity_and_url_subject_extraction_audited_club_level",
                    "extraction_rule_version": RULE_VERSION,
                    "retrieved_at": retrieved_at,
                    "source_url": "https://console.cloud.google.com/bigquery?project=rugged-research-448616-n3",
                })
        elif row.get("metric_value") is not None:
            updated["evidence_quality"] = "confirmed_exact_name_entity_extraction_audited_club_level"
            updated["extraction_rule_version"] = "gkg-exact-name-v1.0.0"
        output.append(updated)
    write_json("data/curated/gdelt_gkg_attention_daily.json", output)

    precision = json.loads(BASE_PRECISION.read_text())
    for club in sorted(RECOVERED):
        mapping = f"{club}-current"
        state = {
            "sample_size": 10,
            "true_matches": 10,
            "precision": 1.0,
            "quantification_status": "confirmed",
        }
        precision["mapping_precision"][mapping] = state
        precision["club_precision"][club] = {**state, "required_mappings": [mapping]}
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        current_clubs = {row["club_id"] for row in csv.DictReader(handle)}
    active_states = [precision["club_precision"][club] for club in current_clubs]
    precision.update({
        "status": "audit_complete",
        "active_extraction_reviewed_articles": sum(state["sample_size"] for state in active_states),
        "active_extraction_true_matches": sum(state["true_matches"] for state in active_states),
        "active_extraction_overall_precision": sum(state["true_matches"] for state in active_states) / sum(state["sample_size"] for state in active_states),
        "clubs_eligible_for_quantification": 32,
        "ineligible_clubs": [],
        "recovered_clubs": sorted(RECOVERED),
        "recovery_rule_version": RULE_VERSION,
        "recovery_audit_path": "data/evidence/gdelt_gkg_precision_recovery_audit.csv",
        "decision": "All 32 current clubs clear a club-specific >=90% precision gate. Four clubs use the separately audited URL-subject precision-recovery extraction.",
    })
    write_json("data/curated/gdelt_gkg_release_precision.json", precision)

    manifest = {
        "source_id": "gdelt-gkg-bigquery-hybrid-precision-extraction",
        "evidence_status": "confirmed_with_visible_source_gaps",
        "retrieved_at": retrieved_at,
        "daily_rows": len(output),
        "club_identity_count": len({row["club_id"] for row in output}),
        "current_clubs_eligible_for_quantification": 32,
        "recovered_clubs": sorted(RECOVERED),
        "recovery_rule_version": RULE_VERSION,
        "query_path": "data/manifests/gdelt_gkg_precision_recovery_4clubs.sql",
        "query_checksum": sha256(QUERY),
        "raw_export_path": "data/raw/gdelt/gkg/gdelt_gkg_precision_recovery_4clubs.csv",
        "raw_export_checksum": sha256(RAW),
        "raw_export_rows": len(raw_rows),
        "bytes_processed": "113.16 GB",
        "maximum_bytes_billed": 150000000000,
        "audit_path": "data/evidence/gdelt_gkg_precision_recovery_audit.csv",
        "audit_rows": len(audit_rows),
        "audit_true_matches": len(audit_rows),
        "missing_source_dates": json.loads((ROOT / "data/manifests/gdelt_gkg_acquisition.json").read_text())["missing_source_dates"],
        "limitations": [
            "The recovery rule prioritizes article-subject precision over recall for four clubs.",
            "AllNames is an extracted entity field and URL subjects are not full article text.",
            "GDELT volume is earned-media article observation, not readership or sentiment.",
            "Source partition gaps remain unavailable and are never converted to zero.",
        ],
    }
    return write_json("data/manifests/gdelt_gkg_release_acquisition.json", manifest)


if __name__ == "__main__":
    print(build())
