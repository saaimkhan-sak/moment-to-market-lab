"""Acquire the two missing validity-query samples for manual GDELT review.

This script never labels an article as a true match. It archives the exact DOC
ArticleList response and writes a deterministic five-row candidate sheet that a
reviewer must code before the rows can enter the canonical audit.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from common import ROOT, now_utc, write_json


REQUESTS = [
    {
        "mapping_id": "TOR-current",
        "club_id": "TOR",
        "query": '"Toronto Maple Leafs" sourcelang:english',
        "start": "20260503000000",
        "end": "20260803000000",
    },
    {
        "mapping_id": "UTA-hockey-club",
        "club_id": "UTA",
        "query": '"Utah Hockey Club" sourcelang:english',
        "start": "20250205000000",
        "end": "20250506235959",
    },
]
USER_AGENT = "nhl-moment-to-market-lab/1.0 (public-research; paced-acquisition)"


def source_url(item: dict) -> str:
    params = {
        "format": "json",
        "mode": "artlist",
        "maxrecords": 50,
        "startdatetime": item["start"],
        "enddatetime": item["end"],
        "query": item["query"],
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode(params, quote_via=quote)


def article_rows(payload: dict) -> list[dict]:
    # ArticleList JSON has appeared under both `articles` and JSONFeed `items`.
    values = payload.get("articles") or payload.get("items") or []
    rows = []
    for article in values:
        url = article.get("url") or article.get("external_url")
        title = article.get("title")
        if not url or not title:
            continue
        rows.append({
            "article_url": url,
            "title": title,
            "domain": article.get("domain") or urlparse(url).netloc.lower().removeprefix("www."),
            "language": article.get("language") or "",
            "source_country": article.get("sourcecountry") or article.get("source_country") or "",
            "seen_at": article.get("seendate") or article.get("date_published") or "",
        })
    return rows


def deterministic_sample(rows: list[dict], query: str, size: int = 5) -> list[dict]:
    unique = {row["article_url"]: row for row in rows}
    ranked = sorted(
        unique.values(),
        key=lambda row: hashlib.sha256(f"{query}|{row['article_url']}".encode()).hexdigest(),
    )
    if len(ranked) < size:
        raise ValueError(f"GDELT returned only {len(ranked)} auditable articles for {query}")
    return ranked[:size]


def build(spacing_seconds: float = 120.0) -> Path:
    archive_dir = ROOT / "data/raw/gdelt/audit_supplement"
    archive_dir.mkdir(parents=True, exist_ok=True)
    candidate_rows = []
    manifest_rows = []
    for index, item in enumerate(REQUESTS):
        if index:
            time.sleep(spacing_seconds)
        url = source_url(item)
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=120) as response:
            body = response.read()
            status = response.status
        payload = json.loads(body)
        rows = article_rows(payload)
        sample = deterministic_sample(rows, item["query"])
        retrieved_at = now_utc()
        archive = archive_dir / f"{item['mapping_id']}.json"
        archive.write_text(json.dumps({
            "mapping_id": item["mapping_id"],
            "club_id": item["club_id"],
            "query": item["query"],
            "source_url": url,
            "http_status": status,
            "retrieved_at": retrieved_at,
            "body_checksum": hashlib.sha256(body).hexdigest(),
            "payload": payload,
        }, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        for row in sample:
            audit_id = hashlib.sha256(f"gdelt-doc-supplement|{item['club_id']}|{item['query']}|{row['article_url']}".encode()).hexdigest()[:32]
            candidate_rows.append({
                "audit_id": audit_id,
                "club_id": item["club_id"],
                "stratum": "validity_query_supplement_exact_full_name",
                **row,
                "query": item["query"],
                "retrieved_at": retrieved_at,
                "reviewer": "",
                "is_true_club_match": "",
                "exclusion_reason": "",
                "reviewed_at": "",
                "review_basis": "",
            })
        manifest_rows.append({
            "mapping_id": item["mapping_id"],
            "club_id": item["club_id"],
            "query": item["query"],
            "source_url": url,
            "archive_path": str(archive.relative_to(ROOT)),
            "returned_articles": len(rows),
            "sampled_articles": len(sample),
            "retrieved_at": retrieved_at,
        })
    output = ROOT / "data/evidence/gdelt_query_audit_supplement_candidates.csv"
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidate_rows[0]))
        writer.writeheader()
        writer.writerows(candidate_rows)
    return write_json("data/manifests/gdelt_query_audit_supplement.json", {
        "evidence_status": "pending_manual_review",
        "candidate_path": str(output.relative_to(ROOT)),
        "candidate_count": len(candidate_rows),
        "requests": manifest_rows,
    })


if __name__ == "__main__":
    print(build())
