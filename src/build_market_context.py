"""Assemble the canonical cross-border market-context table without forced ranking."""
from __future__ import annotations
import json
from common import ROOT, write_json

def build():
    rows=[]
    for name in ('market_context_us.json','market_context_canada.json'):
        rows.extend(json.loads((ROOT/'data/curated'/name).read_text()))
    qcew_rows=json.loads((ROOT/'data/curated/qcew_location_quotients.json').read_text())
    acs_rows=json.loads((ROOT/'data/curated/acs_industry_location_quotients.json').read_text())
    acs_by_key={(row['club_id'],row['industry_label']):row for row in acs_rows}
    for qcew in qcew_rows:
        rows.append({
            'club_id':qcew['club_id'],'country':'US','geography_id':qcew['cbsa'],
            'geography_type':'CBSA','metric_name':f"qcew_lq_{qcew['industry_label']}",
            'metric_value':qcew.get('location_quotient'),'unit':'location_quotient',
            'reference_period':qcew['reference_period'],'source_id':'bls-qcew-annual',
            'source_url':qcew['source_url'],'retrieved_at':qcew['retrieved_at'],
            'evidence_status':qcew['evidence_status'],
            'unavailable_reason':qcew.get('unavailable_reason'),
            'bls_disclosure_code':qcew.get('bls_disclosure_code'),
            'denominator_vector':{
                'market_industry_employment':qcew.get('market_employment'),
                'market_total_employment':qcew.get('market_total_employment'),
                'us_industry_employment':qcew.get('us_industry_employment'),
                'us_total_employment':qcew.get('us_total_employment'),
            },
            'interpretation_limit':'Industry context only; suppressed or unavailable cells are not low concentration.',
        })
    for acs in acs_rows:
        rows.append({'club_id':acs['club_id'],'country':'US','geography_id':acs['cbsa'],'geography_type':'CBSA','metric_name':f"acs_industry_lq_{acs['industry_label']}",'metric_value':acs['location_quotient_estimate'],'unit':'location_quotient_estimate','reference_period':acs['reference_period'],'source_id':acs['source_id'],'source_url':acs['source_url'],'retrieved_at':acs['retrieved_at'],'evidence_status':acs['evidence_status'],'margin_of_error_inputs':{'market_industry_moe_90':acs['market_employment_moe_90'],'market_total_moe_90':acs['market_total_employment_moe_90'],'us_industry_moe_90':acs['us_industry_employment_moe_90'],'us_total_moe_90':acs['us_total_employment_moe_90']},'interpretation_limit':acs['limitation']})
    for qcew in qcew_rows:
        fallback=acs_by_key.get((qcew['club_id'],qcew['industry_label']))
        use_qcew=qcew['evidence_status']=='confirmed'
        value=qcew['location_quotient'] if use_qcew else (fallback or {}).get('location_quotient_estimate')
        rows.append({'club_id':qcew['club_id'],'country':'US','geography_id':qcew['cbsa'],'geography_type':'CBSA','metric_name':f"preferred_industry_lq_{qcew['industry_label']}",'metric_value':value,'unit':'location_quotient','reference_period':qcew['reference_period'] if use_qcew else (fallback or {}).get('reference_period'),'source_id':'bls-qcew-annual' if use_qcew else (fallback or {}).get('source_id'),'source_url':qcew['source_url'] if use_qcew else (fallback or {}).get('source_url'),'retrieved_at':qcew['retrieved_at'] if use_qcew else (fallback or {}).get('retrieved_at'),'evidence_status':'confirmed' if value is not None else 'unavailable','fallback_used':not use_qcew,'original_qcew_state':qcew['evidence_status'],'original_qcew_reason':qcew.get('unavailable_reason'),'interpretation_limit':'Preferred public industry-concentration measure. QCEW is used when publishable; otherwise ACS S2403 is used and clearly labeled.'})
    return write_json('data/curated/market_context.json',rows)

if __name__=='__main__': print(build())
