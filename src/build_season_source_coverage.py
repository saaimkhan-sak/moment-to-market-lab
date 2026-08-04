"""Build the auditable club-season source-coverage matrix for the release."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import csv
import json

from analysis_window import SEASONS, club_active_in_season
from common import ROOT, write_json


def parse_day(value: str) -> date:
    text = value[:10]
    if "-" in text:
        return date.fromisoformat(text)
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def season_bounds(season: str) -> tuple[date, date]:
    first = int(season[:4])
    return date(first, 7, 1), date(first + 1, 6, 30)


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def build():
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        clubs = list(csv.DictReader(handle))
    games = json.loads((ROOT / "data/curated/game.json").read_text())
    reconciliation = json.loads((ROOT / "data/curated/nhl_moneypuck_reconciliation.json").read_text())
    wikimedia = json.loads((ROOT / "data/curated/attention_daily.json").read_text())
    gdelt_path = ROOT / "data/curated/gdelt_gkg_attention_daily.json"
    gdelt = json.loads(gdelt_path.read_text()) if gdelt_path.exists() else []
    videos = json.loads((ROOT / "data/curated/content_video.json").read_text())

    context_games = {str(row["game_id"]) for row in json.loads((ROOT / "data/curated/moneypuck_game_context.json").read_text())}
    score_disagreement_games = {
        str(row["game_id"])
        for row in reconciliation.get("rows", [])
        if row.get("status") == "mismatch" and row.get("teams_match") is True
    }
    dates_by_source = defaultdict(set)
    for row in wikimedia:
        dates_by_source[(row["club_id"], "wikimedia_pageviews")].add(parse_day(row["date_utc"]))
    for row in gdelt:
        if row.get("metric_value") is not None:
            dates_by_source[(row["club_id"], "gdelt_earned_media")].add(parse_day(row["date_utc"]))
    videos_by_club = defaultdict(list)
    for row in videos:
        videos_by_club[row["club_id"]].append(parse_day(row["published_at"]))

    rows = []
    raw_root = ROOT / "data/raw/nhl"
    for club in clubs:
        club_id = club["club_id"]
        for season in SEASONS:
            if not club_active_in_season(club_id, season):
                continue
            start, end = season_bounds(season)
            expected_days = (end - start).days + 1
            club_games = [
                row for row in games
                if str(row.get("season")) == season
                and row.get("game_type") in {2, 3}
                and club_id in {row.get("home_club_id"), row.get("away_club_id")}
            ]
            game_ids = {str(row["game_id"]) for row in club_games}
            detail_games = sum(
                (raw_root / f"{game_id}-boxscore.json").exists()
                and (raw_root / f"{game_id}-play-by-play.json").exists()
                for game_id in game_ids
            )
            money_games = len(game_ids & context_games)
            score_disagreements = len(game_ids & score_disagreement_games)
            wikimedia_days = sum(start <= day <= end for day in dates_by_source[(club_id, "wikimedia_pageviews")])
            gdelt_days = sum(start <= day <= end for day in dates_by_source[(club_id, "gdelt_earned_media")])
            youtube_uploads = sum(start <= day <= end for day in videos_by_club[club_id])
            required_available = (
                bool(game_ids)
                and detail_games == len(game_ids)
                and money_games == len(game_ids)
                and wikimedia_days == expected_days
                and gdelt_days > 0
            )
            status = "confirmed" if required_available and gdelt_days == expected_days and score_disagreements == 0 else "confirmed_with_visible_source_gaps"
            rows.append({
                "club_id": club_id,
                "franchise_id": club["franchise_id"],
                "season": season,
                "season_start_utc": start.isoformat(),
                "season_end_utc": end.isoformat(),
                "evidence_status": status,
                "eligible_for_core_model": required_available,
                "nhl_games": len(game_ids),
                "nhl_gamecenter_detail_games": detail_games,
                "nhl_gamecenter_coverage": ratio(detail_games, len(game_ids)),
                "moneypuck_matched_games": money_games,
                "moneypuck_coverage": ratio(money_games, len(game_ids)),
                "moneypuck_score_disagreements": score_disagreements,
                "score_authority": "official_nhl_gamecenter",
                "wikimedia_observed_days": wikimedia_days,
                "wikimedia_expected_days": expected_days,
                "wikimedia_coverage": ratio(wikimedia_days, expected_days),
                "gdelt_observed_days": gdelt_days,
                "gdelt_expected_days": expected_days,
                "gdelt_coverage": ratio(gdelt_days, expected_days),
                "youtube_official_uploads": youtube_uploads,
                "youtube_role": "descriptive_event_time_publication_metadata_not_required_for_core_attention_model",
            })

    write_json("data/curated/evidence_coverage.json", rows)
    manifest = {
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "evidence_status": "confirmed" if all(row["evidence_status"] == "confirmed" for row in rows) else "confirmed_with_visible_source_gaps",
        "club_season_rows": len(rows),
        "current_clubs": len({row["club_id"] for row in rows}),
        "seasons": list(SEASONS),
        "eligible_club_seasons": sum(row["eligible_for_core_model"] for row in rows),
        "rows_with_visible_source_gaps": sum(row["evidence_status"] != "confirmed" for row in rows),
        "policy": "Expansion identities enter in their first active season. Arizona and Utah records are not silently merged. YouTube publication metadata is descriptive and does not gate the two-channel attention model.",
    }
    return write_json("data/manifests/season_source_coverage.json", manifest)


if __name__ == "__main__":
    print(build())
