"""Build evidence-first club profiles from the final multichannel model."""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json

from common import ROOT, write_json


def display(value: str) -> str:
    return value.replace("_", " ")


def assessment_candidates(model: dict, club: str) -> list[dict]:
    estimates = {
        (row["club_id"], row["moment_type"], row["post_window"], row["attention_channel"]): row
        for row in model["estimates"]
    }
    candidates = []
    for assessment in model["cross_channel_assessments"]:
        if assessment["club_id"] != club:
            continue
        channel_rows = [
            estimates.get((club, assessment["moment_type"], assessment["post_window"], channel))
            for channel in assessment["required_channels"]
        ]
        if any(row is None for row in channel_rows):
            continue
        raw_values = [row["raw_median_lift"] for row in channel_rows if row.get("raw_median_lift") is not None]
        model_values = [row["estimate"] for row in channel_rows if row.get("estimate") is not None]
        candidates.append({
            **assessment,
            "channel_estimates": channel_rows,
            "minimum_sample_size": min(row["sample_size"] for row in channel_rows),
            "minimum_isolated_sample_size": min(row.get("isolated_sample_size", 0) for row in channel_rows),
            "local_raw_mean": sum(raw_values) / len(raw_values) if raw_values else None,
            "modeled_mean": sum(model_values) / len(model_values) if model_values else None,
        })
    return candidates


def choose_finding(candidates: list[dict]) -> dict | None:
    stable = [row for row in candidates if row["cross_channel_status"] == "stable_positive"]
    if not stable:
        return None
    return max(stable, key=lambda row: (row.get("local_raw_mean") or -10**9, row["minimum_sample_size"]))


def build():
    games = json.loads((ROOT / "data/curated/game.json").read_text())
    moments = json.loads((ROOT / "data/curated/moment.json").read_text())
    attention = json.loads((ROOT / "data/curated/attention_daily.json").read_text())
    doc_manifest = json.loads((ROOT / "data/manifests/gdelt_timeline_acquisition.json").read_text())
    doc_complete = doc_manifest.get("evidence_status") in {"confirmed", "confirmed_with_visible_source_gaps"}
    if doc_complete:
        gdelt_attention = json.loads((ROOT / "data/curated/gdelt_attention_daily.json").read_text())
        gdelt_precision = json.loads((ROOT / "data/curated/gdelt_precision.json").read_text())
        gdelt_source_label = "GDELT DOC TimelineVolRaw with manual precision audit"
    else:
        gdelt_precision = json.loads((ROOT / "data/curated/gdelt_gkg_release_precision.json").read_text())
        eligible = {
            club for club, state in gdelt_precision["club_precision"].items()
            if state.get("quantification_status") == "confirmed"
        }
        gdelt_attention = [
            row for row in json.loads((ROOT / "data/curated/gdelt_gkg_attention_daily.json").read_text())
            if row["club_id"] in eligible and row.get("normalized_articles_per_100k") is not None
        ]
        gdelt_source_label = "GDELT GKG exact-name panel; club-level precision gate"
    model = json.loads((ROOT / "data/curated/club_moment_estimate.json").read_text())
    market = json.loads((ROOT / "data/curated/market_context.json").read_text())
    videos = json.loads((ROOT / "data/curated/content_video.json").read_text())
    if model.get("model_version") != "2.0.0-unbalanced-multichannel-hierarchical" or model.get("status") != "confirmed":
        raise RuntimeError("Club profiles require the confirmed two-channel model v2.0.0")

    moment_counts = Counter((row["club_id"], row["moment_type"]) for row in moments)
    attention_counts = Counter((row["club_id"], row["channel"]) for row in attention + gdelt_attention)
    video_counts = Counter(row["club_id"] for row in videos)
    market_counts = Counter(row["club_id"] for row in market if row["evidence_status"] == "confirmed")
    game_counts = Counter()
    for row in games:
        game_counts[row["home_club_id"]] += 1
        game_counts[row["away_club_id"]] += 1

    profiles = []
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        clubs = list(csv.DictReader(handle))
    for config in clubs:
        club = config["club_id"]
        candidates = assessment_candidates(model, club)
        top = choose_finding(candidates)
        if top:
            label = display(top["moment_type"])
            window = display(top["post_window"])
            finding = f"{label.capitalize()} showed a stable positive public-attention association in the {window} window."
            reason = "Wikimedia information demand and audited GDELT earned-media volume agree in modeled and club-local raw direction, with at least ten modeled and isolated observations per channel and every modeled and raw interval excluding zero."
            status = "stable_cross_channel_pattern"
            limitation = "This is a reproducible public-signal association, not causal evidence, ticket demand, sponsor value, conversion, or fan identity."
        else:
            finding = "No reliable two-channel public-response pattern is visible in the available sample. Do not operationalize a moment ranking."
            reason = "No club–moment–window cell clears the registered agreement, precision, and sample-size rules in both Wikimedia and GDELT."
            status = "no_reliable_pattern_yet"
            limitation = "Use the event docket to improve measurement coverage; do not substitute a single-channel result for the missing agreement."

        profiles.append({
            "club_id": club,
            "club_name": config["club_name"],
            "club_slug": config["club_slug"],
            "club_accent": config["club_accent"],
            "country": config["country"],
            "market_name": config["market_name"],
            "game_records": game_counts[club],
            "moment_records": sum(count for (candidate, _), count in moment_counts.items() if candidate == club),
            "moment_type_counts": {kind: count for (candidate, kind), count in sorted(moment_counts.items()) if candidate == club},
            "attention_days_by_channel": {
                "wikimedia_pageviews": attention_counts[(club, "wikimedia_pageviews")],
                "gdelt_earned_media": attention_counts[(club, "gdelt_earned_media")],
            },
            "finding_status": status,
            "finding": finding,
            "reason": reason,
            "finding_evidence": top,
            "cross_channel_assessments": candidates,
            "limitation": limitation,
            "youtube_current_snapshot_videos": video_counts[club],
            "youtube_limitation": "Public statistics are current at retrieval time; historical 24-hour and 72-hour video trajectories were not reconstructed.",
            "market_metrics_confirmed": market_counts[club],
            "gdelt_precision": gdelt_precision["club_precision"].get(club, {"quantification_status": "unavailable"}),
            "sources": [
                "NHL public GameCenter archives",
                "MoneyPuck downloadable CSVs",
                "Wikimedia Pageviews",
                gdelt_source_label,
                "Official YouTube Data API",
                "ACS/BEA/BLS or Statistics Canada",
            ],
            "as_of": "2026-08-03",
            "model_version": model["model_version"],
            "taxonomy_version": "1.1.0",
        })
    return write_json("data/curated/club_profiles.json", profiles)


if __name__ == "__main__":
    print(build())
