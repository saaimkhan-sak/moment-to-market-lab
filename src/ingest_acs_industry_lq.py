"""Build no-key ACS C24030 metro industry LQs as a QCEW fallback."""
from __future__ import annotations
import csv, io, math
from common import ROOT, evidence_record, fetch_bytes, write_json

# C24030 is sex by broad industry. Each tuple contains male and female cells;
# combined categories use the published aggregate category, not child sums.
SECTORS={
    'natural_resources_mining':('003','030'),
    'construction':('006','033'),
    'manufacturing':('007','034'),
    'trade_transportation_utilities':('008','009','010','035','036','037'),
    'information':('013','040'),
    'financial_activities':('014','041'),
    'professional_business_services':('017','044'),
    'education_health_services':('021','048'),
    'leisure_hospitality':('024','051'),
    'other_services':('027','054'),
}

def field(code,suffix): return f'C24030_{suffix}{code}'
def number(value):
    try:
        parsed=float(value)
        return parsed if parsed>-999999999 else None
    except (TypeError,ValueError): return None
def rss(values): return math.sqrt(sum(x*x for x in values)) if values and all(x is not None for x in values) else None
def combined(source,codes,suffix):
    values=[number(source.get(field(code,suffix))) for code in codes]
    return sum(values) if all(value is not None for value in values) else None

def acquire():
    url='https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-c24030.dat'
    raw_dir=ROOT/'data/raw/market'; raw_dir.mkdir(parents=True,exist_ok=True)
    path=raw_dir/'acs-2024-5yr-C24030.dat'
    if path.exists():
        body=path.read_bytes(); provenance={'source_url':url,'retrieved_at':'2026-08-03T00:00:00Z','content_length':len(body)}
    else:
        body,provenance=fetch_bytes(url); path.write_bytes(body)
    geos=[row for row in csv.DictReader((ROOT/'config/market_geographies.csv').open()) if row['country']=='US']
    wanted={row['geography_id'] for row in geos}; by_cbsa={}; us=None
    reader=csv.DictReader(io.TextIOWrapper(io.BytesIO(body),encoding='utf-8-sig'),delimiter='|')
    for source in reader:
        geo_id=source.get('GEO_ID','')
        if geo_id.startswith('310M700US') and geo_id[-5:] in wanted: by_cbsa[geo_id[-5:]]=source
        elif geo_id=='0100000US': us=source
    if us is None: raise ValueError('C24030 national denominator row is missing')
    us_total=number(us.get('C24030_E001')); us_total_moe=number(us.get('C24030_M001'))
    rows=[]
    for geo in geos:
        source=by_cbsa.get(geo['geography_id']); market_total=number(source.get('C24030_E001')) if source else None; market_total_moe=number(source.get('C24030_M001')) if source else None
        for label,codes in SECTORS.items():
            market=combined(source,codes,'E') if source else None; market_moe=rss([number(source.get(field(code,'M'))) for code in codes]) if source else None
            national=combined(us,codes,'E'); national_moe=rss([number(us.get(field(code,'M'))) for code in codes])
            complete=all(value not in {None,0} for value in (market,market_total,national,us_total))
            lq=(market/market_total)/(national/us_total) if complete else None
            rows.append({'club_id':geo['club_id'],'cbsa':geo['geography_id'],'industry_label':label,'market_employment_estimate':market,'market_employment_moe_90':market_moe,'market_total_employment_estimate':market_total,'market_total_employment_moe_90':market_total_moe,'us_industry_employment_estimate':national,'us_industry_employment_moe_90':national_moe,'us_total_employment_estimate':us_total,'us_total_employment_moe_90':us_total_moe,'location_quotient_estimate':lq,'reference_period':'2020-2024 ACS 5-year','source_id':'acs-2024-c24030','source_url':url,'retrieved_at':provenance['retrieved_at'],'evidence_status':'confirmed' if complete else 'unavailable','estimate_type':'survey_estimate','limitation':'ACS resident-worker industry estimates differ from QCEW establishment employment; 90% margins of error are retained and the LQ is descriptive.'})
    write_json('data/curated/acs_industry_location_quotients.json',rows)
    return write_json('data/evidence/acs-industry-lq.json',{'source':evidence_record('acs-2024-c24030','confirmed','Official no-key survey-estimate fallback; not a replacement value inside QCEW.'),'raw_path':str(path),'raw_bytes':len(body),'rows':rows})

if __name__=='__main__': print(acquire())
