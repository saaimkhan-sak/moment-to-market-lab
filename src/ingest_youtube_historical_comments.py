"""Reconstruct surviving top-level YouTube comment timing for selected videos.

The API response is field-filtered so raw archives retain timestamps and IDs,
not comment text or author information. Deleted and moderated comments cannot be
recovered and are never treated as zero.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError

from common import ROOT, digest, fetch_json, load_env, now_utc, write_json
from ingest_youtube import request


RAW = ROOT / "data/raw/youtube-comments"
FIELDS = "nextPageToken,pageInfo,items(id,snippet(topLevelComment(id,snippet(publishedAt,updatedAt)),totalReplyCount))"


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def archive_path(video_id: str) -> Path:
    return RAW / f"{video_id}.json"


def acquire_video(video_id: str, key: str) -> dict:
    path = archive_path(video_id)
    if path.exists():
        record = json.loads(path.read_text())
        return record["manifest"]
    pages = []
    page_token = None
    try:
        while True:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": 100,
                "order": "time",
                "textFormat": "plainText",
                "fields": FIELDS,
                "key": key,
            }
            if page_token:
                params["pageToken"] = page_token
            payload, provenance = request("commentThreads", **params)
            pages.append({"provenance": provenance, "payload": payload})
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
            time.sleep(0.05)
        ids = {
            item.get("snippet", {}).get("topLevelComment", {}).get("id")
            for page in pages for item in page["payload"].get("items", [])
        }
        ids.discard(None)
        manifest = {
            "video_id": video_id,
            "evidence_status": "confirmed",
            "page_count": len(pages),
            "surviving_top_level_comment_count": len(ids),
            "retrieved_at": pages[-1]["provenance"]["retrieved_at"],
            "source_url": pages[0]["provenance"]["source_url"],
            "fields_policy": "IDs and timestamps only; no author or comment text retained",
        }
    except HTTPError as exc:
        status = "unavailable" if exc.code in {403, 404} else "blocked"
        manifest = {
            "video_id": video_id,
            "evidence_status": status,
            "reason": f"youtube_http_{exc.code}",
            "page_count": len(pages),
            "retrieved_at": now_utc(),
            "source_url": f"https://www.googleapis.com/youtube/v3/commentThreads?videoId={video_id}",
        }
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"manifest": manifest, "pages": pages}, indent=2, sort_keys=True))
    return manifest


def build_curated(targets: list[dict]) -> str:
    target_by_video = {row["video_id"]: row for row in targets}
    rows = []
    coverage = []
    for video_id, target in sorted(target_by_video.items()):
        path = archive_path(video_id)
        if not path.exists():
            coverage.append({**target, "evidence_status": "missing", "reason": "comment_archive_not_acquired"})
            continue
        record = json.loads(path.read_text())
        coverage.append({**target, **record["manifest"]})
        if record["manifest"].get("evidence_status") != "confirmed":
            continue
        seen = set()
        event_at = utc(target["moment_time_utc"])
        for page in record["pages"]:
            for item in page["payload"].get("items", []):
                comment = item.get("snippet", {}).get("topLevelComment", {})
                comment_id = comment.get("id")
                snippet = comment.get("snippet", {})
                published = snippet.get("publishedAt")
                if not comment_id or not published or comment_id in seen:
                    continue
                seen.add(comment_id)
                offset = int((utc(published) - event_at).total_seconds() // 86400)
                if offset < 0 or offset > 7:
                    continue
                post_window = "immediate" if offset <= 1 else ("short_persistence" if offset <= 3 else "sustained")
                rows.append({
                    "moment_id": target["moment_id"],
                    "club_id": target["club_id"],
                    "moment_type": target["moment_type"],
                    "video_id": video_id,
                    "comment_id": comment_id,
                    "comment_published_at": published,
                    "day_offset": offset,
                    "post_window": post_window,
                    "source_url": target["source_url"],
                    "retrieved_at": record["manifest"]["retrieved_at"],
                    "evidence_status": "confirmed",
                    "metric_scope": "surviving_top_level_public_comments_only",
                })
    rows.sort(key=lambda row: (row["moment_id"], row["comment_published_at"], row["comment_id"]))
    coverage.sort(key=lambda row: (row["club_id"], row["moment_time_utc"], row["video_id"]))
    write_json("data/curated/youtube_historical_comment_event.json", rows)
    return str(write_json("data/manifests/youtube_historical_comment_acquisition.json", {
        "built_at": now_utc(),
        "target_count": len(target_by_video),
        "confirmed_targets": sum(row.get("evidence_status") == "confirmed" for row in coverage),
        "unavailable_targets": sum(row.get("evidence_status") == "unavailable" for row in coverage),
        "missing_targets": sum(row.get("evidence_status") == "missing" for row in coverage),
        "curated_comment_count": len(rows),
        "coverage": coverage,
        "limitation": "Counts include only top-level comments still public at retrieval. Deleted, moderated, reply, and disabled-comment observations are not reconstructed; this is descriptive public interaction, not sentiment or causal impact.",
    }))


def run(limit: int | None = None) -> str:
    load_env()
    key = os.getenv("YOUTUBE_API_KEY")
    plan = json.loads((ROOT / "data/manifests/youtube_historical_comment_targets.json").read_text())
    targets = plan["targets"]
    if not key:
        return str(write_json("data/manifests/youtube_historical_comment_acquisition.json", {
            "built_at": now_utc(), "evidence_status": "unavailable",
            "reason": "YOUTUBE_API_KEY is not set", "target_count": len(targets),
        }))
    pending = [row for row in targets if not archive_path(row["video_id"]).exists()]
    if limit is not None:
        pending = pending[:limit]
    for index, target in enumerate(pending, 1):
        result = acquire_video(target["video_id"], key)
        print(f"[{index}/{len(pending)}] {target['video_id']}: {result['evidence_status']}", flush=True)
        time.sleep(0.05)
    return build_curated(targets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    print(run(args.limit))
