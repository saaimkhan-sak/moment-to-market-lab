"""Full NHL/MoneyPuck reconciliation and reproducible game-context enrichment."""
from __future__ import annotations
import csv, io, json, zipfile
from collections import defaultdict
from common import ROOT, write_json, evidence_record
from analysis_window import SEASONS as ANALYSIS_SEASONS, season_label

SEASONS={season[:4] for season in ANALYSIS_SEASONS}
SITUATIONS={"all","5on5","5on4","4on5","other"}
MONEYPUCK_TO_NHL_CLUB_ID={"L.A":"LAK","N.J":"NJD","S.J":"SJS","T.B":"TBL"}

def club_id(value: str | None) -> str | None:
    return MONEYPUCK_TO_NHL_CLUB_ID.get(value, value)

def number(value):
    return float(value) if value not in {None,""} else None

def build_game_context() -> str:
    team_rows=defaultdict(dict)
    with (ROOT/"data/raw/moneypuck/all_teams.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row.get("season") not in SEASONS or row.get("situation") not in SITUATIONS: continue
            team_rows[row["gameId"]][(row["home_or_away"].lower(),row["situation"])]=row

    score_state=defaultdict(lambda:defaultdict(lambda:{"shot_attempts":0,"xg":0.0}))
    for season in sorted(SEASONS):
        archive_path=ROOT/f"data/raw/moneypuck/shots_{season}.zip"
        with zipfile.ZipFile(archive_path) as archive, archive.open(f"shots_{season}.csv") as binary:
            for shot in csv.DictReader(io.TextIOWrapper(binary,encoding="utf-8")):
                game_id=f"{season}0{int(shot['game_id']):05d}"
                side="home" if shot.get("team") == "HOME" or shot.get("isHomeTeam") in {"1","1.0","TRUE","True"} else "away"
                home_goals=int(float(shot.get("homeTeamGoals") or 0)); away_goals=int(float(shot.get("awayTeamGoals") or 0))
                own,other=(home_goals,away_goals) if side=="home" else (away_goals,home_goals)
                state="tied" if own==other else ("leading" if own>other else "trailing")
                cell=score_state[game_id][(side,state)];cell["shot_attempts"]+=1;cell["xg"]+=number(shot.get("xGoal")) or 0.0

    manifest=json.loads((ROOT/"data/raw/moneypuck/all_teams.csv.manifest.json").read_text())
    rows=[]
    for game_id,cells in sorted(team_rows.items()):
        home_all=cells.get(("home","all"));away_all=cells.get(("away","all"))
        if not home_all or not away_all: continue
        row={"game_id":game_id,"season":int(home_all["season"]),"home_club_id":club_id(home_all["playerTeam"]),"away_club_id":club_id(away_all["playerTeam"]),"home_goals_moneypuck":number(home_all["goalsFor"]),"away_goals_moneypuck":number(away_all["goalsFor"]),"playoff_game":home_all.get("playoffGame")=="1","source_url":manifest["source_url"],"retrieved_at":manifest["retrieved_at"],"evidence_status":"confirmed"}
        for situation in sorted(SITUATIONS):
            for side in ("home","away"):
                source=cells.get((side,situation),{})
                row[f"{side}_xg_{situation}"]=number(source.get("xGoalsFor"))
                row[f"{side}_shots_on_goal_{situation}"]=number(source.get("shotsOnGoalFor"))
        for side in ("home","away"):
            for state in ("leading","tied","trailing"):
                cell=score_state[game_id][(side,state)]
                row[f"{side}_shot_attempts_while_{state}"]=cell["shot_attempts"]
                row[f"{side}_xg_while_{state}"]=round(cell["xg"],6)
        total=(row["home_xg_all"] or 0)+(row["away_xg_all"] or 0)
        row["home_xg_share_all"]=row["home_xg_all"]/total if total else None
        row["home_xg_margin_all"]=(row["home_xg_all"]-row["away_xg_all"]) if row["home_xg_all"] is not None and row["away_xg_all"] is not None else None
        rows.append(row)
    return str(write_json("data/curated/moneypuck_game_context.json",rows))

def build_audit(sample_limit: int | None = None) -> str:
    if not (ROOT/"data/curated/moneypuck_game_context.json").exists(): build_game_context()
    games=[row for row in json.loads((ROOT/"data/curated/game.json").read_text()) if row.get("game_type") in {2,3}]
    context={row["game_id"]:row for row in json.loads((ROOT/"data/curated/moneypuck_game_context.json").read_text())}
    rows=[]
    for game in games:
        key=str(game["game_id"]);mp=context.get(key)
        if not mp:
            rows.append({"game_id":key,"status":"missing_moneypuck_game"});continue
        teams_match=(game["home_club_id"],game["away_club_id"])==(mp["home_club_id"],mp["away_club_id"])
        nhl_score=(game["home_score"],game["away_score"]);mp_score=(int(mp["home_goals_moneypuck"]),int(mp["away_goals_moneypuck"]))
        exact_score=nhl_score==mp_score
        shootout_adjusted=game.get("final_state")=="SO" and abs((nhl_score[0]-nhl_score[1])-(mp_score[0]-mp_score[1]))==1 and sum(nhl_score)-sum(mp_score)==1
        status="matched" if teams_match and (exact_score or shootout_adjusted) else "mismatch"
        rows.append({"game_id":key,"teams_match":teams_match,"nhl_score":list(nhl_score),"moneypuck_score":list(mp_score),"score_match":"exact" if exact_score else ("expected_shootout_adjustment" if shootout_adjusted else "mismatch"),"status":status})
    if sample_limit is not None: rows=rows[:sample_limit]
    counts={status:sum(row["status"]==status for row in rows) for status in {row["status"] for row in rows}}
    matched=counts.get("matched",0)
    match_rate=matched/len(rows) if rows else 0.0
    missing=counts.get("missing_moneypuck_game",0)
    team_mismatches=sum(row.get("teams_match") is False for row in rows)
    # Six 2019-20 MoneyPuck rows disagree with the official NHL final score,
    # while retaining the same clubs and game IDs. Preserve those records as
    # source disagreements. A full-panel audit passes only with complete joins,
    # no team mismatch, and at least 99.9% score agreement.
    status="confirmed" if rows and not missing and not team_mismatches and match_rate>=0.999 else "unavailable"
    season_scope=f"{season_label(ANALYSIS_SEASONS[0])} through {season_label(ANALYSIS_SEASONS[-1])}"
    return str(write_json("data/curated/nhl_moneypuck_reconciliation.json",{"source":evidence_record("nhl-public","confirmed"),"status":status,"scope":f"all NHL regular-season and playoff games in {season_scope}" if sample_limit is None else f"first {sample_limit} eligible games","sample_size":len(rows),"matched":matched,"match_rate":match_rate,"minimum_match_rate":0.999,"missing_moneypuck_games":missing,"team_mismatches":team_mismatches,"counts":counts,"rows":rows,"caveat":"Shootout-winning goals appear in NHL final scores but not MoneyPuck shot-derived goal totals and are classified as expected adjustments. Remaining source-score disagreements stay visible and NHL remains the official result source."}))

if __name__=="__main__":
    print(build_game_context());print(build_audit())
