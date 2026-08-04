"""Materialize the GDELT article audit and precision gates by validity-era query."""
from __future__ import annotations

import csv
from collections import defaultdict

from common import ROOT, write_json


def expected_queries() -> dict[str, set[str]]:
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        current = {row["club_id"] for row in csv.DictReader(handle)}
    expected = defaultdict(set)
    with (ROOT / "config/entity_dictionary.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row["status"] == "confirmed" and row["club_id"] in current:
                expected[row["club_id"]].add(f'"{row["entity_label"]}" sourcelang:english')
    return expected


def precision_state(values: list[bool]) -> dict:
    precision = sum(values) / len(values) if values else None
    return {
        "sample_size": len(values),
        "precision": precision,
        "quantification_status": "confirmed" if len(values) >= 5 and precision is not None and precision >= 0.90 else "unavailable",
    }


def build():
    path = ROOT / "data/evidence/gdelt_article_audit.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    reviewed = [row for row in rows if row.get("is_true_club_match") in {"true", "false"}]
    write_json("data/curated/gdelt_article_observation.json", [
        {
            "audit_id": row["audit_id"],
            "club_id": row["club_id"],
            "query": row["query"],
            "article_url": row["article_url"],
            "title": row["title"],
            "domain": row["domain"],
            "source_language": row["language"],
            "source_country": row["source_country"],
            "seen_at": row["seen_at"],
            "retrieved_at": row["retrieved_at"],
            "reviewer": row["reviewer"],
            "reviewed_at": row["reviewed_at"],
            "is_true_club_match": row["is_true_club_match"] == "true",
            "exclusion_reason": row["exclusion_reason"] or None,
            "review_basis": row.get("review_basis") or None,
            "evidence_status": "confirmed_manual_review",
        }
        for row in reviewed
    ])

    by_club = defaultdict(list)
    by_query = defaultdict(list)
    for row in reviewed:
        value = row["is_true_club_match"] == "true"
        by_club[row["club_id"]].append(value)
        by_query[(row["club_id"], row["query"])].append(value)
    expected = expected_queries()
    query_precision = {}
    club_precision = {}
    for club, queries in sorted(expected.items()):
        query_states = {}
        for query in sorted(queries):
            state = precision_state(by_query[(club, query)])
            query_states[query] = state
            query_precision[f"{club}|{query}"] = state
        aggregate = precision_state(by_club[club])
        aggregate["required_queries"] = query_states
        aggregate["quantification_status"] = "confirmed" if all(state["quantification_status"] == "confirmed" for state in query_states.values()) else "unavailable"
        club_precision[club] = aggregate

    true_matches = sum(row["is_true_club_match"] == "true" for row in reviewed)
    overall = {"sample_size": len(reviewed), "true_matches": true_matches, "precision": true_matches / len(reviewed) if reviewed else None}
    complete = len(reviewed) >= 160 and len(club_precision) == 32 and all(state["sample_size"] >= 5 for state in club_precision.values())
    quantified = sum(state["quantification_status"] == "confirmed" for state in club_precision.values())
    status = "audit_complete" if complete else "unavailable_pending_stratified_160_article_audit"
    return write_json("data/curated/gdelt_precision.json", {
        "status": status,
        "minimum_article_audit": 160,
        "minimum_per_club": 5,
        "minimum_per_validity_query": 5,
        "quantification_threshold": 0.90,
        "reviewed_articles": len(reviewed),
        "required_validity_queries": sum(len(queries) for queries in expected.values()),
        "validity_queries_eligible": sum(state["quantification_status"] == "confirmed" for state in query_precision.values()),
        "clubs_eligible_for_quantification": quantified,
        "overall_precision": overall,
        "club_precision": club_precision,
        "query_precision": query_precision,
    })


if __name__ == "__main__":
    print(build())
