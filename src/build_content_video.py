"""Assemble the canonical 32-club official YouTube snapshot table."""
from __future__ import annotations
import csv, json
from common import ROOT, write_json

def build():
    rows=[]
    with (ROOT/'config/official_channel_registry.csv').open() as handle:
        registry=list(csv.DictReader(handle))
    for channel in registry:
        name=channel['official_youtube_handle'].lstrip('@').lower()
        path=ROOT/f'data/curated/youtube-{name}.json'
        if channel['evidence_status']!='confirmed' or not path.exists():
            continue
        for video in json.loads(path.read_text()):
            rows.append({'club_id':channel['club_id'],**video})
    return write_json('data/curated/content_video.json',rows)

if __name__=='__main__': print(build())
