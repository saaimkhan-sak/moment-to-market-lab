"""Assemble compact, deterministic browser data from final curated outputs."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics

from common import ROOT, write_json
from content_formats import format_counts


APP_DATA = ROOT / "app/data"
LEGACY_LEAGUE_FILES = [
    "game.json",
    "moment.json",
    "attention_event_window.json",
    "club_moment_estimate.json",
    "club_profiles.json",
    "activation_playbook.json",
    "market_context.json",
]
STALE_APP_FILES = LEGACY_LEAGUE_FILES + [
    "game_event.json",
    "gdelt_article_observation.json",
    "gdelt_attention_daily.json",
    "gdelt_gkg_precision.json",
    "gdelt_precision.json",
    "nhl_moneypuck_reconciliation.json",
    "signal_traces.json",
    "youtube_summary.json",
    "CLUB_REGISTRY.csv",
    "gdelt_gkg_attention_daily.json",
    "gdelt_gkg_release_precision.json",
]
def day(value: str) -> date:
    return date.fromisoformat(value[:4] + "-" + value[4:6] + "-" + value[6:8]) if "-" not in value[:10] else date.fromisoformat(value[:10])


def median(values):
    return statistics.median(values) if values else None


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_signal_traces(moments: list[dict], attention: list[dict]) -> list[dict]:
    by_club_channel = defaultdict(dict)
    for row in attention:
        value = row.get("metric_value")
        if row["channel"] == "gdelt_earned_media":
            value = row.get("normalized_articles_per_100k")
        if value is not None:
            by_club_channel[(row["club_id"], row["channel"])][day(row["date_utc"])] = float(value)
    moment_days = defaultdict(list)
    for row in moments:
        moment_days[row["club_id"]].append((row["moment_id"], day(row["moment_time_utc"]), row.get("game_id")))
    grouped = defaultdict(lambda: defaultdict(list))
    for moment in moments:
        club = moment["club_id"]
        event_day = day(moment["moment_time_utc"])
        overlap = any(
            other_id != moment["moment_id"] and abs((other_day - event_day).days) <= 7 and other_game != moment.get("game_id")
            for other_id, other_day, other_game in moment_days[club]
        )
        if overlap:
            continue
        for (candidate_club, channel), daily in by_club_channel.items():
            if candidate_club != club:
                continue
            baseline_values = [daily.get(event_day - timedelta(days=offset)) for offset in range(1, 15)]
            if any(value is None for value in baseline_values):
                continue
            baseline = sum(baseline_values) / 14
            for offset in range(-7, 8):
                value = daily.get(event_day + timedelta(days=offset))
                if value is None:
                    continue
                normalized = (value - baseline) / max(baseline, 1)
                grouped[(club, moment["moment_type"], channel)][offset].append(normalized)
    rows = []
    for (club, moment_type, channel), offsets in sorted(grouped.items()):
        rows.append({
            "club_id": club,
            "moment_type": moment_type,
            "attention_channel": channel,
            "normalization": "(daily value - 14-day pre-event mean) / max(14-day pre-event mean, 1)",
            "points": [
                {"day_offset": offset, "median_difference": median(offsets.get(offset, [])), "sample_size": len(offsets.get(offset, []))}
                for offset in range(-7, 8)
            ],
        })
    return rows


def youtube_summary(
    videos: list[dict],
    publications: list[dict],
    historical_comments: list[dict],
    comment_manifest: dict,
) -> list[dict]:
    grouped = defaultdict(list)
    for video in videos:
        grouped[video["club_id"]].append(video)
    publication_groups = defaultdict(list)
    for row in publications:
        if row.get("evidence_status") == "confirmed":
            publication_groups[(row["club_id"], row["moment_type"])].append(row)
    comment_groups = defaultdict(list)
    for row in historical_comments:
        if row.get("evidence_status") == "confirmed":
            comment_groups[(row["club_id"], row["moment_type"])].append(row)
    coverage_groups = defaultdict(list)
    for row in comment_manifest.get("coverage", []):
        coverage_groups[(row["club_id"], row["moment_type"])].append(row)
    result = []
    for club, rows in sorted(grouped.items()):
        rules = format_counts(rows)
        top = sorted(rows, key=lambda row: int(row.get("view_count") or 0), reverse=True)[:8]
        moment_types = sorted({moment for candidate, moment in publication_groups if candidate == club})
        historical_by_moment = []
        for moment_type in moment_types:
            published = publication_groups[(club, moment_type)]
            comments = comment_groups[(club, moment_type)]
            coverage = coverage_groups[(club, moment_type)]
            historical_by_moment.append({
                "moment_type": moment_type,
                "qualifying_moments_with_uploads": len({row["moment_id"] for row in published}),
                "official_uploads_by_window": dict(sorted(Counter(row["post_window"] for row in published).items())),
                "comment_target_count": len(coverage),
                "comment_targets_confirmed": sum(row.get("evidence_status") == "confirmed" for row in coverage),
                "comment_targets_unavailable": sum(row.get("evidence_status") != "confirmed" for row in coverage),
                "surviving_top_level_comments_by_window": dict(sorted(Counter(row["post_window"] for row in comments).items())),
            })
        result.append({
            "club_id": club,
            "video_count": len(rows),
            "oldest_published_at": min(row["published_at"] for row in rows),
            "newest_published_at": max(row["published_at"] for row in rows),
            "retrieved_at": max(row["retrieved_at"] for row in rows),
            "format_counts": rules,
            "classification_rule": "case-insensitive title keyword rules registered in src/content_formats.py; categories may overlap",
            "top_current_public_view_snapshots": [
                {key: row[key] for key in ("video_id", "title", "published_at", "view_count", "like_count", "comment_count", "source_url")}
                for row in top
            ],
            "historical_publication_by_moment": historical_by_moment,
            "historical_publication_scope": "Official upload timestamps and surviving top-level public-comment timestamps are event-time observations. Current views, likes, comments, and subscribers are excluded from this historical layer.",
            "limitation": "Current views, likes, and comment totals are retrieval-time snapshots, not historical trajectories. Historical comment counts include only top-level comments still public at retrieval; deleted, moderated, reply, and disabled-comment observations cannot be reconstructed.",
        })
    return result


def build():
    model = json.loads((ROOT / "data/curated/club_moment_estimate.json").read_text())
    gdelt_manifest = json.loads((ROOT / "data/manifests/gdelt_timeline_acquisition.json").read_text())
    gkg_manifest = json.loads((ROOT / "data/manifests/gdelt_gkg_release_acquisition.json").read_text())
    gkg_precision = json.loads((ROOT / "data/curated/gdelt_gkg_release_precision.json").read_text())
    gdelt_precision = json.loads((ROOT / "data/curated/gdelt_precision.json").read_text())
    doc_complete = gdelt_manifest.get("evidence_status") in {"confirmed", "confirmed_with_visible_source_gaps"}
    gkg_eligible = {
        club for club, state in gkg_precision.get("club_precision", {}).items()
        if state.get("quantification_status") == "confirmed"
    }
    if model.get("status") != "confirmed" or (not doc_complete and not gkg_eligible):
        raise RuntimeError("Web release requires a confirmed two-channel model and at least one precision-qualified GDELT panel")
    APP_DATA.mkdir(parents=True, exist_ok=True)
    for name in STALE_APP_FILES:
        (APP_DATA / name).unlink(missing_ok=True)
    downloads = ROOT / "app/downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "METHODOLOGY.md", downloads / "METHODOLOGY.md")
    shutil.copyfile(ROOT / "SOURCE_LEDGER.csv", downloads / "SOURCE_LEDGER.csv")
    memo_output = ROOT / "outputs/memos"
    if memo_output.exists():
        shutil.copytree(memo_output, ROOT / "app/memos", dirs_exist_ok=True)

    moments = json.loads((ROOT / "data/curated/moment.json").read_text())
    attention = json.loads((ROOT / "data/curated/attention_daily.json").read_text())
    if doc_complete:
        attention.extend(json.loads((ROOT / "data/curated/gdelt_attention_daily.json").read_text()))
        gdelt_mode = "doc_timeline_exact_name"
        gdelt_eligible_clubs = sorted(gdelt_precision.get("club_precision", {}))
        gdelt_unavailable_clubs = []
    else:
        attention.extend(
            row for row in json.loads((ROOT / "data/curated/gdelt_gkg_attention_daily.json").read_text())
            if row["club_id"] in gkg_eligible and row.get("normalized_articles_per_100k") is not None
        )
        gdelt_mode = "gkg_exact_name_club_level_precision_gate"
        gdelt_eligible_clubs = sorted(gkg_eligible)
        gdelt_unavailable_clubs = sorted(set(gkg_precision.get("club_precision", {})) - gkg_eligible)
    videos = json.loads((ROOT / "data/curated/content_video.json").read_text())
    publications = json.loads((ROOT / "data/curated/youtube_event_publication.json").read_text())
    historical_comments = json.loads((ROOT / "data/curated/youtube_historical_comment_event.json").read_text())
    comment_manifest = json.loads((ROOT / "data/manifests/youtube_historical_comment_acquisition.json").read_text())
    traces = build_signal_traces(moments, attention)
    youtube = youtube_summary(videos, publications, historical_comments, comment_manifest)

    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        club_configs = list(csv.DictReader(handle))
    current_clubs = {row["club_id"] for row in club_configs}
    stable = [row for row in model["cross_channel_assessments"] if row["stable"] and row["club_id"] in current_clubs]
    stable_counts = Counter(row["moment_type"] for row in stable)
    league_summary = {
        "as_of": "2026-08-03",
        "club_count": 32,
        "taxonomy_version": "1.1.0",
        "model_version": model["model_version"],
        "stable_cell_count": len(stable),
        "stable_cells_by_moment": dict(sorted(stable_counts.items())),
        "gdelt_interval_coverage": {
            "mode": gdelt_mode,
            "eligible_clubs": len(gdelt_eligible_clubs),
            "eligible_club_ids": gdelt_eligible_clubs,
            "unavailable_club_ids": gdelt_unavailable_clubs,
            "doc_archived": gdelt_manifest.get("archived_response_count", gdelt_manifest.get("confirmed_intervals", 0)),
            "doc_planned": gdelt_manifest.get("planned_intervals", 0),
            "source_unavailable_days": gdelt_manifest.get("source_unavailable_day_count", gkg_manifest.get("missing_source_date_count", 0)),
        },
        "source_coverage": {
            "nhl_gamecenter": "confirmed",
            "moneypuck": "confirmed",
            "wikimedia": "confirmed",
            "gdelt": gdelt_manifest["evidence_status"] if doc_complete else gkg_manifest["evidence_status"],
            "youtube": "confirmed_current_snapshot",
            "youtube_event_time": "confirmed_publication_and_surviving_comment_timestamps",
            "market_context": "confirmed_with_labelled_suppression_fallbacks",
        },
        "stable_rule": "Both channels have at least 10 modeled and 10 isolated observations; modeled and club-local raw medians agree in direction; every modeled and raw 95% interval excludes zero.",
        "commercial_guardrail": "No attendance, revenue, sponsor value, conversion, CRM behavior, renewal probability, or fan identity is inferred.",
    }
    write_json("app/data/league_summary.json", league_summary)
    profiles = json.loads((ROOT / "data/curated/club_profiles.json").read_text())
    games = json.loads((ROOT / "data/curated/game.json").read_text())
    event_windows = json.loads((ROOT / "data/curated/attention_event_window.json").read_text())
    playbooks = json.loads((ROOT / "data/curated/activation_playbook.json").read_text())
    market = json.loads((ROOT / "data/curated/market_context.json").read_text())
    profile_by_club = {row["club_id"]: row for row in profiles}
    config_by_club = {row["club_id"]: row for row in club_configs}
    club_index = []
    club_files = []
    clubs_dir = APP_DATA / "clubs"
    clubs_dir.mkdir(parents=True, exist_ok=True)
    for club in sorted(current_clubs):
        profile = profile_by_club[club]
        club_index.append({key: profile[key] for key in ("club_id", "club_name", "club_slug", "club_accent", "country", "market_name")})
        club_moments = [row for row in moments if row["club_id"] == club]
        game_ids = {row.get("game_id") for row in club_moments if row.get("game_id")}
        bundle = {
            "profile": {key: value for key, value in profile.items() if key not in {"cross_channel_assessments", "finding_evidence"}},
            "moments": club_moments,
            "games": [
                {key: row.get(key) for key in ("game_id", "home_club_id", "away_club_id", "final_state", "source_url")}
                for row in games if row["game_id"] in game_ids
            ],
            "event_windows": [row for row in event_windows if row["club_id"] == club],
            "model": {
                "model_version": model["model_version"],
                "estimates": [row for row in model["estimates"] if row["club_id"] == club],
                "cross_channel_assessments": [row for row in model["cross_channel_assessments"] if row["club_id"] == club],
            },
            "playbooks": [row for row in playbooks if row["club_id"] == club],
            "market": [row for row in market if row["club_id"] == club],
            "traces": [row for row in traces if row["club_id"] == club],
            "youtube": [row for row in youtube if row["club_id"] == club],
            "memo_path": f"/memos/{config_by_club[club]['club_slug']}/",
        }
        relative = f"clubs/{profile['club_slug']}.json"
        write_json(f"app/data/{relative}", bundle)
        club_files.append(relative)
    write_json("app/data/club_index.json", club_index)
    release_files = ["club_index.json", "league_summary.json"] + club_files
    manifest = {
        "evidence_status": "confirmed_with_visible_source_gaps" if gdelt_unavailable_clubs else "confirmed",
        "created_at": "2026-08-03T00:00:00Z",
        "club_count": 32,
        "model_version": model["model_version"],
        "taxonomy_version": "1.1.0",
        "files": release_files,
        "file_checksums": {
            name: checksum(APP_DATA / name)
            for name in release_files
        },
        "static_checksums": {
            name: checksum(ROOT / "app" / name)
            for name in ("index.html", "explore/index.html", "app.js", "styles.css", "historical.css", "accessibility.css", "favicon.svg")
        },
        "signal_trace_count": len(traces),
        "youtube_club_count": 32,
        "delivery_mode": "per_club_route_bundle",
        "gdelt_source_mode": gdelt_mode,
        "gdelt_eligible_club_count": len(gdelt_eligible_clubs),
        "gdelt_unavailable_clubs": gdelt_unavailable_clubs,
    }
    return write_json("data/manifests/web_release.json", manifest)


if __name__ == "__main__":
    print(build())
