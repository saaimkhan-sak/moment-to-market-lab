"""Repair the archived evidence paths for historically ambiguous club entities."""
from __future__ import annotations

import csv
from urllib.parse import quote

from common import ROOT, archive_json, fetch_json, write_json, now_utc


TARGETS = {
    "ARI": {"label": "Arizona Coyotes", "qid": "Q206312", "article": "Arizona Coyotes"},
    "WPG": {"label": "Winnipeg Jets", "qid": "Q472741", "article": "Winnipeg Jets"},
}


def main() -> None:
    evidence = {}
    for club_id, target in TARGETS.items():
        search_url = "https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=10&search=" + quote(target["label"])
        search_payload, search_provenance = fetch_json(search_url)
        if target["qid"] not in {row.get("id") for row in search_payload.get("search", [])}:
            raise ValueError(f"Expected entity absent from Wikidata search: {club_id} {target['qid']}")
        search_path = archive_json("wikidata", f"search-{club_id.lower()}", search_payload, search_provenance)

        entity_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&ids={target['qid']}&props=labels|sitelinks"
        entity_payload, entity_provenance = fetch_json(entity_url)
        entity = entity_payload.get("entities", {}).get(target["qid"], {})
        article = ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title")
        if article != target["article"]:
            raise ValueError(f"Unexpected English article for {club_id}: {article}")
        entity_path = archive_json("wikidata", f"{club_id.lower()}-{target['qid']}", entity_payload, entity_provenance)
        evidence[club_id] = {
            "search_source_url": search_url,
            "retrieved_at": entity_provenance["retrieved_at"],
            "search_archive": str(search_path),
            "entity_archive": str(entity_path),
            "entity_id": target["qid"],
            "wikipedia_article": article,
        }

    path = ROOT / "config/entity_dictionary.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        if row["club_id"] in evidence:
            row.update(evidence[row["club_id"]])
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    manifest = write_json("data/manifests/entity_provenance_repair.json", {
        "created_at": now_utc(),
        "evidence_status": "confirmed",
        "repairs": evidence,
    })
    print(manifest)


if __name__ == "__main__":
    main()
