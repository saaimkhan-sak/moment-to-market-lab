"""Resumable archival of NHL GameCenter boxscore and play-by-play evidence.

The public endpoints are undocumented.  This worker is deliberately sequential,
stores each original response, and records failures instead of substituting data.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
from pathlib import Path

from common import ROOT, evidence_record, write_json
from ingest_nhl import ingest_game


def selected_games(include_preseason: bool = False) -> list[dict]:
    rows = json.loads((ROOT / "data/curated/game.json").read_text())
    allowed = {1, 2, 3} if include_preseason else {2, 3}
    return [row for row in rows if row.get("game_type") in allowed and row.get("home_score") is not None]


def detail_exists(game_id: int) -> bool:
    raw = ROOT / "data/raw/nhl"
    return (raw / f"{game_id}-boxscore.json").exists() and (raw / f"{game_id}-play-by-play.json").exists()


def acquire(start: int = 0, limit: int | None = None, include_preseason: bool = False, workers: int = 4) -> Path:
    games = selected_games(include_preseason)
    missing = [game for game in games if not detail_exists(game["game_id"])]
    batch = missing[start : start + limit if limit is not None else None]
    results = []

    def fetch(position_game):
        position, game = position_game
        game_id = game["game_id"]
        try:
            paths = ingest_game(str(game_id))
            return {"game_id": game_id, "position": position, "evidence_status": "confirmed", "paths": paths}
        except Exception as exc:  # retain the gap; never fabricate a game event.
            return {"game_id": game_id, "position": position, "evidence_status": "unavailable", "reason": type(exc).__name__}

    indexed = list(enumerate(batch, start + 1))
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        futures = [pool.submit(fetch, item) for item in indexed]
        for future in as_completed(futures):
            results.append(future.result())
            # Four workers plus the per-game 200ms pause in ingest_game keeps
            # source pressure bounded while avoiding a multi-hour serial run.
            time.sleep(0.02)
    results.sort(key=lambda row: row["position"])
    manifest = {
        "source": evidence_record("nhl-gamecenter", "confirmed", "At most four workers; each game pauses between endpoints; failed games remain explicit and the run is resumable from archived files."),
        "selection": {"start": start, "limit": limit, "include_preseason": include_preseason, "workers": workers, "total_eligible": len(games), "already_complete": len(games)-len(missing), "missing_before_batch": len(missing)},
        "results": results,
    }
    return write_json(f"data/manifests/nhl_game_detail_batch_{start:05d}.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-preseason", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    print(acquire(args.start, args.limit, args.include_preseason, args.workers))
