"""Acquire official 2021 Census Profile CMA extracts from Statistics Canada."""
from __future__ import annotations
import csv
from common import ROOT, evidence_record, fetch_bytes, write_json

def acquire():
    geos=[r for r in csv.DictReader((ROOT/'config/market_geographies.csv').open()) if r['country']=='CA']
    results=[]
    raw_dir=ROOT/'data/raw/market'; raw_dir.mkdir(parents=True,exist_ok=True)
    for geo in geos:
        dguid='2021S0503'+geo['geography_id']
        url=f'https://api.statcan.gc.ca/census-recensement/profile/sdmx/rest/data/STC_CP,DF_CMACA/A5.{dguid}...?format=csv'
        try:
            body,provenance=fetch_bytes(url)
            path=raw_dir/f"statcan-2021-cma-{geo['geography_id']}.csv"; path.write_bytes(body)
            results.append({**geo,'dguid':dguid,'source_url':url,'retrieved_at':provenance['retrieved_at'],'checksum':provenance['checksum'],'raw_path':str(path),'bytes':len(body),'evidence_status':'confirmed'})
        except Exception as exc:
            results.append({**geo,'dguid':dguid,'source_url':url,'evidence_status':'unavailable','reason':type(exc).__name__})
    metrics={'1':('population','persons','1'),'39':('average_age','years','1'),'229':('median_household_income_cad','CAD','1'),'2008':('bachelors_or_higher_pct','percent','4'),'2230':('unemployment_rate_pct','percent','1')}
    curated=[]
    for result in results:
        if result['evidence_status']!='confirmed': continue
        with open(result['raw_path'],newline='') as handle:
            for row in csv.DictReader(handle):
                spec=metrics.get(row['CHARACTERISTIC'])
                if not spec or row['GENDER']!='1' or row['STATISTIC']!=spec[2] or row['OBS_VALUE']=='': continue
                curated.append({'club_id':result['club_id'],'country':'CA','geography_type':'CMA','geography_id':result['geography_id'],'geography_name':result['display_name'],'reference_period':'2021 Census','metric_name':spec[0],'metric_value':float(row['OBS_VALUE']),'unit':spec[1],'source_id':'statcan-2021-census-profile','source_url':result['source_url'],'retrieved_at':result['retrieved_at'],'evidence_status':'confirmed'})
    write_json('data/curated/market_context_canada.json',curated)
    return write_json('data/evidence/market-canada.json',{'source':evidence_record('statcan-2021-census-profile','confirmed','CMA extracts are not ranked against U.S. ACS values.'),'rows':results,'curated_rows':curated})

if __name__=='__main__': print(acquire())
