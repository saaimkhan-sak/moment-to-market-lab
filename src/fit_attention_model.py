"""Auditable public-attention event study with explicit suppression gates."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import json
import statistics
import warnings
from common import ROOT, write_json

WINDOWS={"immediate":(0,1),"short_persistence":(2,3),"sustained_attention":(4,7)}
BASELINE_DAYS=14
MODEL_VERSION="2.0.0-unbalanced-multichannel-hierarchical"


def load_attention_channels():
    """Load confirmed channel observations without merging their units."""
    rows=[]
    wikimedia_path=ROOT/'data/curated/attention_daily.json'
    if wikimedia_path.exists():
        rows.extend(json.loads(wikimedia_path.read_text()))
    gdelt_path=ROOT/'data/curated/gdelt_attention_daily.json'
    precision_path=ROOT/'data/curated/gdelt_precision.json'
    timeline_manifest=ROOT/'data/manifests/gdelt_timeline_acquisition.json'
    doc_loaded=False
    if gdelt_path.exists() and precision_path.exists() and timeline_manifest.exists():
        precision=json.loads(precision_path.read_text())
        acquisition=json.loads(timeline_manifest.read_text())
        eligible={club for club,state in precision.get('club_precision',{}).items() if state.get('quantification_status')=='confirmed'}
        if precision.get('status')=='audit_complete' and acquisition.get('evidence_status') in {'confirmed','confirmed_with_visible_source_gaps'}:
            for row in json.loads(gdelt_path.read_text()):
                if row.get('club_id') in eligible and row.get('normalized_articles_per_100k') is not None:
                    rows.append({**row,'metric_value':row['normalized_articles_per_100k']})
            doc_loaded=True
    # The source contract is a club-level precision gate, not an all-or-nothing
    # league gate. When the preferred DOC timeline is incomplete, the archived
    # GKG exact-name panel may enter only for clubs whose GKG article audit meets
    # the same >=90% threshold. Failed clubs remain absent from this channel.
    release_gkg_path=ROOT/'data/curated/gdelt_gkg_attention_daily.json'
    release_gkg_precision_path=ROOT/'data/curated/gdelt_gkg_release_precision.json'
    release_gkg_manifest_path=ROOT/'data/manifests/gdelt_gkg_release_acquisition.json'
    gkg_path=release_gkg_path if release_gkg_path.exists() else ROOT/'data/curated/gdelt_gkg_attention_daily_excluded.json'
    gkg_precision_path=release_gkg_precision_path if release_gkg_precision_path.exists() else ROOT/'data/curated/gdelt_gkg_precision.json'
    gkg_manifest_path=release_gkg_manifest_path if release_gkg_manifest_path.exists() else ROOT/'data/manifests/gdelt_gkg_acquisition.json'
    if not doc_loaded and gkg_path.exists() and gkg_precision_path.exists() and gkg_manifest_path.exists():
        gkg_precision=json.loads(gkg_precision_path.read_text())
        gkg_manifest=json.loads(gkg_manifest_path.read_text())
        eligible={club for club,state in gkg_precision.get('club_precision',{}).items() if state.get('quantification_status')=='confirmed'}
        if gkg_precision.get('status')=='audit_complete' and gkg_manifest.get('evidence_status','').startswith('confirmed'):
            for row in json.loads(gkg_path.read_text()):
                if row.get('club_id') in eligible and row.get('normalized_articles_per_100k') is not None:
                    rows.append({
                        **row,
                        'metric_value':row['normalized_articles_per_100k'],
                        'evidence_quality':'confirmed_gkg_exact_name_audited_club_level',
                    })
    return rows

def attention_lift(post_value: float, baseline_mean: float) -> float:
    return (post_value-baseline_mean)/max(baseline_mean,1)

def overlaps(event_date, other_date) -> bool:
    return abs((event_date-other_date).days)<=7

def eligible_for_ranking(sample_size: int, evidence_grade: str) -> bool:
    return sample_size>=10 and evidence_grade not in {"unavailable","blocked","missing"}

def parse_day(value: str) -> date:
    return date.fromisoformat(value[:10])

def mean(values):
    return sum(values)/len(values) if values else None

def percentile(values, p):
    if not values: return None
    vals=sorted(values); index=(len(vals)-1)*p; low=int(index); high=min(low+1,len(vals)-1)
    return vals[low]+(vals[high]-vals[low])*(index-low)

def bootstrap_interval(values, rounds=400):
    """Deterministic bootstrap of the sample median; no hidden random seed."""
    if len(values)<2: return (None,None)
    import random
    rng=random.Random(20260802)
    medians=[statistics.median([values[rng.randrange(len(values))] for _ in values]) for _ in range(rounds)]
    return percentile(medians,.025), percentile(medians,.975)

def event_study_rows():
    moments=json.loads((ROOT/'data/curated/moment.json').read_text())
    attention=load_attention_channels()
    by_club_channel=defaultdict(dict)
    for row in attention:
        if row.get('metric_value') is not None:
            by_club_channel[(row['club_id'],row['channel'])][parse_day(row['date_utc'])]=row['metric_value']
    moment_days=defaultdict(list)
    for moment in moments:
        moment_days[moment['club_id']].append((moment['moment_id'],parse_day(moment['moment_time_utc']),moment.get('game_id')))
    rows=[]
    for moment in moments:
        club=moment['club_id']; event_day=parse_day(moment['moment_time_utc'])
        # Any different game/event in the +/-7d envelope is recorded. The primary
        # simple event-study estimate excludes it rather than calling it isolated.
        overlap=any(mid!=moment['moment_id'] and abs((day-event_day).days)<=7 and gid!=moment.get('game_id') for mid,day,gid in moment_days[club])
        channels=sorted(channel for candidate_club,channel in by_club_channel if candidate_club==club)
        for channel in channels:
            daily=by_club_channel[(club,channel)]
            baseline=[daily[event_day-timedelta(days=n)] for n in range(1,BASELINE_DAYS+1) if event_day-timedelta(days=n) in daily]
            base=mean(baseline)
            for window_name,(start,end) in WINDOWS.items():
                post=[daily[event_day+timedelta(days=n)] for n in range(start,end+1) if event_day+timedelta(days=n) in daily]
                if base is None or len(baseline)<BASELINE_DAYS or len(post)!=(end-start+1):
                    status='missing_attention_coverage'; lift=None
                elif overlap:
                    status='excluded_overlapping_major_event'; lift=None
                else:
                    status='eligible'; lift=attention_lift(mean(post),base)
                rows.append({'moment_id':moment['moment_id'],'club_id':club,'game_id':moment.get('game_id'),'moment_type':moment['moment_type'],'attention_channel':channel,'post_window':window_name,'event_date_utc':event_day.isoformat(),'baseline_mean':base,'baseline_observation_count':len(baseline),'post_observation_count':len(post),'overlap_excluded':overlap,'attention_lift':lift,'evidence_status':status})
    return rows

def sensitivity_estimates(baseline_days, channel):
    """Recompute isolated raw medians under a registered baseline length."""
    moments=json.loads((ROOT/'data/curated/moment.json').read_text())
    attention=[row for row in load_attention_channels() if row.get('channel')==channel]
    by_club=defaultdict(dict)
    for row in attention:
        if row.get('metric_value') is not None:
            by_club[row['club_id']][parse_day(row['date_utc'])]=row['metric_value']
    moment_days=defaultdict(list)
    for moment in moments:
        moment_days[moment['club_id']].append((moment['moment_id'],parse_day(moment['moment_time_utc']),moment.get('game_id')))
    grouped=defaultdict(list)
    for moment in moments:
        club=moment['club_id']; event_day=parse_day(moment['moment_time_utc']); daily=by_club.get(club,{})
        overlap=any(mid!=moment['moment_id'] and abs((day-event_day).days)<=7 and gid!=moment.get('game_id') for mid,day,gid in moment_days[club])
        baseline=[daily[event_day-timedelta(days=n)] for n in range(1,baseline_days+1) if event_day-timedelta(days=n) in daily]
        if overlap or len(baseline)!=baseline_days: continue
        base=mean(baseline)
        for window,(start,end) in WINDOWS.items():
            post=[daily[event_day+timedelta(days=n)] for n in range(start,end+1) if event_day+timedelta(days=n) in daily]
            if len(post)==end-start+1:
                grouped[(club,moment['moment_type'],window)].append(attention_lift(mean(post),base))
    return [{'baseline_days':baseline_days,'attention_channel':channel,'club_id':club,'moment_type':kind,'post_window':window,'raw_median_lift':statistics.median(values),'sample_size':len(values)} for (club,kind,window),values in sorted(grouped.items())]

def season_for_day(day):
    return f"{day.year}{day.year+1}" if day.month>=7 else f"{day.year-1}{day.year}"

def fit_hierarchical_channel(rows, channel):
    import math
    import numpy as np
    import pandas as pd
    import statsmodels.formula.api as smf
    games=json.loads((ROOT/'data/curated/game.json').read_text())
    moments=json.loads((ROOT/'data/curated/moment.json').read_text())
    attention=[row for row in load_attention_channels() if row.get('channel')==channel]
    registered=sorted({m['moment_type'] for m in moments})
    features=[f"m__{kind}__{window}" for kind in registered for window in WINDOWS]
    by_club_games=defaultdict(lambda:defaultdict(list))
    for game in games:
        if game.get('game_type') not in {2,3} or game.get('home_score') is None: continue
        day=parse_day(game['start_time_utc'])
        by_club_games[game['home_club_id']][day].append((game,'home'))
        by_club_games[game['away_club_id']][day].append((game,'away'))
    exposures=defaultdict(lambda:defaultdict(int))
    for moment in moments:
        event_day=parse_day(moment['moment_time_utc'])
        for window,(start,end) in WINDOWS.items():
            for offset in range(start,end+1): exposures[(moment['club_id'],event_day+timedelta(days=offset))][f"m__{moment['moment_type']}__{window}"]+=1
    records=[]
    for club,club_rows in __import__('itertools').groupby(sorted(attention,key=lambda x:(x['club_id'],x['date_utc'])),key=lambda x:x['club_id']):
        points=0; played=0
        for row in club_rows:
            day=parse_day(row['date_utc']); day_games=by_club_games[club].get(day,[])
            context=points/max(2*played,1) if played else 0.5
            home_away='no_game'; opponent='none'
            if day_games:
                game,home_away=day_games[0]; opponent=game['away_club_id'] if home_away=='home' else game['home_club_id']
            rec={'club_id':club,'date':day,'log_attention':math.log(float(row['metric_value'])+1),'home_away':home_away,'opponent':opponent,'standings_context':context,'day_of_week':day.weekday(),'month':day.month,'season':season_for_day(day)}
            rec.update({name:exposures[(club,day)].get(name,0) for name in features});records.append(rec)
            for game,side in day_games:
                own=game['home_score'] if side=='home' else game['away_score']; other=game['away_score'] if side=='home' else game['home_score']
                points += 2 if own>other else (1 if game.get('final_state') in {'OT','SO'} else 0); played += 1
    frame=pd.DataFrame(records)
    # Remove empty/constant moment columns before Patsy constructs the matrix.
    # Opponent is a crossed random effect: retaining hundreds of sparse opponent
    # fixed-effect columns made the original design rank deficient.
    active_features=[name for name in features if frame[name].nunique()>1 and frame[name].sum()>0]
    formula='log_attention ~ '+' + '.join(active_features)+" + C(home_away) + standings_context + C(day_of_week) + C(month) + C(season)"
    model=smf.mixedlm(
        formula,frame,groups=frame['club_id'],re_formula='1',
        vc_formula={'opponent_effect':'0 + C(opponent)'},
    )
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter('always')
        result=model.fit(reml=False,method=['lbfgs','powell'],maxiter=500,disp=False)
    optimization_warnings=sorted({f"{type(item.message).__name__}: {item.message}" for item in caught_warnings})
    fixed=result.fe_params; se=result.bse_fe
    isolated=defaultdict(list)
    for row in rows:
        if row['attention_lift'] is not None: isolated[(row['club_id'],row['moment_type'],row['post_window'])].append(row['attention_lift'])
    modeled_counts=defaultdict(int)
    for row in rows:
        if row['evidence_status'] in {'eligible','excluded_overlapping_major_event'}:
            modeled_counts[(row['club_id'],row['moment_type'],row['post_window'])]+=1
    estimates=[]
    clubs=sorted({x['club_id'] for x in attention})
    for club in clubs:
        for kind in registered:
            for window in WINDOWS:
                name=f'm__{kind}__{window}'; beta=float(fixed.get(name,float('nan'))); stderr=float(se.get(name,float('nan')))
                low=beta-1.96*stderr; high=beta+1.96*stderr; n=modeled_counts[(club,kind,window)]; raw=isolated[(club,kind,window)]
                raw_low,raw_high=bootstrap_interval(raw)
                grade='confirmed_partial_pooling' if n>=10 and math.isfinite(beta) and math.isfinite(stderr) else 'suppressed_small_sample'
                interpretation='partially pooled association in expected public pageviews; not causal lift' if channel=='wikimedia_pageviews' else 'partially pooled association in normalized earned-media article observations; not readership, sentiment, or causal lift'
                estimates.append({'club_id':club,'moment_type':kind,'attention_channel':channel,'post_window':window,'estimate':math.exp(beta)-1 if math.isfinite(beta) else None,'confidence_interval_low':math.exp(low)-1 if math.isfinite(low) else None,'confidence_interval_high':math.exp(high)-1 if math.isfinite(high) else None,'raw_median_lift':statistics.median(raw) if raw else None,'raw_confidence_interval_low':raw_low,'raw_confidence_interval_high':raw_high,'sample_size':n,'isolated_sample_size':len(raw),'evidence_grade':grade,'ranking_eligible':n>=10 and grade=='confirmed_partial_pooling' and len(raw)>=10,'model_version':MODEL_VERSION,'calculated_at':'2026-08-03','estimate_interpretation':interpretation})
    random_effects={club:{key:float(value) for key,value in effect.items()} for club,effect in result.random_effects.items()}
    sensitivity={str(days):sensitivity_estimates(days,channel) for days in (7,21)}
    outcome='log(Wikimedia daily pageviews + 1)' if channel=='wikimedia_pageviews' else 'log(GDELT exact-name English article observations per 100,000 monitored articles + 1)'
    return {'attention_channel':channel,'status':'confirmed' if result.converged else 'unavailable_nonconverged','formula':formula,'opponent_control':'crossed random intercept','outcome':outcome,'overlap_rule':'Moment-window indicators enter jointly; overlapping events are modeled together. Isolated raw medians remain separately reported.','baseline_days':BASELINE_DAYS,'windows':WINDOWS,'sensitivity_baselines':[7,21],'sensitivity_estimates':sensitivity,'n_daily_observations':len(frame),'active_moment_features':active_features,'club_random_intercepts':random_effects,'converged':bool(result.converged),'log_likelihood':float(result.llf),'optimization_warnings':optimization_warnings,'suppression_rule':'club/moment modeled or isolated sample_size < 10','estimates':estimates}


def cross_channel_assessments(estimates):
    """Require two independently eligible channels before using 'stable'."""
    grouped=defaultdict(dict)
    for row in estimates:
        grouped[(row['club_id'],row['moment_type'],row['post_window'])][row['attention_channel']]=row
    assessments=[]
    required={'wikimedia_pageviews','gdelt_earned_media'}
    for (club,kind,window),channels in sorted(grouped.items()):
        if not required.issubset(channels):
            status='insufficient_channel_coverage'
        else:
            pair=[channels[name] for name in sorted(required)]
            eligible=all(row.get('ranking_eligible') and row.get('estimate') is not None for row in pair)
            model_precise=all(row.get('confidence_interval_low') is not None and row.get('confidence_interval_high') is not None and not (row['confidence_interval_low']<=0<=row['confidence_interval_high']) for row in pair)
            raw_precise=all(row.get('raw_confidence_interval_low') is not None and row.get('raw_confidence_interval_high') is not None and not (row['raw_confidence_interval_low']<=0<=row['raw_confidence_interval_high']) for row in pair)
            same_positive=all(row['estimate']>0 and row.get('raw_median_lift') is not None and row['raw_median_lift']>0 for row in pair)
            same_negative=all(row['estimate']<0 and row.get('raw_median_lift') is not None and row['raw_median_lift']<0 for row in pair)
            if eligible and model_precise and raw_precise and same_positive:
                status='stable_positive'
            elif eligible and model_precise and raw_precise and same_negative:
                status='stable_negative'
            elif eligible and not (same_positive or same_negative):
                status='mixed_direction'
            else:
                status='insufficient_evidence'
        assessments.append({'club_id':club,'moment_type':kind,'post_window':window,'cross_channel_status':status,'stable':status in {'stable_positive','stable_negative'},'required_channels':sorted(required),'rule':'both channels have at least 10 modeled and 10 isolated observations; modeled and club-local raw medians share direction across channels; every modeled and raw 95% interval excludes zero'})
    return assessments

def build():
    rows=event_study_rows(); groups=defaultdict(list)
    for row in rows:
        if row['evidence_status']=='eligible': groups[(row['club_id'],row['moment_type'],row['attention_channel'],row['post_window'])].append(row['attention_lift'])
    estimates=[]
    for (club,kind,channel,window), values in sorted(groups.items()):
        n=len(values); low,high=bootstrap_interval(values)
        grade='descriptive_public_evidence' if n>=10 else 'suppressed_small_sample'
        estimates.append({'club_id':club,'moment_type':kind,'attention_channel':channel,'post_window':window,'estimate':statistics.median(values),'confidence_interval_low':low,'confidence_interval_high':high,'raw_median_lift':statistics.median(values),'sample_size':n,'evidence_grade':grade,'ranking_eligible':eligible_for_ranking(n,grade),'model_version':'0.2.0-event-study','calculated_at':'deterministic-build'})
    write_json('data/curated/attention_event_window.json',rows)
    channels=sorted({row['attention_channel'] for row in rows})
    try:
        channel_models=[fit_hierarchical_channel([row for row in rows if row['attention_channel']==channel],channel) for channel in channels]
        combined=[estimate for model in channel_models for estimate in model['estimates']]
        result={'model_version':MODEL_VERSION,'status':'confirmed' if len(channel_models)>=2 and all(model['converged'] for model in channel_models) else 'unavailable_requires_two_converged_channels','converged':len(channel_models)>=2 and all(model['converged'] for model in channel_models),'channels':channels,'channel_models':channel_models,'estimates':combined,'cross_channel_assessments':cross_channel_assessments(combined),'suppression_rule':'club/moment modeled or isolated sample_size < 10; stable requires two channels with the same precise modeled and club-local raw direction'}
    except ImportError as exc: result={'model_version':MODEL_VERSION,'status':'unavailable_missing_dependency','reason':str(exc),'estimates':estimates,'cross_channel_assessments':[]}
    return write_json('data/curated/club_moment_estimate.json',result)
if __name__=='__main__': print(build())
