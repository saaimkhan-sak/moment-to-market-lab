"""Registered objective moment rules; incomplete evidence fails closed."""
from __future__ import annotations
import csv, json, uuid
from common import ROOT, write_json

RULE_VERSION="1.1.0"

def final_result_moments(game: dict, club: str, opponent: str, score_for: int, score_against: int, rivalry: bool) -> list[str]:
    result=[]
    if rivalry: result.append("rivalry_win" if score_for>score_against else "rivalry_loss")
    if score_for>score_against and game.get("final_state")=="OT": result.append("overtime_win")
    if score_for>score_against and game.get("final_state")=="SO": result.append("shootout_win")
    return result

def boxscore_player_moments(player: dict) -> list[str]:
    result=[]
    if player.get("goals",0)>=3: result.append("hat_trick")
    if player.get("points",0)>=4: result.append("four_point_game")
    return result

def goalie_moment(goalie: dict) -> list[str]:
    return ["goalie_high_volume_shutout"] if goalie.get("shutout") is True and goalie.get("saves",0)>=40 else []

def comeback_moment(third_start_deficit: int | None, won: bool) -> bool:
    return third_start_deficit is not None and third_start_deficit>=2 and won

def official_announcement_moment(record: dict) -> str | None:
    allowed={"playoff_clinch","official_roster_event","community_or_heritage_event"}
    if record.get("moment_type") in allowed and record.get("evidence_status")=="confirmed" and record.get("source_url") and record.get("announcement_time_utc"): return record["moment_type"]
    return None

def build():
    games=json.loads((ROOT/'data/curated/game.json').read_text()) if (ROOT/'data/curated/game.json').exists() else []
    rivalry_rows=[]
    with (ROOT/'config/rivalries.csv').open() as handle:
        for row in csv.DictReader(handle):
            if row.get('evidence_status')!='confirmed' or not row.get('source_url'):
                continue
            rivalry_rows.append(row)

    def is_rivalry(club, opponent, game_time):
        day=game_time[:10]
        for row in rivalry_rows:
            if {club,opponent}!={row['club_id'],row['opponent_id']}:
                continue
            if row.get('valid_from') and day<row['valid_from']:
                continue
            if row.get('valid_to') and day>row['valid_to']:
                continue
            return True
        return False
    out=[]
    by_id={game['game_id']:game for game in games}
    for game in games:
        if game.get('game_type') not in {2,3}:
            continue
        for club,opp,own,their in [(game['home_club_id'],game['away_club_id'],game['home_score'],game['away_score']), (game['away_club_id'],game['home_club_id'],game['away_score'],game['home_score'])]:
            if own is None or their is None: continue
            for kind in final_result_moments(game, club, opp, own, their, is_rivalry(club,opp,game['start_time_utc'])):
                out.append({'moment_id':str(uuid.uuid5(uuid.NAMESPACE_URL, f"{game['game_id']}-{club}-{kind}")), 'club_id':club,'game_id':game['game_id'],'moment_type':kind,'moment_time_utc':game['start_time_utc'],'trigger_rule_id':kind,'rule_version':RULE_VERSION,'player_ids':[],'opponent_id':opp,'evidence_status':'confirmed','source_url':game['source_url']})
    # Player and goalie rules require an archived official boxscore.  A missing
    # GameCenter record simply yields no claim rather than a guessed result.
    for path in sorted((ROOT/'data/raw/nhl').glob('*-boxscore.json')):
        record=json.loads(path.read_text()); box=record['payload']; game=by_id.get(box.get('id'))
        if not game or game.get('game_type') not in {2,3}:
            continue
        for side,club in [('homeTeam',box.get('homeTeam',{}).get('abbrev')),('awayTeam',box.get('awayTeam',{}).get('abbrev'))]:
            stats=(box.get('playerByGameStats') or {}).get(side,{})
            for group in ('forwards','defense'):
                for player in stats.get(group,[]):
                    for kind in boxscore_player_moments(player):
                        out.append({'moment_id':str(uuid.uuid5(uuid.NAMESPACE_URL, f"{game['game_id']}-{club}-{kind}-{player.get('playerId')}")), 'club_id':club,'game_id':game['game_id'],'moment_type':kind,'moment_time_utc':game['start_time_utc'],'trigger_rule_id':kind,'rule_version':RULE_VERSION,'player_ids':[player.get('playerId')],'opponent_id':game['away_club_id'] if side=='homeTeam' else game['home_club_id'],'evidence_status':'confirmed','source_url':record['provenance']['source_url']})
            final_score=box.get(side,{}).get('score')
            opponent_score=box.get('awayTeam' if side=='homeTeam' else 'homeTeam',{}).get('score')
            for goalie in stats.get('goalies',[]):
                goalie_input={'shutout':opponent_score==0 and final_score>0,'saves':goalie.get('saves',0)}
                for kind in goalie_moment(goalie_input):
                    out.append({'moment_id':str(uuid.uuid5(uuid.NAMESPACE_URL, f"{game['game_id']}-{club}-{kind}-{goalie.get('playerId')}")), 'club_id':club,'game_id':game['game_id'],'moment_type':kind,'moment_time_utc':game['start_time_utc'],'trigger_rule_id':kind,'rule_version':RULE_VERSION,'player_ids':[goalie.get('playerId')],'opponent_id':game['away_club_id'] if side=='homeTeam' else game['home_club_id'],'evidence_status':'confirmed','source_url':record['provenance']['source_url']})
    # PBP establishes the score at the beginning of Period 3.  This rule is
    # emitted only where an archived period-start and final result are present.
    for path in sorted((ROOT/'data/raw/nhl').glob('*-play-by-play.json')):
        record=json.loads(path.read_text()); pbp=record['payload']; game=by_id.get(pbp.get('id'))
        if not game or game.get('game_type') not in {2,3}: continue
        third=None; running=(0,0)
        for play in pbp.get('plays',[]):
            period=(play.get('periodDescriptor') or {}).get('number')
            if period==3 and play.get('typeDescKey')=='period-start':
                third=running; break
            details=play.get('details') or {}
            if details.get('homeScore') is not None and details.get('awayScore') is not None:
                running=(details['homeScore'],details['awayScore'])
        if third is None: continue
        for club,own,their,at_start in [(game['home_club_id'],game['home_score'],game['away_score'],third[0]-third[1]),(game['away_club_id'],game['away_score'],game['home_score'],third[1]-third[0])]:
            if comeback_moment(-at_start, own>their):
                out.append({'moment_id':str(uuid.uuid5(uuid.NAMESPACE_URL, f"{game['game_id']}-{club}-two_goal_third_period_comeback_win")), 'club_id':club,'game_id':game['game_id'],'moment_type':'two_goal_third_period_comeback_win','moment_time_utc':game['start_time_utc'],'trigger_rule_id':'two_goal_third_period_comeback_win','rule_version':RULE_VERSION,'player_ids':[],'opponent_id':game['away_club_id'] if club==game['home_club_id'] else game['home_club_id'],'evidence_status':'confirmed','source_url':record['provenance']['source_url']})
    announcement_path=ROOT/'data/curated/official_announcement.json'
    if announcement_path.exists():
        for record in json.loads(announcement_path.read_text()):
            kind=official_announcement_moment(record)
            if not kind:
                continue
            source_key=record.get('announcement_id') or record['source_url']
            out.append({
                'moment_id':str(uuid.uuid5(uuid.NAMESPACE_URL,f"{record['club_id']}-{kind}-{source_key}")),
                'club_id':record['club_id'],
                'game_id':None,
                'moment_type':kind,
                'moment_time_utc':record['announcement_time_utc'],
                'trigger_rule_id':record.get('trigger_rule_id',kind),
                'rule_version':record.get('rule_version',RULE_VERSION),
                'player_ids':record.get('player_ids',[]),
                'opponent_id':record.get('opponent_id'),
                'evidence_status':'confirmed',
                'source_url':record['source_url'],
                'announcement_title':record.get('announcement_title'),
            })
    unique={row['moment_id']:row for row in out}
    return write_json('data/curated/moment.json',[unique[key] for key in sorted(unique)])
if __name__ == '__main__': print(build())
