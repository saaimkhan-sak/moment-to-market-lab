"""Apply audited franchise-era Wikimedia mappings without merging identities."""
from __future__ import annotations
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'config/entity_dictionary.csv'; existing=list(csv.DictReader(path.open()))
    rows=[]
    for row in existing:
        if row['club_id'] in {'WPG','UTA'}: continue
        rows.append({'mapping_id':f"{row['club_id']}-current",**row,'valid_from':'2023-10-01','valid_to':''})
    rows.extend([
        {'mapping_id':'WPG-current','club_id':'WPG','entity_id':'Q472741','entity_label':'Winnipeg Jets','wikipedia_article':'Winnipeg Jets','valid_from':'2023-10-01','valid_to':'','status':'confirmed','reason':'','search_source_url':'https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=10&search=Winnipeg%20Jets','retrieved_at':'2026-08-03','search_archive':str(ROOT/'data/raw/wikidata/search-wpg.json'),'entity_archive':str(ROOT/'data/raw/wikimedia/wikidata-Q472741.json')},
        {'mapping_id':'ARI-2023-24','club_id':'ARI','entity_id':'Q206312','entity_label':'Arizona Coyotes','wikipedia_article':'Arizona Coyotes','valid_from':'2023-10-01','valid_to':'2024-06-30','status':'confirmed','reason':'','search_source_url':'https://www.wikidata.org/wiki/Q206312','retrieved_at':'2026-08-03','search_archive':str(ROOT/'data/raw/wikidata/search-wpg.json'),'entity_archive':str(ROOT/'data/raw/wikimedia/wikidata-Q206312.json')},
        {'mapping_id':'UTA-hockey-club','club_id':'UTA','entity_id':'Q125520712','entity_label':'Utah Hockey Club','wikipedia_article':'Utah Hockey Club','valid_from':'2024-06-13','valid_to':'2025-05-06','status':'confirmed','reason':'','search_source_url':'https://www.wikidata.org/wiki/Q125520712','retrieved_at':'2026-08-03','search_archive':str(ROOT/'data/raw/wikidata/search-uta.json'),'entity_archive':str(ROOT/'data/raw/wikimedia/wikidata-Q125520712.json')},
        {'mapping_id':'UTA-mammoth','club_id':'UTA','entity_id':'Q125520712','entity_label':'Utah Mammoth','wikipedia_article':'Utah Mammoth','valid_from':'2025-05-07','valid_to':'','status':'confirmed','reason':'','search_source_url':'https://www.wikidata.org/wiki/Q125520712','retrieved_at':'2026-08-03','search_archive':str(ROOT/'data/raw/wikidata/search-uta.json'),'entity_archive':str(ROOT/'data/raw/wikimedia/wikidata-Q125520712.json')},
    ])
    fields=['mapping_id','club_id','entity_id','entity_label','wikipedia_article','valid_from','valid_to','status','reason','search_source_url','retrieved_at','search_archive','entity_archive']
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(sorted(rows,key=lambda x:(x['club_id'],x['valid_from'])))
    print(f"Wrote {len(rows)} validity-aware entity mappings.")

if __name__=='__main__': main()
