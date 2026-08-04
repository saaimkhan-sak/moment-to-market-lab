"""Daily canonical article pageviews. Missing observations are preserved, never converted to zero."""
from __future__ import annotations
import csv, json, sys, time
from urllib.parse import quote
from common import ROOT, archive_json, fetch_json, write_json, evidence_record
from analysis_window import ANALYSIS_START, ANALYSIS_END

DEFAULT_START=ANALYSIS_START.replace('-','')
DEFAULT_END=ANALYSIS_END.replace('-','')

def ingest(article: str, start: str, end: str) -> str:
    article_slug=quote(article.replace(' ', '_'), safe='')
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{article_slug}/daily/{start}/{end}"
    payload, provenance = fetch_json(url)
    provenance.update({"project": "en.wikipedia", "access": "all-access", "agent": "user", "article": article, "granularity": "daily", "start": start, "end": end})
    return str(archive_json("wikimedia", f"{article}-{start}-{end}", payload, provenance))

def ingest_all_clubs(start=DEFAULT_START, end=DEFAULT_END) -> str:
    results=[]
    for row in csv.DictReader((ROOT/'config/entity_dictionary.csv').open()):
        if row.get('status') != 'confirmed' or not row.get('wikipedia_article'):
            results.append({'club_id':row['club_id'],'evidence_status':'unavailable','reason':row.get('reason','unresolved_entity')})
            continue
        effective_start=max(start,(row.get('valid_from') or start).replace('-',''))
        effective_end=min(end,(row.get('valid_to') or end).replace('-',''))
        if effective_start>effective_end:
            results.append({'club_id':row['club_id'],'mapping_id':row.get('mapping_id'),'article':row['wikipedia_article'],'evidence_status':'unavailable','reason':'mapping_validity_outside_requested_window'})
            continue
        try:
            path=ingest(row['wikipedia_article'], effective_start, effective_end)
            results.append({'club_id':row['club_id'],'mapping_id':row.get('mapping_id'),'article':row['wikipedia_article'],'valid_from':row.get('valid_from'),'valid_to':row.get('valid_to'),'evidence_status':'confirmed','path':path})
        except Exception as exc:
            results.append({'club_id':row['club_id'],'article':row['wikipedia_article'],'evidence_status':'unavailable','reason':type(exc).__name__})
        time.sleep(.25)
    return str(write_json('data/manifests/wikimedia_pageview_acquisition.json', {'source':evidence_record('wikimedia-pageviews','confirmed','Missing records remain missing; no zero imputation.'),'window':{'start':start,'end':end},'results':results}))


def retry_missing(start=DEFAULT_START, end=DEFAULT_END) -> str:
    """Retry only unavailable mappings and preserve every confirmed archive."""
    manifest_path = ROOT / 'data/manifests/wikimedia_pageview_acquisition.json'
    manifest = json.loads(manifest_path.read_text())
    prior = manifest.get('results', [])
    unavailable = {(row.get('mapping_id'), row.get('club_id'), row.get('article')) for row in prior if row.get('evidence_status') != 'confirmed'}
    mappings = list(csv.DictReader((ROOT / 'config/entity_dictionary.csv').open()))
    replacements = {}
    for row in mappings:
        key = (row.get('mapping_id'), row.get('club_id'), row.get('wikipedia_article'))
        legacy_key = (None, row.get('club_id'), row.get('wikipedia_article'))
        if key not in unavailable and legacy_key not in unavailable:
            continue
        effective_start = max(start, (row.get('valid_from') or start).replace('-', ''))
        effective_end = min(end, (row.get('valid_to') or end).replace('-', ''))
        try:
            path = ingest(row['wikipedia_article'], effective_start, effective_end)
            replacement = {
                'club_id': row['club_id'],
                'mapping_id': row.get('mapping_id'),
                'article': row['wikipedia_article'],
                'valid_from': row.get('valid_from'),
                'valid_to': row.get('valid_to'),
                'evidence_status': 'confirmed',
                'path': path,
            }
        except Exception as exc:
            replacement = {
                'club_id': row['club_id'],
                'mapping_id': row.get('mapping_id'),
                'article': row['wikipedia_article'],
                'evidence_status': 'unavailable',
                'reason': type(exc).__name__,
            }
        replacements[(row.get('club_id'), row.get('wikipedia_article'))] = replacement
        time.sleep(2)
    results = []
    for row in prior:
        results.append(replacements.pop((row.get('club_id'), row.get('article')), row))
    results.extend(replacements.values())
    return str(write_json('data/manifests/wikimedia_pageview_acquisition.json', {
        'source': evidence_record('wikimedia-pageviews', 'confirmed', 'Missing records remain missing; no zero imputation.'),
        'window': {'start': start, 'end': end},
        'results': results,
    }))

if __name__ == "__main__":
    if sys.argv[1:] == ['--all-clubs']:
        print(ingest_all_clubs())
    elif sys.argv[1:] == ['--retry-missing']:
        print(retry_missing())
    else:
        print(ingest(*sys.argv[1:4]))
