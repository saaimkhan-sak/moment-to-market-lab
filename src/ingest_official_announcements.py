"""Validate manually reviewed official announcement triggers.

The source table is deliberately curated rather than keyword-generated. Each
YouTube record must resolve to a video in the archived, verified official club
channel dataset, and its UTC timestamp must match the API snapshot exactly.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from common import ROOT, now_utc, write_json
from analysis_window import ANALYSIS_START as ANALYSIS_START_DAY, ANALYSIS_END as ANALYSIS_END_DAY


SOURCE = ROOT / "config/official_announcement_sources.csv"
VIDEOS = ROOT / "data/curated/content_video.json"
ALLOWED_TYPES = {
    "playoff_clinch",
    "official_roster_event",
    "community_or_heritage_event",
}
ANALYSIS_START = ANALYSIS_START_DAY + "T00:00:00Z"
ANALYSIS_END = ANALYSIS_END_DAY + "T23:59:59Z"


def current_clubs() -> set[str]:
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        return {row["club_id"] for row in csv.DictReader(handle)}


def youtube_video_id(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.netloc not in {"www.youtube.com", "youtube.com"} or parsed.path != "/watch":
        raise ValueError(f"Unsupported official YouTube URL: {source_url}")
    values = parse_qs(parsed.query).get("v", [])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"Missing YouTube video ID: {source_url}")
    return values[0]


def validate_timestamp(value: str) -> None:
    if not value.endswith("Z"):
        raise ValueError(f"Announcement timestamp is not UTC: {value}")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not (ANALYSIS_START <= value <= ANALYSIS_END):
        raise ValueError(f"Announcement timestamp outside analysis window: {value}")


def main() -> None:
    clubs = current_clubs()
    videos = {row["video_id"]: row for row in json.loads(VIDEOS.read_text())}
    with SOURCE.open(newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    seen = set()
    records = []
    for row in source_rows:
        announcement_id = row["announcement_id"].strip()
        if not announcement_id or announcement_id in seen:
            raise ValueError(f"Duplicate or empty announcement_id: {announcement_id}")
        seen.add(announcement_id)
        if row["club_id"] not in clubs:
            raise ValueError(f"Unregistered current club: {row['club_id']}")
        if row["moment_type"] not in ALLOWED_TYPES:
            raise ValueError(f"Unsupported official moment type: {row['moment_type']}")
        if row["evidence_status"] != "confirmed":
            raise ValueError(f"Curated source is not confirmed: {announcement_id}")
        if not row["reviewer"] or not row["reviewed_at"] or not row["review_basis"]:
            raise ValueError(f"Missing manual-review provenance: {announcement_id}")
        validate_timestamp(row["announcement_time_utc"])

        video_id = youtube_video_id(row["source_url"])
        video = videos.get(video_id)
        if not video:
            raise ValueError(f"Official source is absent from archived YouTube data: {video_id}")
        if video.get("evidence_status") != "confirmed":
            raise ValueError(f"Official video is not confirmed: {video_id}")
        if video["club_id"] != row["club_id"]:
            raise ValueError(f"Official video club mismatch: {announcement_id}")
        if video["published_at"] != row["announcement_time_utc"]:
            raise ValueError(f"Official video timestamp mismatch: {announcement_id}")

        records.append({
            "announcement_id": announcement_id,
            "club_id": row["club_id"],
            "moment_type": row["moment_type"],
            "announcement_time_utc": row["announcement_time_utc"],
            "announcement_title": row["announcement_title"],
            "source_title": video["title"],
            "source_url": row["source_url"],
            "source_type": row["source_type"],
            "source_video_id": video_id,
            "source_channel_id": video["channel_id"],
            "source_retrieved_at": video["retrieved_at"],
            "evidence_status": "confirmed",
            "reviewer": row["reviewer"],
            "reviewed_at": row["reviewed_at"],
            "review_basis": row["review_basis"],
            "player_ids": [value for value in row.get("player_ids", "").split("|") if value],
            "opponent_id": row.get("opponent_id") or None,
            "rule_version": row["rule_version"],
            "timestamp_semantics": "official_publication_time_not_inferred_transaction_time",
        })

    records.sort(key=lambda row: (row["announcement_time_utc"], row["announcement_id"]))
    roster_clubs = {row["club_id"] for row in records if row["moment_type"] == "official_roster_event"}
    if roster_clubs != clubs:
        raise ValueError(f"Roster-event coverage must include all current clubs; missing={sorted(clubs-roster_clubs)}")
    type_counts = Counter(row["moment_type"] for row in records)
    if set(type_counts) != ALLOWED_TYPES:
        raise ValueError(f"All official moment classes must be populated: {type_counts}")

    write_json("data/curated/official_announcement.json", records)
    manifest = write_json("data/manifests/official_announcement_acquisition.json", {
        "source_id": "official-club-youtube-manual-announcement-audit",
        "created_at": now_utc(),
        "evidence_status": "confirmed",
        "record_count": len(records),
        "current_clubs_with_roster_event": len(roster_clubs),
        "moment_type_counts": dict(sorted(type_counts.items())),
        "source_table": str(SOURCE.relative_to(ROOT)),
        "source_video_archive": str(VIDEOS.relative_to(ROOT)),
        "timestamp_semantics": "official_publication_time_not_inferred_transaction_time",
    })
    print(manifest)


if __name__ == "__main__":
    main()
