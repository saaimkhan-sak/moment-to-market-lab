from __future__ import annotations
import json
import csv
from common import ROOT, write_json

def build():
    mappings={row['wikipedia_article']:row for row in csv.DictReader((ROOT/'config/entity_dictionary.csv').open()) if row.get('status')=='confirmed'}
    keyed={}
    for p in (ROOT/'data/raw/wikimedia').glob('*.json'):
        r=json.loads(p.read_text()); prov=r['provenance']; mapping=mappings.get(prov.get('article'))
        if not mapping:
            continue
        for x in r['payload'].get('items',[]):
            # The API omits dates with no returned observation. Preserve that
            # coverage gap by emitting only observed values rather than zeros.
            day=x['timestamp'][:8]; valid_from=(mapping.get('valid_from') or '0000-01-01').replace('-',''); valid_to=(mapping.get('valid_to') or '9999-12-31').replace('-','')
            if not valid_from<=day<=valid_to: continue
            row={'club_id':mapping['club_id'],'entity_id':mapping['entity_id'],'mapping_id':mapping.get('mapping_id'),'date_utc':day,'channel':'wikimedia_pageviews','metric_name':'views','metric_value':x.get('views'),'project_or_platform':prov['project'],'source_url':prov['source_url'],'retrieved_at':prov['retrieved_at'],'evidence_quality':'confirmed'}
            key=(row['club_id'],row['entity_id'],day,row['channel'],row['metric_name'])
            if key not in keyed or row['retrieved_at']>keyed[key]['retrieved_at']: keyed[key]=row
    return write_json('data/curated/attention_daily.json',[keyed[key] for key in sorted(keyed)])
if __name__ == '__main__': print(build())
