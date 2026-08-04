"""Archive NHL public responses; endpoints are undocumented and rate-limited deliberately."""
from __future__ import annotations
import csv, json, sys, time
from common import ROOT, archive_json, fetch_json, write_json, evidence_record
from analysis_window import SEASONS, club_active_in_season

def ingest(club_abbreviation: str, season: str) -> str:
    url = f"https://api-web.nhle.com/v1/club-schedule-season/{club_abbreviation}/{season}"
    payload, provenance = fetch_json(url)
    return str(archive_json("nhl", f"{club_abbreviation.lower()}-{season}-schedule", payload, provenance))

def ingest_game(game_id: str) -> dict:
    results = {}
    for kind, endpoint in {"boxscore":"boxscore", "play-by-play":"play-by-play"}.items():
        url=f"https://api-web.nhle.com/v1/gamecenter/{game_id}/{endpoint}"
        payload, provenance=fetch_json(url)
        results[kind]=str(archive_json("nhl", f"{game_id}-{kind}", payload, provenance))
        time.sleep(.2)
    return results

def season_start(season: str) -> int: return int(season[:4])

def plan_full_league(seasons=SEASONS) -> str:
    clubs=list(csv.DictReader((ROOT/"config/clubs.csv").open()))
    tasks=[]
    for row in clubs:
        for season in seasons:
            if not club_active_in_season(row["club_id"], season): continue
            tasks.append({"club_id":row["club_id"],"abbreviation":row["nhl_abbreviation"],"season":season,"endpoint":"club-schedule-season","evidence_status":"planned"})
    for season in seasons:
        if club_active_in_season("ARI", season):
            tasks.append({"club_id":"ARI","abbreviation":"ARI","season":season,"endpoint":"club-schedule-season","evidence_status":"planned","historical_only":True})
    return str(write_json("data/manifests/nhl_full_league_plan.json", {"source":evidence_record("nhl-public","planned", "Run schedules first; then enumerate game IDs and archive boxscore/play-by-play with 200ms pacing."),"tasks":tasks}))

def acquire_schedules_full_league() -> str:
    plan=json.loads((ROOT/"data/manifests/nhl_full_league_plan.json").read_text()) if (ROOT/"data/manifests/nhl_full_league_plan.json").exists() else json.loads((ROOT/plan_full_league()).read_text())
    results=[]
    for index, task in enumerate(plan["tasks"],1):
        target=ROOT/f"data/raw/nhl/{task['abbreviation'].lower()}-{task['season']}-schedule.json"
        try:
            path=str(target) if target.exists() else ingest(task["abbreviation"],task["season"])
            results.append({**task,"evidence_status":"confirmed","path":path})
        except Exception as exc:
            results.append({**task,"evidence_status":"unavailable","reason":type(exc).__name__})
        time.sleep(.25)
    return str(write_json("data/manifests/nhl_schedule_acquisition.json", {"source":evidence_record("nhl-public","confirmed"),"results":results}))

if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "--plan-full-league": print(plan_full_league())
    elif sys.argv[1:] == ["--acquire-schedules-full-league"]: print(acquire_schedules_full_league())
    elif sys.argv[1:] and sys.argv[1] == "--game": print(json.dumps(ingest_game(sys.argv[2]), indent=2))
    else: print(ingest(sys.argv[1], sys.argv[2]))
