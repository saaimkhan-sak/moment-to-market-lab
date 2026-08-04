"""GDELT article retrieval: raw context only until precision audit passes."""
from __future__ import annotations
import csv, json, sys, time, uuid
from urllib.parse import quote
from common import ROOT, archive_json, evidence_record, fetch_json, now_utc, write_json

def ingest(query: str, start: str, end: str) -> str:
    url = "https://api.gdeltproject.org/api/v2/doc/doc?format=json&mode=artlist&maxrecords=250&startdatetime=" + start + "&enddatetime=" + end + "&query=" + quote(query)
    payload, provenance = fetch_json(url)
    provenance.update({"query": query, "date_window": f"{start}:{end}", "quantification_status": "unavailable_pending_precision_audit"})
    return str(archive_json("gdelt", f"gdelt-{start}-{end}", payload, provenance))

def audit_template() -> str:
    headers=["audit_id","club_id","stratum","article_url","title","query","retrieved_at","reviewer","is_true_club_match","exclusion_reason","reviewed_at"]
    path=ROOT/"data/evidence/gdelt_article_audit.csv"; path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with path.open("w",newline="") as handle: csv.DictWriter(handle,fieldnames=headers).writeheader()
    return str(path)

def acquire_audit_sample(start='20260503000000',end='20260803000000') -> str:
    clubs=list(csv.DictReader((ROOT/'config/clubs.csv').open())); rows=[]; results=[]
    for club in clubs:
        query=f'"{club["club_name"]}" sourcelang:english'
        url="https://api.gdeltproject.org/api/v2/doc/doc?format=json&mode=artlist&maxrecords=5&startdatetime="+start+"&enddatetime="+end+"&query="+quote(query)
        try:
            payload,provenance=fetch_json(url)
            path=archive_json('gdelt',f"{club['club_id'].lower()}-{start}-{end}",payload,{**provenance,'query':query,'date_window':f'{start}:{end}','quantification_status':'unavailable_pending_precision_audit'})
            seen=set(); selected=[]
            for article in payload.get('articles',[]):
                article_url=article.get('url')
                if not article_url or article_url in seen: continue
                seen.add(article_url); selected.append(article)
                if len(selected)==5: break
            for article in selected:
                rows.append({'audit_id':str(uuid.uuid5(uuid.NAMESPACE_URL,club['club_id']+'|'+article['url'])),'club_id':club['club_id'],'stratum':'recent_english_exact_full_name','article_url':article['url'],'title':article.get('title',''),'query':query,'retrieved_at':provenance['retrieved_at'],'reviewer':'','is_true_club_match':'','exclusion_reason':'','reviewed_at':''})
            results.append({'club_id':club['club_id'],'candidate_count':len(payload.get('articles',[])),'sample_count':len(selected),'evidence_status':'confirmed' if len(selected)==5 else 'unavailable','raw_path':str(path),'source_url':url})
        except Exception as exc:
            results.append({'club_id':club['club_id'],'candidate_count':0,'sample_count':0,'evidence_status':'unavailable','reason':type(exc).__name__,'source_url':url})
        time.sleep(.25)
    headers=['audit_id','club_id','stratum','article_url','title','query','retrieved_at','reviewer','is_true_club_match','exclusion_reason','reviewed_at']
    with (ROOT/'data/evidence/gdelt_article_audit.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=headers); writer.writeheader(); writer.writerows(rows)
    return str(write_json('data/manifests/gdelt_audit_sample.json',{'source':evidence_record('gdelt-doc-api','confirmed','Exact full-name, English-language recent sample; quantification remains unavailable until manual review.'),'window':{'start':start,'end':end},'results':results,'sample_rows':len(rows)}))

def acquire_club_sample(club_id,start='20260503000000',end='20260803000000',query_suffix='sourcelang:english',append=False) -> str:
    club=next(x for x in csv.DictReader((ROOT/'config/clubs.csv').open()) if x['club_id']==club_id)
    query=f'"{club["club_name"]}" {query_suffix}'; raw_path=ROOT/f"data/raw/gdelt/{club_id.lower()}-{start}-{end}.json"
    if raw_path.exists(): record=json.loads(raw_path.read_text()); payload=record['payload']; provenance=record['provenance']
    else:
        url="https://api.gdeltproject.org/api/v2/doc/doc?format=json&mode=artlist&maxrecords=50&startdatetime="+start+"&enddatetime="+end+"&query="+quote(query)
        payload,provenance=fetch_json(url,attempts=3,timeout=90); archive_json('gdelt',f"{club_id.lower()}-{start}-{end}",payload,{**provenance,'query':query,'date_window':f'{start}:{end}','quantification_status':'unavailable_pending_precision_audit'})
    seen=set(); rows=[]
    for article in payload.get('articles',[]):
        if not article.get('url') or article['url'] in seen: continue
        seen.add(article['url']); rows.append({'club_id':club_id,'article_url':article['url'],'title':article.get('title',''),'query':query,'retrieved_at':provenance['retrieved_at'],'domain':article.get('domain',''),'language':article.get('language',''),'source_country':article.get('sourcecountry',''),'seen_at':article.get('seendate','')})
        if len(rows)==5: break
    candidate_path=ROOT/f'data/evidence/gdelt_candidates/{club_id}.json'
    if append and candidate_path.exists():
        existing=json.loads(candidate_path.read_text()).get('rows',[])
        merged={row['article_url']:row for row in existing}
        merged.update({row['article_url']:row for row in rows})
        rows=list(merged.values())[:5]
    return str(write_json(f'data/evidence/gdelt_candidates/{club_id}.json',{'club_id':club_id,'evidence_status':'confirmed' if len(rows)==5 else 'unavailable','rows':rows}))

def assemble_audit() -> str:
    rows=[]; results=[]
    for club in csv.DictReader((ROOT/'config/clubs.csv').open()):
        path=ROOT/f"data/evidence/gdelt_candidates/{club['club_id']}.json"
        data=json.loads(path.read_text()) if path.exists() else {'rows':[],'evidence_status':'unavailable'}
        raw_path=ROOT/f"data/raw/gdelt/{club['club_id'].lower()}-20260503000000-20260803000000.json"
        raw_articles=json.loads(raw_path.read_text()).get('payload',{}).get('articles',[]) if raw_path.exists() else []
        raw_by_url={article.get('url'):article for article in raw_articles}
        for article in data['rows']:
            raw=raw_by_url.get(article['article_url'],{})
            rows.append({'audit_id':str(uuid.uuid5(uuid.NAMESPACE_URL,club['club_id']+'|'+article['article_url'])),'club_id':club['club_id'],'stratum':'recent_english_exact_full_name','article_url':article['article_url'],'title':article['title'],'query':article['query'],'domain':article.get('domain') or raw.get('domain',''),'language':article.get('language') or raw.get('language',''),'source_country':article.get('source_country') or raw.get('sourcecountry',''),'seen_at':article.get('seen_at') or raw.get('seendate',''),'retrieved_at':article['retrieved_at'],'reviewer':'','is_true_club_match':'','exclusion_reason':'','reviewed_at':''})
        results.append({'club_id':club['club_id'],'sample_count':len(data['rows']),'evidence_status':data['evidence_status']})
    headers=['audit_id','club_id','stratum','article_url','title','query','domain','language','source_country','seen_at','retrieved_at','reviewer','is_true_club_match','exclusion_reason','reviewed_at']
    with (ROOT/'data/evidence/gdelt_article_audit.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=headers);writer.writeheader();writer.writerows(rows)
    return str(write_json('data/manifests/gdelt_audit_sample.json',{'source':evidence_record('gdelt-doc-api','confirmed','Per-club resumable sample; manual review pending.'),'results':results,'sample_rows':len(rows)}))

def resume_missing() -> str:
    results=[]
    for club in csv.DictReader((ROOT/'config/clubs.csv').open()):
        path=ROOT/f"data/evidence/gdelt_candidates/{club['club_id']}.json"
        if path.exists(): continue
        try:
            results.append({'club_id':club['club_id'],'path':acquire_club_sample(club['club_id']),'evidence_status':'confirmed'})
        except Exception as exc:
            results.append({'club_id':club['club_id'],'evidence_status':'unavailable','reason':type(exc).__name__})
        time.sleep(8)
    write_json('data/manifests/gdelt_resume.json',{'source':evidence_record('gdelt-doc-api','confirmed','Eight-second pacing after prior 429 responses.'),'results':results})
    return assemble_audit()

if __name__ == "__main__":
    if sys.argv[1:] == ['--init-audit']: print(audit_template())
    elif sys.argv[1:] == ['--acquire-audit-sample']: print(acquire_audit_sample())
    elif sys.argv[1:2] == ['--club']: print(acquire_club_sample(sys.argv[2]))
    elif sys.argv[1:] == ['--assemble-audit']: print(assemble_audit())
    elif sys.argv[1:] == ['--resume-missing']: print(resume_missing())
    else: print(ingest(*sys.argv[1:4]))
