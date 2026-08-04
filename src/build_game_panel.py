"""Normalize archived NHL schedules to the canonical game grain without inferring missing fields."""
from __future__ import annotations
import json
from pathlib import Path
from common import ROOT, write_json

def build() -> Path:
    by_game_id={}
    context_path=ROOT/'data/curated/moneypuck_game_context.json'
    moneypuck={row['game_id']:row for row in json.loads(context_path.read_text())} if context_path.exists() else {}
    for path in sorted((ROOT/'data/raw/nhl').glob('*-schedule.json')):
        record=json.loads(path.read_text()); p=record['payload']; provenance=record['provenance']
        for game in p.get('games', []):
            row={'game_id': game.get('id'), 'season': game.get('season'), 'game_type': game.get('gameType'), 'start_time_utc': game.get('startTimeUTC'), 'venue': (game.get('venue') or {}).get('default'), 'home_club_id': (game.get('homeTeam') or {}).get('abbrev'), 'away_club_id': (game.get('awayTeam') or {}).get('abbrev'), 'home_score': (game.get('homeTeam') or {}).get('score'), 'away_score': (game.get('awayTeam') or {}).get('score'), 'final_state': game.get('gameOutcome',{}).get('lastPeriodType'), 'source_url': provenance['source_url'], 'retrieved_at': provenance['retrieved_at']}
            game_id=row['game_id']
            if not game_id:
                continue
            existing=by_game_id.get(game_id)
            # A game is observed from each club's schedule. Preserve one canonical
            # row; fail if duplicate public responses disagree on material fields.
            comparable=('season','game_type','start_time_utc','home_club_id','away_club_id','home_score','away_score','final_state')
            if existing and any(existing[field] != row[field] for field in comparable):
                raise ValueError(f'Conflicting NHL schedule observations for game {game_id}')
            by_game_id[game_id]=row
    for game_id,row in by_game_id.items():
        if str(game_id) in moneypuck:
            row['moneypuck_context']=moneypuck[str(game_id)]
    return write_json('data/curated/game.json', [by_game_id[key] for key in sorted(by_game_id)])
if __name__ == '__main__': print(build())
