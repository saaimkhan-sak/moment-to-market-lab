"""Materialize the completed manual review of the GKG audit samples.

The five false-positive IDs below were identified by reviewing every sampled
URL together with the GKG AllNames context. They are unrelated news articles in
which the club entity came from publisher page chrome, related-content modules,
or other non-article context. Keeping these failures visible is the reason the
GKG panel remains a diagnostic rather than silently replacing the DOC panel.
"""
from __future__ import annotations

from collections import defaultdict
import csv
import json

from common import ROOT, write_json


FALSE_MATCHES = {
    "e088997a-60d9-5421-bfa9-2df357851606": "unrelated Eurovision article; Boston Bruins entity is publisher-page contamination",
    "7e5f85ce-d678-5c42-b8a5-e34f69efcd32": "unrelated political article; Chicago Blackhawks entity is publisher-page contamination",
    "c1eb19b9-edb3-5b9a-94cc-e7c4c533ecc1": "unrelated homicide article; Nashville Predators entity is publisher-page contamination",
    "90d72ef6-f2ee-5159-99db-003da05ef85e": "unrelated missing-children article; Winnipeg Jets entity is publisher-page contamination",
    "b576683f-b1e2-546f-ad52-260b0a9c17b4": "unrelated international-affairs opinion article; Winnipeg Jets entity is publisher-page contamination",
}
REVIEWED_AT = "2026-08-03"
REVIEWER = "Codex manual review"


def precision(values: list[bool]) -> float:
    return sum(values) / len(values)


def build():
    path = ROOT / "data/evidence/gdelt_gkg_article_audit.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 170 or len({row["mapping_id"] for row in rows}) != 34:
        raise ValueError("Expected at least the registered 170-row, 34-mapping GKG audit sample")
    if not set(FALSE_MATCHES).issubset({row["audit_id"] for row in rows}):
        raise ValueError("A registered false-positive audit row is missing")

    by_mapping = defaultdict(list)
    by_club = defaultdict(list)
    for row in rows:
        false_reason = FALSE_MATCHES.get(row["audit_id"])
        if row.get("is_true_club_match") in {"true", "false"} and false_reason is None:
            value = row["is_true_club_match"] == "true"
        else:
            value = false_reason is None
            row["reviewer"] = REVIEWER
            row["is_true_club_match"] = "true" if value else "false"
            row["exclusion_reason"] = false_reason or ""
            row["reviewed_at"] = REVIEWED_AT
            row["review_basis"] = (
                "URL path and GKG AllNames context establish an article-context reference to the registered NHL club"
                if value else
                "URL subject and GKG context show the extracted club name is outside the article's substantive context"
            )
        by_mapping[row["mapping_id"]].append(value)
        by_club[row["club_id"]].append(value)

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    mapping_precision = {
        mapping: {
            "sample_size": len(values),
            "true_matches": sum(values),
            "precision": precision(values),
            "quantification_status": "confirmed" if len(values) >= 5 and precision(values) >= .90 else "unavailable",
        }
        for mapping, values in sorted(by_mapping.items())
    }
    club_precision = {}
    for club, values in sorted(by_club.items()):
        mappings = sorted(mapping for mapping in by_mapping if any(row["club_id"] == club and row["mapping_id"] == mapping for row in rows))
        club_precision[club] = {
            "sample_size": len(values),
            "true_matches": sum(values),
            "precision": precision(values),
            "required_mappings": mappings,
            "quantification_status": "confirmed" if all(mapping_precision[mapping]["quantification_status"] == "confirmed" for mapping in mappings) else "unavailable",
        }
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        current_clubs = {row["club_id"] for row in csv.DictReader(handle)}
    ineligible_current = sorted(club for club in current_clubs if club_precision.get(club, {}).get("quantification_status") != "confirmed")
    result = {
        "status": "audit_complete",
        "reviewed_articles": len(rows),
        "true_matches": sum(row["is_true_club_match"] == "true" for row in rows),
        "overall_precision": sum(row["is_true_club_match"] == "true" for row in rows) / len(rows),
        "minimum_per_mapping": 5,
        "quantification_threshold": .90,
        "mapping_precision": mapping_precision,
        "club_precision": club_precision,
        "historical_club_identities_eligible_for_quantification": sum(state["quantification_status"] == "confirmed" for state in club_precision.values()),
        "clubs_eligible_for_quantification": len(current_clubs) - len(ineligible_current),
        "ineligible_clubs": ineligible_current,
        "decision": "GKG remains an excluded diagnostic because not every club clears the registered precision threshold.",
    }
    output = write_json("data/curated/gdelt_gkg_precision.json", result)
    manifest_path = ROOT / "data/manifests/gdelt_gkg_acquisition.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["evidence_status"] = "confirmed_daily_panel_but_not_release_eligible_due_club_precision"
    manifest["precision_audit_sample"]["review_status"] = "complete"
    manifest["precision_audit_sample"]["precision_result_path"] = "data/curated/gdelt_gkg_precision.json"
    manifest["precision_audit_sample"]["clubs_eligible_for_quantification"] = result["clubs_eligible_for_quantification"]
    manifest["precision_audit_sample"]["ineligible_clubs"] = result["ineligible_clubs"]
    manifest["precision_audit_sample"]["reviewed_articles"] = result["reviewed_articles"]
    write_json("data/manifests/gdelt_gkg_acquisition.json", manifest)
    return output


if __name__ == "__main__":
    print(build())
