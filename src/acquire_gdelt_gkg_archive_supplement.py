"""Acquire deterministic GKG precision-audit supplements from raw archives.

The BigQuery audit's five-row strata exposed publisher-page contamination for
four clubs.  This collector extends those strata without cherry-picking: it
hash-orders regular-season game dates, checks fixed three-hour GKG snapshots,
retains every source ZIP unchanged, and emits unlabeled candidate rows.  A
human review is still required before any row can affect release eligibility.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from common import ROOT, now_utc, write_json


TARGETS = {
    "BOS": {"mapping_id": "BOS-current", "entity_id": "Q194121", "entity_label": "Boston Bruins"},
    "CHI": {"mapping_id": "CHI-current", "entity_id": "Q209636", "entity_label": "Chicago Blackhawks"},
    "NSH": {"mapping_id": "NSH-current", "entity_id": "Q207980", "entity_label": "Nashville Predators"},
    "WPG": {"mapping_id": "WPG-current", "entity_id": "Q472741", "entity_label": "Winnipeg Jets"},
}
SNAPSHOT_HOURS = tuple(range(0, 24, 3))
USER_AGENT = "nhl-moment-to-market-lab/1.0 (public-research; archive-audit)"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_master(path: Path) -> dict[str, dict]:
    wanted = {f"{hour:02d}0000" for hour in SNAPSHOT_HOURS}
    records = {}
    with path.open() as handle:
        for line in handle:
            parts = line.split()
            if len(parts) != 3:
                continue
            size, md5, url = parts
            name = url.rsplit("/", 1)[-1]
            if not name.endswith(".gkg.csv.zip"):
                continue
            timestamp = name[:14]
            if timestamp[8:] not in wanted:
                continue
            records[timestamp] = {"size": int(size), "md5": md5, "url": url}
    return records


def selected_game_dates(club_id: str) -> list[str]:
    games = json.loads((ROOT / "data/curated/game.json").read_text())
    dates = {
        game["start_time_utc"][:10].replace("-", "")
        for game in games
        if game["game_type"] == 2 and club_id in {game["home_club_id"], game["away_club_id"]}
    }
    return sorted(dates, key=lambda date: hashlib.sha256(f"gkg-audit-v1|{club_id}|{date}".encode()).hexdigest())


def download(record: dict, target: Path) -> tuple[bytes, bool]:
    if target.exists():
        body = target.read_bytes()
        return body, True
    request = urllib.request.Request(record["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
    if len(body) != record["size"]:
        raise ValueError(f"size mismatch for {record['url']}")
    if hashlib.md5(body).hexdigest() != record["md5"]:  # noqa: S324 - source manifest uses MD5
        raise ValueError(f"master-list checksum mismatch for {record['url']}")
    target.write_bytes(body)
    return body, False


def matching_rows(body: bytes, club_id: str, target: dict, timestamp: str) -> list[dict]:
    pattern = re.compile(rf"(?:^|;){re.escape(target['entity_label'])},\d+", re.IGNORECASE)
    rows = []
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        member = archive.namelist()[0]
        with archive.open(member) as raw:
            for raw_line in raw:
                fields = raw_line.decode("utf-8", errors="replace").rstrip("\n").split("\t")
                if len(fields) < 24 or not pattern.search(fields[23]):
                    continue
                rows.append({
                    "mapping_id": target["mapping_id"],
                    "club_id": club_id,
                    "entity_id": target["entity_id"],
                    "entity_label": target["entity_label"],
                    "article_date": timestamp[:8],
                    "article_url": fields[4],
                    "source_common_name": fields[3],
                    "source_locations": fields[10],
                    "matched_all_names": fields[23],
                    "source_gkg_record_id": fields[0],
                    "source_archive_timestamp": timestamp,
                })
    return rows


def acquire(master_path: Path, target_candidates: int) -> Path:
    master = load_master(master_path)
    archive_dir = ROOT / "data/raw/gdelt/gkg_archive_supplement"
    archive_dir.mkdir(parents=True, exist_ok=True)
    existing = {
        row["article_url"]
        for row in csv.DictReader((ROOT / "data/evidence/gdelt_gkg_article_audit.csv").open())
    }
    candidates: list[dict] = []
    seen = set(existing)
    archives = []
    counts = defaultdict(int)

    for club_id, target in TARGETS.items():
        for game_date in selected_game_dates(club_id):
            for hour in SNAPSHOT_HOURS:
                timestamp = f"{game_date}{hour:02d}0000"
                record = master.get(timestamp)
                if not record:
                    continue
                archive_path = archive_dir / f"{timestamp}.gkg.csv.zip"
                body, reused = download(record, archive_path)
                matches = matching_rows(body, club_id, target, timestamp)
                archives.append({
                    "club_id": club_id,
                    "game_date_stratum": game_date,
                    "timestamp": timestamp,
                    "source_url": record["url"],
                    "archive_path": str(archive_path.relative_to(ROOT)),
                    "bytes": len(body),
                    "master_md5": record["md5"],
                    "sha256": sha256_bytes(body),
                    "reused": reused,
                    "exact_name_rows": len(matches),
                })
                for row in matches:
                    if row["article_url"] in seen:
                        continue
                    seen.add(row["article_url"])
                    row["sample_hash"] = sha256_bytes(
                        f"gkg-audit-v1|{target['mapping_id']}|{row['article_url']}".encode()
                    )
                    candidates.append(row)
                    counts[club_id] += 1
                if counts[club_id] >= target_candidates:
                    break
            if counts[club_id] >= target_candidates:
                break

    candidates.sort(key=lambda row: (row["club_id"], row["sample_hash"]))
    reviewed_at_fields = {
        "reviewer": "", "is_true_club_match": "", "exclusion_reason": "",
        "reviewed_at": "", "review_basis": "",
    }
    for rank, row in enumerate(candidates, start=1):
        row["sample_rank"] = rank
        row.update(reviewed_at_fields)
    output = ROOT / "data/evidence/gdelt_gkg_archive_supplement_candidates.csv"
    if candidates:
        with output.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(candidates[0]))
            writer.writeheader()
            writer.writerows(candidates)

    return write_json("data/manifests/gdelt_gkg_archive_supplement.json", {
        "created_at": now_utc(),
        "evidence_status": "pending_manual_review",
        "sampling_version": "gkg-archive-audit-v1",
        "sampling_contract": "SHA256-ordered regular-season game dates; fixed 00/03/06/09/12/15/18/21 UTC snapshots; all exact-name candidates retained and hash-ranked; no automatic labels.",
        "master_list_path": str(master_path),
        "master_list_sha256": sha256_bytes(master_path.read_bytes()),
        "target_candidates_per_failed_club": target_candidates,
        "candidate_counts": dict(counts),
        "candidate_path": str(output.relative_to(ROOT)),
        "source_archive_count": len(archives),
        "source_archives": archives,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-list", type=Path, required=True)
    parser.add_argument("--target-candidates", type=int, default=20)
    args = parser.parse_args()
    print(acquire(args.master_list, args.target_candidates))
