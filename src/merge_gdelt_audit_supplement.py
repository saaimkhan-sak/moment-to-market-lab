"""Merge fully reviewed validity-query supplement rows into the DOC audit."""
from __future__ import annotations

import csv

from common import ROOT
from validate_gdelt_matches import build as rebuild_precision


def build():
    candidate_path = ROOT / "data/evidence/gdelt_query_audit_supplement_candidates.csv"
    audit_path = ROOT / "data/evidence/gdelt_article_audit.csv"
    with candidate_path.open(newline="") as handle:
        supplements = list(csv.DictReader(handle))
    if len(supplements) != 10:
        raise ValueError(f"Expected ten supplement rows, found {len(supplements)}")
    if any(not row.get("reviewer") or row.get("is_true_club_match") not in {"true", "false"} or not row.get("reviewed_at") or not row.get("review_basis") for row in supplements):
        raise ValueError("Every supplement row must be manually reviewed before merge")
    with audit_path.open(newline="") as handle:
        existing = list(csv.DictReader(handle))
    existing_ids = {row["audit_id"] for row in existing}
    merged = existing + [row for row in supplements if row["audit_id"] not in existing_ids]
    merged.sort(key=lambda row: (row["club_id"], row["query"], row["audit_id"]))
    with audit_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(existing[0]))
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in writer.fieldnames} for row in merged)
    return rebuild_precision()


if __name__ == "__main__":
    print(build())
