"""Build a historical, event-time YouTube publication panel without backcasting stats.

Publication timestamps are genuinely historical public metadata. Current views,
likes, and comment totals are deliberately excluded from this table because they
were observed at retrieval time, not at the event time.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta

from common import ROOT, now_utc, write_json


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def window(day_offset: int) -> str | None:
    if 0 <= day_offset <= 1:
        return "immediate"
    if 2 <= day_offset <= 3:
        return "short_persistence"
    if 4 <= day_offset <= 7:
        return "sustained"
    return None


def build() -> str:
    moments = json.loads((ROOT / "data/curated/moment.json").read_text())
    videos = json.loads((ROOT / "data/curated/content_video.json").read_text())
    by_club: dict[str, list[dict]] = defaultdict(list)
    for video in videos:
        if video.get("published_at"):
            by_club[video["club_id"]].append(video)
    for rows in by_club.values():
        rows.sort(key=lambda row: (row["published_at"], row["video_id"]))

    candidates: list[dict] = []
    for moment in moments:
        event_at = utc(moment["moment_time_utc"])
        end = event_at + timedelta(days=8)
        for video in by_club.get(moment["club_id"], []):
            published_at = utc(video["published_at"])
            if published_at < event_at:
                continue
            if published_at >= end:
                break
            # Use elapsed 24-hour bins from the event timestamp. A late-evening
            # event followed by a morning publication should remain Day 0, not
            # jump merely because the UTC calendar date changed.
            offset = int((published_at - event_at).total_seconds() // 86400)
            candidates.append({
                "moment_id": moment["moment_id"],
                "club_id": moment["club_id"],
                "moment_type": moment["moment_type"],
                "moment_time_utc": moment["moment_time_utc"],
                "video_id": video["video_id"],
                "video_published_at": video["published_at"],
                "day_offset": offset,
                "post_window": window(offset),
                "source_url": video["source_url"],
                "video_metadata_retrieved_at": video["retrieved_at"],
            })

    # A publication may follow several overlapping moments. Assign it only to
    # the closest preceding moment in the primary panel; preserve every
    # alternative match and its exclusion reason for auditability.
    by_video: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        by_video[row["video_id"]].append(row)
    for rows in by_video.values():
        rows.sort(key=lambda row: (
            utc(row["video_published_at"]) - utc(row["moment_time_utc"]),
            row["moment_id"],
        ))
        primary = rows[0]["moment_id"]
        for row in rows:
            row["in_primary_panel"] = row["moment_id"] == primary
            row["exclusion_reason"] = None if row["in_primary_panel"] else "overlapping_moment_closest_preceding_assignment"
            row["evidence_status"] = "confirmed"
            row["metric_scope"] = "official_club_upload_publication_only"

    primary = [row for row in candidates if row["in_primary_panel"]]
    primary.sort(key=lambda row: (row["moment_time_utc"], row["club_id"], row["video_published_at"], row["video_id"]))
    candidates.sort(key=lambda row: (row["video_id"], row["moment_time_utc"], row["moment_id"]))
    write_json("data/curated/youtube_event_publication.json", primary)
    write_json("data/evidence/youtube_event_publication_all_matches.json", candidates)

    # Comment reconstruction targets one objective video per moment: the first
    # primary-panel upload during Days 0-1. Selection uses timestamps only and
    # never current engagement totals.
    target_by_moment: dict[str, list[dict]] = defaultdict(list)
    for row in primary:
        if row["post_window"] == "immediate":
            target_by_moment[row["moment_id"]].append(row)
    targets = []
    for moment_id, rows in target_by_moment.items():
        selected = min(rows, key=lambda row: (row["video_published_at"], row["video_id"]))
        targets.append({key: selected[key] for key in (
            "moment_id", "club_id", "moment_type", "moment_time_utc",
            "video_id", "video_published_at", "source_url"
        )})
    targets.sort(key=lambda row: (row["club_id"], row["moment_time_utc"], row["video_id"]))
    return str(write_json("data/manifests/youtube_historical_comment_targets.json", {
        "built_at": now_utc(),
        "selection_rule": "first official club upload published during UTC-relative Days 0-1 after each moment; overlapping videos assigned to closest preceding moment",
        "selection_inputs_exclude_current_engagement": True,
        "candidate_pair_count": len(candidates),
        "primary_publication_count": len(primary),
        "target_count": len(targets),
        "targets": targets,
        "limitation": "Upload timing is a club publishing response. It is not audience reach, engagement, sentiment, or causal impact.",
    }))


if __name__ == "__main__":
    print(build())
