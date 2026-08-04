"""Record the manual review of the deterministic raw-GKG supplement.

Every candidate was reviewed from its URL subject together with the GKG
AllNames context.  The original five-row audit remains intact.  Rows where the
club is merely in a standings list, syndicated related-content block, or
publisher navigation are retained as false matches.
"""
from __future__ import annotations

import csv
import json
import uuid

from common import ROOT, write_json


# Global sample ranks in the immutable, hash-ordered candidate sheet.
TRUE_RANKS = {
    1, 2, 5, 6, 10, 12, 18, 20,
    22, 23, 24, 26, 27, 31, 33, 34, 35, 36, 38, 39, 41,
    42, 44, 45, 47, 48, 53, 54, 56, 57, 59, 60, 61, 62,
    71, 72, 75, 79, 83, 87,
}
REVIEWED_AT = "2026-08-03"
REVIEWER = "Codex manual review"


def main() -> str:
    candidate_path = ROOT / "data/evidence/gdelt_gkg_archive_supplement_candidates.csv"
    candidates = list(csv.DictReader(candidate_path.open()))
    ranks = {int(row["sample_rank"]) for row in candidates}
    if len(candidates) != 87 or ranks != set(range(1, 88)):
        raise ValueError("Expected the registered 87-row deterministic archive supplement")

    for row in candidates:
        is_true = int(row["sample_rank"]) in TRUE_RANKS
        row["reviewer"] = REVIEWER
        row["is_true_club_match"] = "true" if is_true else "false"
        row["exclusion_reason"] = "" if is_true else (
            "URL subject is unrelated to the target club or the club appears only in incidental, standings, publisher-page, or related-content context"
        )
        row["reviewed_at"] = REVIEWED_AT
        row["review_basis"] = (
            "URL subject and GKG AllNames context establish a substantive article-context reference to the registered NHL club"
            if is_true else
            "URL subject and GKG AllNames context do not establish the club as a substantive article subject"
        )
    with candidate_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidates[0]))
        writer.writeheader()
        writer.writerows(candidates)

    audit_path = ROOT / "data/evidence/gdelt_gkg_article_audit.csv"
    audit_rows = list(csv.DictReader(audit_path.open()))
    fieldnames = list(audit_rows[0])
    for field in ("source_gkg_record_id", "source_archive_timestamp"):
        if field not in fieldnames:
            fieldnames.append(field)
    existing = {(row["club_id"], row["article_url"]) for row in audit_rows}
    manifest = json.loads((ROOT / "data/manifests/gdelt_gkg_archive_supplement.json").read_text())
    added = 0
    for row in candidates:
        key = (row["club_id"], row["article_url"])
        if key in existing:
            continue
        audit_rows.append({
            "audit_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"gkg-archive-supplement|{row['mapping_id']}|{row['article_url']}")),
            "mapping_id": row["mapping_id"],
            "club_id": row["club_id"],
            "entity_id": row["entity_id"],
            "entity_label": row["entity_label"],
            "article_date": f"{row['article_date'][:4]}-{row['article_date'][4:6]}-{row['article_date'][6:]}",
            "article_url": row["article_url"],
            "source_common_name": row["source_common_name"],
            "source_locations": row["source_locations"],
            "matched_all_names": row["matched_all_names"],
            "sample_rank": row["sample_rank"],
            "query_method": "gkg_raw_archive_exact_name_deterministic_supplement",
            "retrieved_at": manifest["created_at"],
            "reviewer": row["reviewer"],
            "is_true_club_match": row["is_true_club_match"],
            "exclusion_reason": row["exclusion_reason"],
            "reviewed_at": row["reviewed_at"],
            "review_basis": row["review_basis"],
            "source_gkg_record_id": row["source_gkg_record_id"],
            "source_archive_timestamp": row["source_archive_timestamp"],
        })
        existing.add(key)
        added += 1
    with audit_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)

    manifest["evidence_status"] = "manual_review_complete"
    manifest["reviewed_candidates"] = len(candidates)
    manifest["true_matches"] = sum(row["is_true_club_match"] == "true" for row in candidates)
    manifest["false_matches"] = sum(row["is_true_club_match"] == "false" for row in candidates)
    manifest["rows_added_to_canonical_audit"] = added
    manifest["reviewer"] = REVIEWER
    manifest["reviewed_at"] = REVIEWED_AT
    return str(write_json("data/manifests/gdelt_gkg_archive_supplement.json", manifest))


if __name__ == "__main__":
    print(main())
