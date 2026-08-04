"""Archive BLS QCEW annual data and calculate reproducible MSA location quotients."""
from __future__ import annotations
import csv, io, zipfile
from common import ROOT, evidence_record, fetch_bytes, write_json

SECTORS={'1011':'natural_resources_mining','1012':'construction','1013':'manufacturing','1021':'trade_transportation_utilities','1022':'information','1023':'financial_activities','1024':'professional_business_services','1025':'education_health_services','1026':'leisure_hospitality','1027':'other_services'}

def acquire():
    url='https://data.bls.gov/cew/data/files/2024/csv/2024_annual_singlefile.zip'
    raw_dir=ROOT/'data/raw/market'; raw_dir.mkdir(parents=True,exist_ok=True)
    path=raw_dir/'2024_annual_singlefile.zip'
    if path.exists(): body=path.read_bytes(); provenance={'source_url':url,'retrieved_at':'2026-08-03T00:00:00Z'}
    else: body,provenance=fetch_bytes(url); path.write_bytes(body)
    geos=[r for r in csv.DictReader((ROOT/'config/market_geographies.csv').open()) if r['country']=='US']
    area_for={r['club_id']:'C'+r['geography_id'][:4] for r in geos}; wanted=set(area_for.values())|{'US000'}
    values={}
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        member=next(name for name in zf.namelist() if name.lower().endswith('.csv'))
        with zf.open(member) as stream:
            reader=csv.DictReader(io.TextIOWrapper(stream,encoding='utf-8-sig'))
            for row in reader:
                area=row['area_fips'].strip(); industry=row['industry_code'].strip(); own=row['own_code'].strip()
                # Supersector rows are private ownership (5); use private total
                # employment as both market and national denominator.
                if area not in wanted or own!='5' or industry not in {'10',*SECTORS}: continue
                raw=row.get('annual_avg_emplvl','').strip()
                values[(area,industry)]={'value':float(raw) if raw else None,'disclosure_code':row.get('disclosure_code','').strip()}
    def value(area,industry): return (values.get((area,industry)) or {}).get('value')
    us_total=value('US000','10'); denominators={code:value('US000',code) for code in SECTORS}
    rows=[]
    for geo in geos:
        area=area_for[geo['club_id']]; market_total=value(area,'10')
        for code,label in SECTORS.items():
            source_cell=values.get((area,code)) or {}; raw_market=source_cell.get('value'); disclosure=source_cell.get('disclosure_code',''); national=denominators[code]
            suppressed=disclosure=='N'; market=None if suppressed else raw_market
            complete=all(x not in {None,0} for x in (market_total,market,us_total,national))
            lq=(market/market_total)/(national/us_total) if complete else None
            reason=None if complete else ('bls_confidentiality_suppression' if suppressed else 'source_value_unavailable')
            rows.append({'club_id':geo['club_id'],'cbsa':geo['geography_id'],'qcew_area_fips':area,'industry_code':code,'industry_label':label,'market_employment':market,'market_total_employment':market_total,'us_industry_employment':national,'us_total_employment':us_total,'location_quotient':lq,'reference_period':'2024 annual average','source_url':url,'retrieved_at':provenance['retrieved_at'],'evidence_status':'confirmed' if complete else 'unavailable','unavailable_reason':reason,'bls_disclosure_code':disclosure or None})
    write_json('data/curated/qcew_location_quotients.json',rows)
    return write_json('data/evidence/qcew.json',{'source':evidence_record('bls-qcew-2024-annual','confirmed','LQ denominator vector is stored on every row; unavailable cells remain unavailable.'),'raw_path':str(path),'raw_bytes':len(body),'rows':rows})

if __name__=='__main__': print(acquire())
