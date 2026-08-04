"""Acquire reproducible U.S. CBSA market context from ACS and BEA."""
from __future__ import annotations
import csv, io, json, os
from urllib.parse import urlencode
from common import ROOT, archive_json, evidence_record, fetch_bytes, fetch_json, load_env, write_json

ACS_VARS={
    'DP05_0001E':'population',
    'DP05_0018E':'median_age',
    'DP03_0062E':'median_household_income_usd',
    'DP03_0009PE':'unemployment_rate_pct',
    'DP02_0068PE':'bachelors_or_higher_pct',
}

def acquire():
    load_env()
    geos=[r for r in csv.DictReader((ROOT/'config/market_geographies.csv').open()) if r['country']=='US']
    table_specs={
        'B01003':{'population':lambda r:float(r['B01003_E001'])},
        'B01002':{'median_age':lambda r:float(r['B01002_E001'])},
        'B19013':{'median_household_income_usd':lambda r:float(r['B19013_E001'])},
        'B23025':{'unemployment_rate_pct':lambda r:100*float(r['B23025_E005'])/max(float(r['B23025_E003']),1)},
        'B15003':{'bachelors_or_higher_pct':lambda r:100*sum(float(r[f'B15003_E{i:03d}']) for i in range(22,26))/max(float(r['B15003_E001']),1)},
    }
    values={geo['geography_id']:{} for geo in geos}; raw_manifest=[]
    raw_dir=ROOT/'data/raw/market'; raw_dir.mkdir(parents=True,exist_ok=True)
    for table,metrics in table_specs.items():
        url=f'https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-{table.lower()}.dat'
        body,provenance=fetch_bytes(url); path=raw_dir/f'acs-2024-5yr-{table}.dat'; path.write_bytes(body)
        raw_manifest.append({'table':table,'path':str(path),**provenance})
        reader=csv.DictReader(io.StringIO(body.decode('utf-8-sig')),delimiter='|')
        for source in reader:
            geo_id=source.get('GEO_ID','')
            cbsa=geo_id[-5:] if geo_id.startswith('310M700US') else None
            if cbsa not in values: continue
            for metric,formula in metrics.items():
                try: values[cbsa][metric]=formula(source)
                except (KeyError,ValueError,ZeroDivisionError): values[cbsa][metric]=None
    provenance={'source_url':'https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/','retrieved_at':raw_manifest[-1]['retrieved_at']}
    rows=[]
    for geo in geos:
        for metric in ACS_VARS.values():
            raw=values[geo['geography_id']].get(metric)
            rows.append({'club_id':geo['club_id'],'country':'US','geography_type':'CBSA','geography_id':geo['geography_id'],'geography_name':geo['display_name'],'reference_period':'2020-2024 ACS 5-year','metric_name':metric,'metric_value':raw,'unit':'USD' if 'usd' in metric else ('percent' if metric.endswith('_pct') else ('years' if metric=='median_age' else 'persons')),'source_id':'acs-2024-table-based-summary-file','source_url':provenance['source_url'],'retrieved_at':provenance['retrieved_at'],'evidence_status':'confirmed' if raw is not None else 'unavailable'})
    bea_key=os.getenv('BEA_API_KEY')
    bea_status=evidence_record('bea-regional','unavailable','BEA_API_KEY is not set')
    if bea_key:
        bea_query={'UserID':bea_key,'method':'GetData','datasetname':'Regional','TableName':'MARPP','LineCode':'1','GeoFIPS':'MSA','Year':'2023','ResultFormat':'JSON'}
        safe_query={**bea_query,'UserID':'REDACTED'}
        bea_url='https://apps.bea.gov/api/data/?'+urlencode(bea_query)
        try:
            bea_payload,bea_prov=fetch_json(bea_url)
            bea_prov['source_url']='https://apps.bea.gov/api/data/?'+urlencode(safe_query)
            for param in (((bea_payload.get('BEAAPI') or {}).get('Request') or {}).get('RequestParam') or []):
                if str(param.get('ParameterName','')).upper()=='USERID': param['ParameterValue']='REDACTED'
            archive_json('market','bea-2023-marpi-msa',bea_payload,bea_prov)
            data=((bea_payload.get('BEAAPI') or {}).get('Results') or {}).get('Data') or []
            by_bea={str(x.get('GeoFips','')).strip(' "'):x for x in data}
            for geo in geos:
                item=by_bea.get(geo['geography_id']); raw=(item or {}).get('DataValue')
                rows.append({'club_id':geo['club_id'],'country':'US','geography_type':'CBSA','geography_id':geo['geography_id'],'geography_name':geo['display_name'],'reference_period':'2023','metric_name':'regional_price_parity_all_items','metric_value':float(str(raw).replace(',','')) if raw not in {None,'','(NA)'} else None,'unit':'index_US_100','source_id':'bea-regional-marpi','source_url':bea_prov['source_url'],'retrieved_at':bea_prov['retrieved_at'],'evidence_status':'confirmed' if item and raw not in {None,'','(NA)'} else 'unavailable'})
            bea_status=evidence_record('bea-regional','confirmed')
        except Exception as exc:
            bea_status=evidence_record('bea-regional','unavailable',type(exc).__name__)
    write_json('data/curated/market_context_us.json',rows)
    return write_json('data/evidence/market-us.json',{'acs':evidence_record('acs-2024-table-based-summary-file','confirmed'), 'bea':bea_status,'club_count':len(geos),'raw_manifest':raw_manifest,'rows':rows})

if __name__=='__main__': print(acquire())
