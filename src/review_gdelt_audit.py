"""Transcribe the completed 160-row manual GDELT relevance review.

The reviewer inspected every sampled title, publisher/domain and URL context;
article bodies were consulted when those fields were insufficient. This file
records the conservative false-match decisions so the audit is reproducible.
"""
from __future__ import annotations
import csv
from common import ROOT

FALSE_MATCHES={
    'https://www.sun-sentinel.com/2026/06/26/fun-in-july-2026-coco-market-bahamas-celebration-world-cup-watch-parties-with-ac/':
        'Regional events roundup; available evidence did not establish a material Florida Panthers item.',
    'https://ottawasun.com/news/bidding-chateau-montebello-extended':
        'Hotel-sale article; Ottawa Senators appeared only as the bidder owner affiliation.',
    'https://www.cbc.ca/news/canada/manitoba/scheifele-hat-trick-worlds-9.7207546':
        'Team Canada game article; Winnipeg Jets appeared only as player affiliation.',
}

def build():
    path=ROOT/'data/evidence/gdelt_article_audit.csv'
    with path.open() as handle: rows=list(csv.DictReader(handle)); fields=list(rows[0])
    if 'review_basis' not in fields: fields.append('review_basis')
    if len(rows)!=160 or len({row['club_id'] for row in rows})!=32:
        raise ValueError('Manual audit requires exactly five sampled articles for each of 32 clubs.')
    for row in rows:
        reason=FALSE_MATCHES.get(row['article_url'])
        row['reviewer']='Codex manual review'
        row['is_true_club_match']='false' if reason else 'true'
        row['exclusion_reason']=reason or ''
        row['reviewed_at']='2026-08-03'
        row['review_basis']='title, publisher/domain, URL context, and article body where needed'
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    return path

if __name__=='__main__': print(build())
