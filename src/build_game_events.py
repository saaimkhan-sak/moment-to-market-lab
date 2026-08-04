"""Normalize archived NHL GameCenter play-by-play to the canonical event grain."""
from __future__ import annotations

import json
from common import ROOT, write_json


def clock_seconds(value: str | None) -> int | None:
    if not value or ':' not in value:
        return None
    minute, second=value.split(':', 1)
    return int(minute) * 60 + int(second)


def build():
    rows=[]
    seen=set()
    duplicate_keys=[]
    missing_key_count=0
    games=json.loads((ROOT/'data/curated/game.json').read_text())
    game_ids={row['game_id'] for row in games}
    eligible_game_ids={row['game_id'] for row in games if row.get('game_type') in {2,3}}
    orphan_game_ids=set()
    for path in sorted((ROOT/'data/raw/nhl').glob('*-play-by-play.json')):
        record=json.loads(path.read_text()); payload=record['payload']; provenance=record['provenance']
        game_id=payload.get('id')
        # The analytical event panel is regular season + playoffs only. Keep
        # archived preseason responses raw, but never normalize them downstream.
        if game_id not in eligible_game_ids:
            continue
        for play in payload.get('plays',[]):
            details=play.get('details') or {}; period=play.get('periodDescriptor') or {}
            player_ids=[details[key] for key in ('scoringPlayerId','assist1PlayerId','assist2PlayerId','blockingPlayerId','shootingPlayerId','goalieInNetId') if details.get(key) is not None]
            event_id=play.get('eventId')
            key=(game_id,event_id)
            if game_id is None or event_id is None:
                missing_key_count+=1
            elif key in seen:
                duplicate_keys.append({'game_id':game_id,'event_id':event_id})
            else:
                seen.add(key)
            if game_id not in game_ids:
                orphan_game_ids.add(game_id)
            rows.append({'game_id':game_id,'event_id':event_id,'club_id':details.get('eventOwnerTeamId'),'event_time_utc':payload.get('startTimeUTC'),'period':period.get('number'),'clock_seconds':clock_seconds(play.get('timeInPeriod')),'event_type':play.get('typeDescKey'),'event_subtype':play.get('secondaryType'),'score_for':None,'score_against':None,'home_score':details.get('homeScore'),'away_score':details.get('awayScore'),'player_ids':player_ids,'source_url':provenance['source_url'],'retrieved_at':provenance['retrieved_at']})
    audit={
        'evidence_status':'confirmed' if not duplicate_keys and not missing_key_count and not orphan_game_ids else 'failed',
        'game_count':len(game_ids),
        'event_count':len(rows),
        'unique_event_key_count':len(seen),
        'duplicate_event_key_count':len(duplicate_keys),
        'duplicate_event_keys':duplicate_keys[:100],
        'missing_event_key_count':missing_key_count,
        'orphan_game_id_count':len(orphan_game_ids),
        'orphan_game_ids':sorted(value for value in orphan_game_ids if value is not None),
        'key_contract':'game.game_id unique; game_event (game_id,event_id) unique and game_id references game',
    }
    write_json('data/manifests/canonical_key_audit.json',audit)
    if audit['evidence_status']!='confirmed':
        raise ValueError(f'Canonical key audit failed: {audit}')
    return write_json('data/curated/game_event.json', rows)


if __name__ == '__main__':
    print(build())
