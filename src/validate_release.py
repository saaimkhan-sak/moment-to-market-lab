"""Fail-closed release audit for the full 32-club analytical product."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys

from common import ROOT, now_utc, write_json
from fit_attention_model import cross_channel_assessments
from validate_entity_mapping import validate as validate_entities


def load(path: str, fallback):
    target = ROOT / path
    return json.loads(target.read_text()) if target.exists() else fallback


def files_exist(paths: list[str]) -> bool:
    return all((ROOT / path).exists() for path in paths)


def code_checksum() -> str:
    digest = hashlib.sha256()
    paths = []
    for folder in ("src", "tests", "config", "app"):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file() and "app/data" not in str(path) and "app/memos" not in str(path))
    paths.extend(ROOT / name for name in ("package.json", "pyproject.toml", "METHODOLOGY.md", "DATA_DICTIONARY.md"))
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def main() -> int:
    required = [
        "data/curated/game.json",
        "data/curated/game_event.json",
        "data/curated/moment.json",
        "data/curated/official_announcement.json",
        "data/curated/attention_daily.json",
        "data/curated/gdelt_gkg_attention_daily.json",
        "data/curated/gdelt_gkg_release_precision.json",
        "data/curated/content_video.json",
        "data/curated/youtube_event_publication.json",
        "data/curated/youtube_historical_comment_event.json",
        "data/curated/evidence_coverage.json",
        "data/curated/moneypuck_game_context.json",
        "data/curated/nhl_moneypuck_reconciliation.json",
        "data/curated/market_context.json",
        "data/curated/club_moment_estimate.json",
        "data/curated/club_profiles.json",
        "data/curated/activation_playbook.json",
        "data/manifests/gdelt_gkg_release_acquisition.json",
        "data/manifests/youtube_complete_acquisition.json",
        "data/manifests/youtube_historical_comment_acquisition.json",
        "data/manifests/season_source_coverage.json",
        "data/manifests/official_announcement_acquisition.json",
        "data/manifests/web_release.json",
        "outputs/release_manifests/executive_memos.json",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    with (ROOT / "CLUB_REGISTRY.csv").open(newline="") as handle:
        clubs = list(csv.DictReader(handle))
    current_clubs = {row["club_id"] for row in clubs}
    games = load("data/curated/game.json", [])
    game_events = load("data/curated/game_event.json", [])
    moments = load("data/curated/moment.json", [])
    announcements = load("data/curated/official_announcement.json", [])
    videos = load("data/curated/content_video.json", [])
    youtube_manifest = load("data/manifests/youtube_complete_acquisition.json", {})
    youtube_publications = load("data/curated/youtube_event_publication.json", [])
    youtube_historical_comments = load("data/curated/youtube_historical_comment_event.json", [])
    youtube_comment_manifest = load("data/manifests/youtube_historical_comment_acquisition.json", {})
    reconciliation = load("data/curated/nhl_moneypuck_reconciliation.json", {})
    moneypuck = load("data/curated/moneypuck_game_context.json", [])
    market = load("data/curated/market_context.json", [])
    qcew = [row for row in market if row.get("metric_name", "").startswith("qcew_lq_")]
    preferred = [row for row in market if row.get("metric_name", "").startswith("preferred_industry_lq_")]
    gdelt_precision = load("data/curated/gdelt_gkg_release_precision.json", {})
    gdelt_release = load("data/manifests/gdelt_gkg_release_acquisition.json", {})
    gdelt_rows = load("data/curated/gdelt_gkg_attention_daily.json", [])
    wikimedia_rows = load("data/curated/attention_daily.json", [])
    model = load("data/curated/club_moment_estimate.json", {})
    playbooks = load("data/curated/activation_playbook.json", [])
    profiles = load("data/curated/club_profiles.json", [])
    memos = load("outputs/release_manifests/executive_memos.json", {})
    web = load("data/manifests/web_release.json", {})
    wikimedia_manifest = load("data/manifests/wikimedia_pageview_acquisition.json", {})
    key_audit = load("data/manifests/canonical_key_audit.json", {})
    source_coverage = load("data/curated/evidence_coverage.json", [])
    source_coverage_manifest = load("data/manifests/season_source_coverage.json", {})
    unexpected_public_files = sorted(
        path.name for path in (ROOT / "app/data").iterdir()
        if path.is_file() and path.name not in {"club_index.json", "league_summary.json"}
    )

    game_map = {row.get("game_id"): row for row in games}
    official_counts = Counter(row.get("moment_type") for row in announcements)
    rivalry_rows = list(csv.DictReader((ROOT / "config/rivalries.csv").open(newline="")))
    rivalry_clubs = {row["club_id"] for row in rivalry_rows} | {row["opponent_id"] for row in rivalry_rows}
    required_context = {
        "home_xg_all", "away_xg_all", "home_xg_share_all",
        "home_xg_while_leading", "home_xg_while_tied", "home_xg_while_trailing",
        "away_xg_while_leading", "away_xg_while_tied", "away_xg_while_trailing",
    }
    channel_models = model.get("channel_models", [])
    stable_rows = model.get("cross_channel_assessments", [])
    recomputed_stability = cross_channel_assessments(model.get("estimates", []))
    event_windows = load("data/curated/attention_event_window.json", [])
    memo_records = memos.get("records", [])
    memo_files_ok = bool(memo_records) and all(
        row.get("slide_count") == 5
        and (ROOT / row.get("json_path", "")).exists()
        and (ROOT / row.get("html_path", "")).exists()
        and hashlib.sha256((ROOT / row.get("json_path", "")).read_bytes()).hexdigest() == row.get("json_checksum")
        and hashlib.sha256((ROOT / row.get("html_path", "")).read_bytes()).hexdigest() == row.get("html_checksum")
        for row in memo_records
    )
    web_files_ok = bool(web.get("file_checksums")) and all(
        (ROOT / "app/data" / name).exists()
        and hashlib.sha256((ROOT / "app/data" / name).read_bytes()).hexdigest() == digest
        for name, digest in web.get("file_checksums", {}).items()
    ) and all(
        (ROOT / "app" / name).exists()
        and hashlib.sha256((ROOT / "app" / name).read_bytes()).hexdigest() == digest
        for name, digest in web.get("static_checksums", {}).items()
    )
    playbook_clubs = Counter(row.get("club_id") for row in playbooks)
    action_fingerprints = {
        hashlib.sha256("|".join(str(row.get(key, "")) for key in ("moment_type", "action_0_24h", "action_24_72h", "action_day_4_7")).encode()).hexdigest()
        for row in playbooks
    }
    club_content_contexts = {
        row.get("club_id"): hashlib.sha256(json.dumps(row.get("official_content_context", {}), sort_keys=True).encode()).hexdigest()
        for row in playbooks
    }
    stability_rule = "both channels have at least 10 modeled and 10 isolated observations; modeled and club-local raw medians share direction across channels; every modeled and raw 95% interval excludes zero"
    announcement_keys = {
        (row.get("club_id"), row.get("moment_type"), row.get("announcement_time_utc"), row.get("source_url"))
        for row in announcements
    }
    materialized_announcement_keys = {
        (row.get("club_id"), row.get("moment_type"), row.get("moment_time_utc"), row.get("source_url"))
        for row in moments if row.get("moment_type") in {"playoff_clinch", "official_roster_event", "community_or_heritage_event"}
    }

    gates = {
        "registry_exactly_32_current_clubs": len(clubs) == 32 and len(current_clubs) == 32,
        "canonical_game_event_keys_unique": (
            key_audit.get("evidence_status") == "confirmed"
            and key_audit.get("game_count") == len(games)
            and key_audit.get("event_count") == key_audit.get("unique_event_key_count")
            and key_audit.get("duplicate_event_key_count") == 0
            and key_audit.get("missing_event_key_count") == 0
            and key_audit.get("orphan_game_id_count") == 0
        ),
        "canonical_moment_attention_keys_unique": (
            len(moments) == len({row.get("moment_id") for row in moments})
            and all(row.get("moment_id") and (not row.get("game_id") or row.get("game_id") in game_map) for row in moments)
            and len(wikimedia_rows) == len({(row.get("club_id"), row.get("entity_id"), row.get("date_utc"), row.get("channel"), row.get("metric_name")) for row in wikimedia_rows})
            and len(gdelt_rows) == len({(row.get("club_id"), row.get("mapping_id"), row.get("date_utc"), row.get("channel"), row.get("metric_name")) for row in gdelt_rows})
            and all(row.get("metric_value") is not None for row in wikimedia_rows)
            and all(
                row.get("metric_value") is not None
                or (
                    row.get("evidence_quality") == "unavailable_source_partition_gap"
                    and row.get("unavailable_reason") == "gdelt_gkg_no_web_records_for_date"
                )
                for row in gdelt_rows
            )
        ),
        "entity_validity_and_archives_are_auditable": validate_entities(),
        "youtube_all_accessible_uploads_32_clubs": (
            youtube_manifest.get("completed_clubs") == 32
            and len(youtube_manifest.get("results", [])) == 32
            and all(row.get("evidence_status") == "confirmed" for row in youtube_manifest.get("results", []))
            and all(
                row.get("playlist_video_ids") == row.get("accessible_videos", 0) + row.get("inaccessible_or_deleted_videos", 0)
                and row.get("playlist_pages", 0) > 0
                and row.get("video_detail_pages", 0) > 0
                and row.get("uploads_playlist_id", "").startswith("UU")
                for row in youtube_manifest.get("results", [])
            )
            and len(videos) == sum(row.get("accessible_videos", 0) for row in youtube_manifest.get("results", []))
            and len(videos) == len({(row.get("club_id"), row.get("video_id")) for row in videos})
            and {row.get("club_id") for row in videos} == current_clubs
        ),
        "youtube_historical_layer_is_event_time_only": (
            bool(youtube_publications)
            and youtube_comment_manifest.get("target_count", 0) > 0
            and youtube_comment_manifest.get("missing_targets") == 0
            and youtube_comment_manifest.get("confirmed_targets", 0) + youtube_comment_manifest.get("unavailable_targets", 0) == youtube_comment_manifest.get("target_count")
            and all(row.get("metric_scope") == "official_club_upload_publication_only" for row in youtube_publications)
            and all(not any(key in row for key in ("view_count", "like_count", "comment_count", "subscriber_count")) for row in youtube_publications)
            and all(row.get("metric_scope") == "surviving_top_level_public_comments_only" for row in youtube_historical_comments)
        ),
        "preseason_excluded_from_event_and_moment_panels": (
            all(game_map.get(row.get("game_id"), {}).get("game_type") in {2, 3} for row in game_events)
            and all(not row.get("game_id") or game_map.get(row["game_id"], {}).get("game_type") in {2, 3} for row in moments)
            and all(not row.get("game_id") or game_map.get(row["game_id"], {}).get("game_type") in {2, 3} for row in event_windows)
        ),
        "moneypuck_full_reconciliation_and_context": (
            reconciliation.get("status") == "confirmed"
            and reconciliation.get("sample_size", 0) >= 14000
            and reconciliation.get("match_rate", 0) >= reconciliation.get("minimum_match_rate", 1)
            and reconciliation.get("missing_moneypuck_games") == 0
            and reconciliation.get("team_mismatches") == 0
            and len(moneypuck) == reconciliation.get("sample_size")
            and all(
                required_context.issubset(row)
                and row.get("evidence_status") == "confirmed"
                and all(row.get(field) is not None for field in required_context)
                for row in moneypuck
            )
        ),
        "official_announcement_classes_and_roster_coverage": (
            official_counts.get("official_roster_event") == 32
            and official_counts.get("playoff_clinch", 0) > 0
            and official_counts.get("community_or_heritage_event", 0) > 0
            and {row.get("club_id") for row in announcements if row.get("moment_type") == "official_roster_event"} == current_clubs
            and all(row.get("evidence_status") == "confirmed" and row.get("timestamp_semantics") == "official_publication_time_not_inferred_transaction_time" for row in announcements)
            and announcement_keys == materialized_announcement_keys
        ),
        "sourced_rivalries_cover_32_clubs": (
            rivalry_clubs == current_clubs
            and len(rivalry_rows) == len({tuple(sorted((row.get("club_id"), row.get("opponent_id")))) for row in rivalry_rows})
            and all(
                row.get("club_id") != row.get("opponent_id")
                and row.get("rule_version") == "1.1.0"
                and row.get("valid_from")
                and row.get("source_note")
                and row.get("evidence_status") == "confirmed"
                and row.get("source_url", "").startswith("https://")
                for row in rivalry_rows
            )
        ),
        "market_context_32_clubs": {row.get("club_id") for row in market} == current_clubs,
        "qcew_suppression_preserved_with_labelled_fallback": (
            len(qcew) == 250
            and sum(row.get("evidence_status") == "unavailable" and row.get("unavailable_reason") == "bls_confidentiality_suppression" for row in qcew) == 36
            and len(preferred) == 250
            and sum(row.get("fallback_used") is True for row in preferred) == 36
            and all(row.get("evidence_status") == "confirmed" and row.get("metric_value") is not None for row in preferred)
        ),
        "gdelt_manual_precision_audit_eligible_32": (
            gdelt_precision.get("status") == "audit_complete"
            and gdelt_precision.get("active_extraction_reviewed_articles", 0) >= 160
            and gdelt_precision.get("clubs_eligible_for_quantification") == 32
            and not gdelt_precision.get("ineligible_clubs")
            and all(
                gdelt_precision.get("club_precision", {}).get(club, {}).get("quantification_status") == "confirmed"
                for club in current_clubs
            )
        ),
        "gdelt_daily_panel_complete_with_visible_source_gaps": (
            gdelt_release.get("evidence_status") in {"confirmed", "confirmed_with_visible_source_gaps"}
            and gdelt_release.get("daily_rows") == len(gdelt_rows)
            and gdelt_release.get("club_identity_count") == 33
            and gdelt_release.get("current_clubs_eligible_for_quantification") == 32
            and all(
                (row.get("metric_value") is not None and row.get("normalized_articles_per_100k") is not None)
                or row.get("evidence_quality") == "unavailable_source_partition_gap"
                for row in gdelt_rows
            )
        ),
        "club_season_source_coverage_is_explicit": (
            bool(source_coverage)
            and source_coverage_manifest.get("club_season_rows") == len(source_coverage)
            and {row.get("club_id") for row in source_coverage} == current_clubs
            and min(row["season"] for row in source_coverage if row["club_id"] == "VGK") == "20172018"
            and min(row["season"] for row in source_coverage if row["club_id"] == "SEA") == "20212022"
            and min(row["season"] for row in source_coverage if row["club_id"] == "UTA") == "20242025"
            and all(row.get("evidence_status") in {"confirmed", "confirmed_with_visible_source_gaps"} for row in source_coverage)
        ),
        "two_channel_hierarchical_model_converged": (
            model.get("model_version") == "2.0.0-unbalanced-multichannel-hierarchical"
            and model.get("status") == "confirmed"
            and model.get("converged") is True
            and set(model.get("channels", [])) == {"wikimedia_pageviews", "gdelt_earned_media"}
            and len(channel_models) == 2
            and {row.get("attention_channel") for row in channel_models} == {"wikimedia_pageviews", "gdelt_earned_media"}
            and all(
                row.get("converged")
                and row.get("n_daily_observations", 0) > 0
                and row.get("baseline_days") == 14
                and row.get("opponent_control") == "crossed random intercept"
                and set(row.get("sensitivity_estimates", {})) == {"7", "21"}
                for row in channel_models
            )
        ),
        "cross_channel_stability_rule_enforced": bool(stable_rows) and stable_rows == recomputed_stability and all(
            row.get("stable") == (row.get("cross_channel_status") in {"stable_positive", "stable_negative"})
            and (not row.get("stable") or row.get("rule") == stability_rule)
            for row in stable_rows
        ),
        "small_samples_suppressed": bool(model.get("estimates")) and all(
            not row.get("ranking_eligible") for row in model.get("estimates", []) if row.get("sample_size", 0) < 10 or row.get("isolated_sample_size", 0) < 10
        ),
        "club_profiles_and_differentiated_playbooks": (
            len(profiles) == 32
            and {row.get("club_id") for row in profiles} == current_clubs
            and len(playbooks) == 96
            and all(playbook_clubs[club] == 3 for club in current_clubs)
            and len(action_fingerprints) >= 32
            and len(club_content_contexts) == 32
            and len(set(club_content_contexts.values())) == 32
            and all(row.get("official_content_context", {}).get("accessible_video_count", 0) > 0 for row in playbooks)
            and all("club_local_channel_evidence" in row.get("evidence", {}) for row in playbooks)
            and all(row.get("requires_internal_validation") is True and row.get("owner_function") and row.get("public_kpi") and row.get("internal_kpi") and row.get("guardrails") for row in playbooks)
        ),
        "five_slide_memos_for_32_clubs": memos.get("memo_count") == 32 and memos.get("slides_per_memo") == 5 and memo_files_ok and len({row.get("analytical_signature") for row in memo_records}) == 32,
        "final_web_release_assembled": (
            web.get("evidence_status") in {"confirmed", "confirmed_with_visible_source_gaps"}
            and web.get("club_count") == 32
            and web.get("youtube_club_count") == 32
            and web.get("model_version") == model.get("model_version")
            and web.get("taxonomy_version") == "1.1.0"
            and web_files_ok
            and files_exist(["app/index.html", "app/app.js", "app/styles.css", "app/historical.css", "app/accessibility.css", "vercel.json"])
            and not unexpected_public_files
        ),
    }
    status = "pass" if not missing and all(gates.values()) else "fail"
    requirement_evidence = {
        "youtube_complete_upload_archives": {
            "clubs": youtube_manifest.get("completed_clubs"),
            "playlist_video_ids": sum(row.get("playlist_video_ids", 0) for row in youtube_manifest.get("results", [])),
            "accessible_videos_materialized": len(videos),
            "inaccessible_or_deleted_video_ids": sum(row.get("inaccessible_or_deleted_videos", 0) for row in youtube_manifest.get("results", [])),
        },
        "entity_validity": {
            "winnipeg_entity_id": "Q472741",
            "arizona_valid_through": "2024-06-30",
            "utah_hockey_club_valid_through": "2025-05-06",
            "utah_mammoth_valid_from": "2025-05-07",
        },
        "preseason_exclusion": {
            "game_events": len(game_events),
            "moments": len(moments),
            "attention_event_windows": len(event_windows),
            "preseason_records_in_these_panels": 0 if gates["preseason_excluded_from_event_and_moment_panels"] else None,
        },
        "moneypuck": {
            "reconciled_games": reconciliation.get("matched"),
            "context_rows": len(moneypuck),
            "required_xg_and_game_state_fields": sorted(required_context),
        },
        "gdelt": {
            "daily_rows": len(gdelt_rows),
            "club_identities": len({row.get("club_id") for row in gdelt_rows}),
            "current_clubs_precision_eligible": gdelt_precision.get("clubs_eligible_for_quantification"),
            "active_extraction_reviewed_articles": gdelt_precision.get("active_extraction_reviewed_articles"),
            "visible_source_gap_dates": gdelt_release.get("missing_source_date_count"),
        },
        "official_announcements": {
            "records": len(announcements),
            "current_clubs_with_roster_event": len({row.get("club_id") for row in announcements if row.get("moment_type") == "official_roster_event"}),
            "materialized_moment_records": len(materialized_announcement_keys),
        },
        "rivalries": {"sourced_pairs": len(rivalry_rows), "covered_current_clubs": len(rivalry_clubs)},
        "model": {
            "channels": model.get("channels", []),
            "daily_observations_by_channel": {row.get("attention_channel"): row.get("n_daily_observations") for row in channel_models},
            "cross_channel_cells": len(stable_rows),
            "stable_cells": sum(row.get("stable") is True for row in stable_rows),
        },
        "differentiated_outputs": {
            "club_profiles": len(profiles),
            "playbooks": len(playbooks),
            "unique_action_fingerprints": len(action_fingerprints),
            "unique_club_content_contexts": len(set(club_content_contexts.values())),
            "memos": memos.get("memo_count"),
            "unique_memo_analytical_signatures": len({row.get("analytical_signature") for row in memo_records}),
        },
        "web_release": {
            "club_route_bundles": len(web.get("files", [])) - 2,
            "unexpected_top_level_public_data_files": unexpected_public_files,
        },
    }
    manifest = {
        "release_id": "moment-to-market-2026-08-03-v1.1-local",
        "created_at": now_utc(),
        "club_count": len(clubs),
        "taxonomy_version": "1.1.0",
        "model_version": model.get("model_version", "unavailable"),
        "source_contract_version": "1.1.0",
        "code_version": code_checksum(),
        "source_dates": {
            "nhl_and_moneypuck": reconciliation.get("source", {}).get("retrieved_at"),
            "youtube": max((row.get("retrieved_at", "") for row in youtube_manifest.get("results", [])), default=None),
            "wikimedia": wikimedia_manifest.get("source", {}).get("retrieved_at"),
            "gdelt": max((row.get("retrieved_at", "") for row in gdelt_rows), default=None),
            "market": max((row.get("retrieved_at", "") for row in market), default=None),
        },
        "missing_required_outputs": missing,
        "quality_gates": gates,
        "requirement_evidence": requirement_evidence,
        "gate_failures": [name for name, passed in gates.items() if not passed],
        "status": status,
        "caveat": "Public-attention associations are descriptive, not causal or commercial outcomes. GDELT is earned-media volume, not sentiment. YouTube views, likes, comments, and subscribers are current public snapshots; only upload and surviving top-level comment timestamps enter the historical descriptive layer. QCEW suppression remains visible and ACS fallbacks remain separately labelled.",
    }
    write_json("outputs/release_manifests/full-league-v1.1.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
