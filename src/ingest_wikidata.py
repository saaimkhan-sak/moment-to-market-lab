"""Resolve entity mappings through Wikidata; no guessed page/article joins."""
from __future__ import annotations
import csv, sys, time
from urllib.parse import urlencode, quote
from common import ROOT, archive_json, fetch_json, write_json, evidence_record

def ingest(qid: str) -> str:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    payload, provenance = fetch_json(url)
    return str(archive_json("wikimedia", f"wikidata-{qid}", payload, provenance))

def plan_club_resolution() -> str:
    rows=[]
    for club in csv.DictReader((ROOT/"config/clubs.csv").open()):
        rows.append({"club_id":club["club_id"],"search_term":club["club_name"],"entity_type":"club","wikidata_query_url":"https://www.wikidata.org/w/api.php?"+urlencode({"action":"wbsearchentities","search":club["club_name"],"language":"en","format":"json"}),"evidence_status":"planned","review_requirement":"Confirm exact club entity, English Wikipedia sitelink, redirects, franchise validity period."})
    return str(write_json("data/manifests/wikidata_club_resolution_plan.json", {"source":evidence_record("wikidata","planned"),"rows":rows}))

def resolve_exact_clubs(retry_unavailable: bool = False) -> str:
    """Resolve only exact club-label matches and retain all query evidence."""
    prior={row['club_id']:row for row in csv.DictReader((ROOT/'config/entity_dictionary.csv').open())} if (ROOT/'config/entity_dictionary.csv').exists() else {}
    rows=[]
    for club in csv.DictReader((ROOT/'config/clubs.csv').open()):
        if retry_unavailable and prior.get(club['club_id'],{}).get('status')=='confirmed':
            rows.append(prior[club['club_id']]); continue
        label=club['club_name']
        search_url='https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=10&search='+quote(label)
        base={'club_id':club['club_id'],'entity_label':label,'search_source_url':search_url}
        try:
            payload, provenance=fetch_json(search_url)
            search_path=archive_json('wikidata', f"search-{club['club_id'].lower()}", payload, provenance)
            matches=[item for item in payload.get('search',[]) if item.get('label','').casefold()==label.casefold()]
            if not matches:
                rows.append({**base,'entity_id':'','wikipedia_article':'','status':'unavailable','reason':'no_exact_wikidata_label','retrieved_at':provenance['retrieved_at'],'search_archive':str(search_path),'entity_archive':''})
                continue
            qid=matches[0]['id']
            entity_url=f'https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&ids={qid}&props=labels|sitelinks'
            entity_payload, entity_provenance=fetch_json(entity_url)
            entity_path=archive_json('wikidata', f"{club['club_id'].lower()}-{qid}", entity_payload, entity_provenance)
            entity=entity_payload.get('entities',{}).get(qid,{})
            article=((entity.get('sitelinks') or {}).get('enwiki') or {}).get('title','')
            rows.append({**base,'entity_id':qid,'wikipedia_article':article,'status':'confirmed' if article else 'unavailable','reason':'' if article else 'missing_enwiki_sitelink','retrieved_at':entity_provenance['retrieved_at'],'search_archive':str(search_path),'entity_archive':str(entity_path)})
        except Exception as exc:
            rows.append({**base,'entity_id':'','wikipedia_article':'','status':'unavailable','reason':type(exc).__name__,'retrieved_at':'','search_archive':'','entity_archive':''})
        time.sleep(.2)
    fields=['club_id','entity_id','entity_label','wikipedia_article','status','reason','search_source_url','retrieved_at','search_archive','entity_archive']
    with (ROOT/'config/entity_dictionary.csv').open('w', newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return str(write_json('data/manifests/wikidata_club_resolution.json', {'source':evidence_record('wikidata','confirmed','Exact-label candidates with archived search and entity responses.'),'results':rows}))

if __name__ == "__main__":
    if sys.argv[1:] == ['--plan-clubs']: print(plan_club_resolution())
    elif sys.argv[1:] == ['--resolve-exact-clubs']: print(resolve_exact_clubs())
    elif sys.argv[1:] == ['--retry-unavailable']: print(resolve_exact_clubs(True))
    else: print(ingest(sys.argv[1]))
