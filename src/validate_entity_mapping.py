import csv, json
from datetime import date
from pathlib import Path
from common import ROOT
def validate():
    with (ROOT/'config/entity_dictionary.csv').open() as handle: rows=list(csv.DictReader(handle))
    required={'mapping_id','club_id','entity_id','wikipedia_article','valid_from','valid_to','status','reason','search_source_url','retrieved_at','search_archive','entity_archive'}
    if not rows or not required.issubset(rows[0]): return False
    for row in rows:
        if not row['club_id'] or row['status'] not in {'confirmed','unavailable'}: return False
        if row['status']=='confirmed' and not (row['entity_id'].startswith('Q') and row['wikipedia_article'] and row['entity_archive']): return False
        if row['status']=='confirmed':
            archive=Path(row['entity_archive'])
            if not archive.exists(): return False
            try: entity_payload=json.loads(archive.read_text())['payload']['entities']
            except (KeyError, json.JSONDecodeError, OSError): return False
            if row['entity_id'] not in entity_payload: return False
        if row['status']=='unavailable' and not row['reason']: return False
    if any(row['club_id']=='WPG' and (row['entity_id']!='Q472741' or row['wikipedia_article']!='Winnipeg Jets') for row in rows): return False
    if any(row['club_id']=='UTA' and row['wikipedia_article'] not in {'Utah Hockey Club','Utah Mammoth'} for row in rows): return False
    if not any(row['club_id']=='ARI' and row['entity_id']=='Q206312' and row['wikipedia_article']=='Arizona Coyotes' for row in rows): return False
    uta=sorted((row for row in rows if row['club_id']=='UTA'),key=lambda row:row['valid_from'])
    if len(uta)!=2 or uta[0]['valid_to']!='2025-05-06' or uta[1]['valid_from']!='2025-05-07': return False
    if any(row['club_id']=='ARI' and (not row['valid_to'] or row['valid_to']>='2024-07-01') for row in rows): return False
    with (ROOT/'config/franchise_history.csv').open() as handle: identities=list(csv.DictReader(handle))
    identity_by_id={row['identity_id']:row for row in identities}
    if set(identity_by_id)!={'ARI-coyotes','UTA-hockey-club','UTA-mammoth'}: return False
    if identity_by_id['ARI-coyotes']['franchise_id']==identity_by_id['UTA-hockey-club']['franchise_id']: return False
    if identity_by_id['UTA-hockey-club']['successor_identity_id']!='UTA-mammoth': return False
    if date.fromisoformat(identity_by_id['UTA-hockey-club']['valid_to']).toordinal()+1 != date.fromisoformat(identity_by_id['UTA-mammoth']['valid_from']).toordinal(): return False
    return True
if __name__=='__main__': print('PASS' if validate() else 'FAIL')
