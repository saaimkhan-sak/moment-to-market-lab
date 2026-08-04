"""Record MoneyPuck source/download metadata. Original CSV is retained unmodified when supplied."""
from __future__ import annotations
from pathlib import Path
import hashlib, shutil, sys, zipfile
from common import ROOT, now_utc, write_json

def ingest(csv_path: str, source_url: str, season: str) -> str:
    source = Path(csv_path); body = source.read_bytes()
    destination = ROOT / "data/raw/moneypuck" / source.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Historical archives may already have been downloaded directly into the
    # immutable raw-data directory.  Do not rewrite those bytes merely to add a
    # provenance manifest.
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    if source.name == "all_teams.csv":
        variables = ["gameId", "season", "team", "playerTeam", "opposingTeam", "home_or_away", "gameDate", "situation", "xGoalsFor", "xGoalsAgainst", "goalsFor", "goalsAgainst", "playoffGame"]
        contents = [source.name]
    else:
        variables = ["shotID", "game_id", "season", "team", "teamCode", "event", "goal", "period", "time", "isPlayoffGame", "xGoal", "shotWasOnGoal", "shotType", "homeTeamCode", "awayTeamCode"]
        with zipfile.ZipFile(source) as archive: contents = archive.namelist()
    return str(write_json(f"data/raw/moneypuck/{source.name}.manifest.json", {"source_url": source_url, "season": season, "retrieved_at": now_utc(), "checksum": hashlib.sha256(body).hexdigest(), "variables_used": variables, "archive_contents": contents, "methodology_caveat": "MoneyPuck public variables enrich hockey context; NHL public game data remains the source of record for reconciliation."}))

if __name__ == "__main__": print(ingest(*sys.argv[1:4]))
