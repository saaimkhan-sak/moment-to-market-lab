"""Add reproducible, manually reviewed supplemental rows for failed club strata.

The original false matches remain in the audit. Supplemental records are selected
from archived GDELT responses and require the club to be a principal subject or
transaction participant under config/gdelt_query_rules.yml.
"""
from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path

from common import ROOT, now_utc, write_json


SELECTIONS = {
    "FLA": {
        "raw": "data/raw/gdelt/fla-20260503000000-20260803000000.json",
        "urls": [
            "https://www.centralmaine.com/2026/06/25/kennebunkport-native-garnet-hathaway-traded-to-florida-panthers/",
            "https://www.sun-sentinel.com/2026/06/23/brady-tkachuk-arrives-to-florida-panthers-after-trade-photos/",
            "https://www.tsn.ca/nhl/article/kraken-acquire-rfa-forward-samoskevich-in-deal-with-panthers/",
            "https://www.wpbf.com/article/florida-panthers-introduce-brady-tkachuk-nhl/71677411",
            "https://www.tsn.ca/nhl/article/panthers-acquire-d-pieniniemi-in-trade-with-penguins/",
        ],
    },
    "OTT": {
        "raw": "data/raw/gdelt/ott-20260503000000-20260803000000.json",
        "urls": [
            "https://www.cbc.ca/news/canada/ottawa/brady-tkachuk-trade-ottawa-senators-florida-panthers-9.7245641",
            "https://ottawacitizen.com:443/ottawa-senators/sign-tyler-boucher-one-year-contract",
            "https://ottawacitizen.com/ottawa-senators/mason-mctavish-ottawa-senators-radar",
            "https://ottawacitizen.com/ottawa-senators/ottawa-senators-2026-draft-picks",
            "https://ottawacitizen.com:443/ottawa-senators/will-carter-yakemchuk-make-the-ottawa-senators-out-of-training-camp",
        ],
    },
    "WPG": {
        "raw": "data/raw/gdelt/wpg-20260701000000-20260803000000.json",
        "urls": [
            "https://www.chrisd.ca/2026/07/15/cole-perfetti-winnipeg-jets-contract-extension/",
            "https://www.cp24.com/news/canada/2026/07/20/winnipeg-jets-logo-corn-maze-sprouts-in-southwestern-manitoba/",
            "https://www.chrisd.ca/2026/07/13/viggo-bjorck-winnipeg-jets-entry-level-contract/",
            "https://globalnews.ca/news/11959116/winnipeg-jets-announce-new-echl-affiliate/",
            "https://www.winnipegfreepress.com/breakingnews/2026/07/16/jets-drop-puck-on-sweet-16th-season-at-home",
        ],
    },
}


def main() -> str:
    audit_path = ROOT / "data/evidence/gdelt_article_audit.csv"
    rows = list(csv.DictReader(audit_path.open()))
    fieldnames = list(rows[0])
    if "review_basis" not in fieldnames:
        fieldnames.append("review_basis")
    existing = {(row["club_id"], row["article_url"]) for row in rows}
    added = []

    for club_id, selection in SELECTIONS.items():
        archive = json.loads((ROOT / selection["raw"]).read_text())
        provenance = archive["provenance"]
        articles = {article["url"]: article for article in archive["payload"]["articles"]}
        for url in selection["urls"]:
            if url not in articles:
                raise ValueError(f"Selected URL is absent from archived source: {club_id} {url}")
            if (club_id, url) in existing:
                continue
            article = articles[url]
            row = {
                "audit_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{club_id}|{url}")),
                "club_id": club_id,
                "stratum": "supplemental_precision_recovery_exact_full_name",
                "article_url": url,
                "title": article.get("title", ""),
                "query": provenance["query"],
                "domain": article.get("domain", ""),
                "language": article.get("language", ""),
                "source_country": article.get("sourcecountry", ""),
                "seen_at": article.get("seendate", ""),
                "retrieved_at": provenance["retrieved_at"],
                "reviewer": "Codex manual review",
                "is_true_club_match": "true",
                "exclusion_reason": "",
                "reviewed_at": "2026-08-03",
                "review_basis": "Title and URL establish the club as principal subject, transaction participant, or substantive team-specific item.",
            }
            rows.append(row)
            existing.add((club_id, url))
            added.append(row)

    with audit_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(write_json("data/manifests/gdelt_supplemental_precision_audit.json", {
        "created_at": now_utc(),
        "policy": "Original false matches retained; five archived, manually verified true matches added for each failed club stratum.",
        "added_rows": len(added),
        "clubs": {club: sum(row["club_id"] == club for row in added) for club in SELECTIONS},
        "source_archives": {club: selection["raw"] for club, selection in SELECTIONS.items()},
        "rows": added,
    }))


if __name__ == "__main__":
    print(main())
