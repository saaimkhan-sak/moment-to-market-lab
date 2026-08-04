const DATA='/data/';
const WINDOWS={immediate:'Day 0–1',short_persistence:'Days 2–3',sustained_attention:'Days 4–7'};
const SOURCES={both:'Wikimedia + GDELT',wikimedia_pageviews:'Wikimedia Pageviews',gdelt_earned_media:'GDELT earned media'};
const fmt=new Intl.NumberFormat('en-US');
const pct=value=>value==null?'—':`${value>=0?'+':''}${(value*100).toFixed(1)}%`;
const title=value=>(value||'').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));

function initialSlug(){
  const match=location.pathname.match(/\/clubs\/([^/]+)/);
  return match?.[1]||new URLSearchParams(location.search).get('club')||'carolina-hurricanes';
}

function routeFor(slug,moment,window,source){
  const params=new URLSearchParams({moment,window,source});
  if(location.hostname==='localhost'||location.hostname==='127.0.0.1'){params.set('club',slug);return `/?${params}`}
  return `/clubs/${slug}?${params}`;
}

function assessment(model,club,moment,window){
  return model.cross_channel_assessments.find(row=>row.club_id===club&&row.moment_type===moment&&row.post_window===window);
}

function singleEstimate(model,club,moment,window,source){
  return model.estimates.find(row=>row.club_id===club&&row.moment_type===moment&&row.post_window===window&&row.attention_channel===source);
}

function assessmentSample(model,club,moment,window){
  const values=['wikimedia_pageviews','gdelt_earned_media'].map(source=>singleEstimate(model,club,moment,window,source)?.sample_size).filter(value=>value!=null);
  return values.length===2?Math.min(...values):null;
}

function renderFinding(state){
  const {profile,moment,window,source,model}=state;
  const count=profile.moment_type_counts[moment]||0;
  const context=`${profile.club_name.toUpperCase()} · ${title(moment)} · ${WINDOWS[window].toUpperCase()}`;
  document.querySelector('#finding-context').textContent=context;
  let headline,why,falsify,status,sample,stateName='no-signal';
  if(source==='both'){
    const row=assessment(model,profile.club_id,moment,window);
    if(row?.stable){
      const direction=row.cross_channel_status==='stable_positive'?'positive':'negative';
      headline=`${title(moment)} showed a stable ${direction} public-attention association in the ${WINDOWS[window].toLowerCase()} window.`;
      why='Wikimedia information demand and audited GDELT earned-media volume agree in both modeled and club-local raw direction, and every modeled and raw 95% interval excludes zero.';
      falsify='A channel reversal, an interval crossing zero after refresh, a precision failure, or a material change under the registered 7-day and 21-day baseline checks.';
      status=`STABLE ${direction.toUpperCase()} ASSOCIATION`; sample=assessmentSample(model,profile.club_id,moment,window); stateName='confirmed';
    }else{
      headline='No reliable two-channel public-response pattern is visible in this cell. Do not operationalize a moment ranking.';
      why=row?'The available channels do not jointly clear the registered agreement, precision, and sample rules.':'This club–moment–window cell lacks complete evidence in both registered channels.';
      falsify='At least ten modeled and ten isolated observations in each channel, aligned modeled and raw direction, and separate modeled and raw 95% intervals that exclude zero.';
      status='NO RELIABLE TWO-CHANNEL SIGNAL';sample=assessmentSample(model,profile.club_id,moment,window);
    }
  }else{
    const row=singleEstimate(model,profile.club_id,moment,window,source);
    const precise=row&&row.confidence_interval_low!=null&&row.confidence_interval_high!=null&&!(row.confidence_interval_low<=0&&row.confidence_interval_high>=0);
    if(row?.ranking_eligible&&precise){
      headline=`${SOURCES[source]} shows a descriptive ${row.estimate>=0?'positive':'negative'} association for ${title(moment).toLowerCase()}.`;
      why='This source clears its own sample and interval rules, but the second independent channel is intentionally not included in the current view.';
      falsify='A contradictory second channel, a confidence interval crossing zero, or sensitivity to the registered baseline windows.';
      status='SINGLE-CHANNEL DESCRIPTION';sample=row.sample_size;stateName='caution';
    }else{
      headline='No reliable public-response pattern is visible in the selected source and window.';
      why='The cell does not clear the registered single-source sample and precision checks.';
      falsify='At least ten comparable observations and a modeled interval that excludes zero, followed by independent-channel corroboration.';
      status='NO RELIABLE SINGLE-SOURCE SIGNAL';sample=row?.sample_size||0;
    }
  }
  document.querySelector('#finding-title').textContent=headline;
  document.querySelector('#finding-what').textContent=`The objective taxonomy identified ${fmt.format(count)} ${title(moment).toLowerCase()} observations for ${profile.club_name} in the archive.`;
  document.querySelector('#finding-why').textContent=why;
  document.querySelector('#finding-falsify').textContent=falsify;
  const stamp=document.querySelector('.evidence-stamp');stamp.dataset.state=stateName;
  document.querySelector('#stamp-status').textContent=status;
  document.querySelector('#stamp-sources').textContent=SOURCES[source].toUpperCase();
  document.querySelector('#stamp-sample').textContent=sample==null?'MINIMUM N = UNAVAILABLE':`MINIMUM N = ${fmt.format(sample)}`;
  document.querySelector('#stamp-window').textContent=`WINDOW: ${WINDOWS[window].toUpperCase()}`;
}

function tracePath(points,x,y){
  const segments=[];let active=[];
  points.forEach(point=>{if(point.median_difference==null){if(active.length){segments.push(active);active=[]}}else active.push(point)});
  if(active.length)segments.push(active);
  return segments.map(segment=>`M${segment.map(point=>`${x(point.day_offset).toFixed(1)},${y(point.median_difference).toFixed(1)}`).join(' L')}`).join(' ');
}

function renderTrace(state){
  const {profile,moment,source,traces}=state;
  const wanted=source==='both'?['wikimedia_pageviews','gdelt_earned_media']:[source];
  const series=wanted.map(channel=>traces.find(row=>row.club_id===profile.club_id&&row.moment_type===moment&&row.attention_channel===channel)).filter(Boolean);
  const values=series.flatMap(row=>row.points.map(point=>point.median_difference).filter(value=>value!=null));
  document.querySelector('#trace-title').textContent=`What changed around ${title(moment).toLowerCase()}?`;
  document.querySelector('#trace-subtitle').textContent=`Median observed difference from each event’s 14-day pre-event mean. ${SOURCES[source]}; isolated events only; Day −7 through Day +7.`;
  const graphic=document.querySelector('#trace-graphic');
  const table=document.querySelector('#trace-table');
  if(!values.length){
    graphic.innerHTML=`<div class="no-signal"><strong>No complete isolated response trace is available.</strong><p>Coverage gaps or overlapping moments prevent a reliable aligned series. Use the event docket below; do not fill the chart with inferred values.</p></div>`;
    table.innerHTML='<p>No accessible trace values are available for this selection.</p>';return;
  }
  const W=780,H=300,m={l:52,r:100,t:30,b:42};
  let min=Math.min(0,...values),max=Math.max(0,...values);if(min===max){min-=.1;max+=.1}const pad=(max-min)*.12;min-=pad;max+=pad;
  const x=value=>m.l+(value+7)/14*(W-m.l-m.r),y=value=>m.t+(max-value)/(max-min)*(H-m.t-m.b);
  const grid=[min,0,max];
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="trace-svg-title trace-svg-desc"><title id="trace-svg-title">${esc(title(moment))} public-signal trace</title><desc id="trace-svg-desc">Median normalized public signal from seven days before through seven days after the selected moment. Day zero is the event.</desc>`;
  grid.forEach(value=>{svg+=`<line class="${Math.abs(value)<1e-9?'chart-zero':'chart-rule'}" x1="${m.l}" x2="${W-m.r}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-label" x="${m.l-8}" y="${y(value)+4}" text-anchor="end">${pct(value)}</text>`});
  svg+=`<line class="chart-event" x1="${x(0)}" x2="${x(0)}" y1="${m.t}" y2="${H-m.b}"/><text class="chart-label" x="${x(0)}" y="18" text-anchor="middle">DAY 0 · EVENT</text>`;
  [-7,-3,0,3,7].forEach(value=>svg+=`<text class="chart-label" x="${x(value)}" y="${H-15}" text-anchor="middle">${value>0?'+':''}${value}</text>`);
  series.forEach((row,index)=>{const klass=row.attention_channel==='wikimedia_pageviews'?'chart-wikimedia':'chart-gdelt';svg+=`<path class="${klass}" d="${tracePath(row.points,x,y)}"/>`;const last=[...row.points].reverse().find(point=>point.median_difference!=null);if(last)svg+=`<text class="chart-end" x="${x(last.day_offset)+8}" y="${y(last.median_difference)+4}">${row.attention_channel==='wikimedia_pageviews'?'WIKIMEDIA':'GDELT'} · N ${last.sample_size}</text>`});
  graphic.innerHTML=svg+'</svg>';
  const offsets=Array.from({length:15},(_,index)=>index-7);
  table.innerHTML=`<table><thead><tr><th>DAY</th>${series.map(row=>`<th>${esc(SOURCES[row.attention_channel])}</th><th>N</th>`).join('')}</tr></thead><tbody>${offsets.map(offset=>`<tr><td>${offset>0?'+':''}${offset}</td>${series.map(row=>{const point=row.points.find(p=>p.day_offset===offset);return `<td>${pct(point?.median_difference)}</td><td>${point?.sample_size||0}</td>`}).join('')}</tr>`).join('')}</tbody></table>`;
}

function renderDocket(state){
  const {profile,moment,window,source,moments,games,eventWindows}=state;
  const gameMap=new Map(games.map(row=>[row.game_id,row]));
  const rows=moments.filter(row=>row.club_id===profile.club_id&&row.moment_type===moment).sort((a,b)=>b.moment_time_utc.localeCompare(a.moment_time_utc)).slice(0,30);
  document.querySelector('#docket-title').textContent=`${title(moment)}: qualifying events and source trail`;
  const head='<div class="docket-head"><span>DATE</span><span>OPPONENT / CONTEXT</span><span>PUBLIC SIGNALS</span><span>WINDOW</span><span>COVERAGE</span><span>SOURCE</span></div>';
  const body=rows.map(row=>{
    const game=gameMap.get(row.game_id)||{};
    const channels=source==='both'?['wikimedia_pageviews','gdelt_earned_media']:[source];
    const evidence=channels.map(channel=>eventWindows.find(item=>item.moment_id===row.moment_id&&item.post_window===window&&item.attention_channel===channel)).filter(Boolean);
    const statuses=evidence.map(item=>item.evidence_status);
    const coverage=!evidence.length?'unavailable':statuses.every(value=>value==='eligible')?'eligible':statuses.includes('excluded_overlapping_major_event')?'overlap excluded':'coverage gap';
    const context=row.opponent_id?`${row.opponent_id} · ${game.final_state||'final'}`:title(row.moment_type);
    const sourceUrl=row.source_url||game.source_url||'#';
    return `<details class="docket-row"><summary><span data-label="DATE">${esc(row.moment_time_utc.slice(0,10))}</span><span data-label="OPPONENT / CONTEXT">${esc(context)}</span><span data-label="PUBLIC SIGNALS">${esc(SOURCES[source])}</span><span data-label="WINDOW">${esc(WINDOWS[window])}</span><span data-label="COVERAGE">${esc(coverage)}</span><span data-label="SOURCE">OPEN +</span></summary><div class="docket-detail"><p><b>Matching logic.</b> ${esc(title(row.moment_type))} was emitted by trigger <code>${esc(row.trigger_rule_id)}</code> under rule ${esc(row.rule_version)}. ${coverage==='eligible'?'The selected response window has complete isolated coverage.':'This row is retained, but the selected estimate is not treated as isolated evidence.'}</p><dl><dt>EVENT ID</dt><dd>${esc(row.moment_id)}</dd><dt>EVIDENCE STATE</dt><dd>${esc(row.evidence_status)}</dd><dt>SOURCE</dt><dd><a href="${esc(sourceUrl)}" target="_blank" rel="noreferrer">Open archived/public evidence ↗</a></dd></dl></div></details>`;
  }).join('');
  document.querySelector('#moment-docket').innerHTML=head+(body||'<div class="no-signal"><strong>No qualifying events are registered for this selection.</strong><p>The empty state is preserved; no examples were hand-picked after reviewing attention data.</p></div>');
}

function renderYouTube(profile,summaries,moment){
  const row=summaries.find(item=>item.club_id===profile.club_id);
  if(!row)return;
  const historical=(row.historical_publication_by_moment||[]).find(item=>item.moment_type===moment);
  document.querySelector('#youtube-summary').textContent=`${profile.club_name}’s verified official channel archive contains ${fmt.format(row.video_count)} accessible videos published from ${row.oldest_published_at.slice(0,10)} through ${row.newest_published_at.slice(0,10)}. Format counts are descriptive title matches and may overlap.`;
  const formats=Object.entries(row.format_counts).sort((a,b)=>b[1]-a[1]);
  document.querySelector('#youtube-formats').innerHTML=`<table class="format-ledger"><thead><tr><th>REGISTERED TITLE FORMAT</th><th>VIDEOS</th></tr></thead><tbody>${formats.map(([label,count])=>`<tr><td>${esc(title(label))}</td><td>${fmt.format(count)}</td></tr>`).join('')}</tbody></table>`;
  const historicalBlock=historical
    ? `<div class="publication-evidence"><h3>${esc(title(moment))}: event-time publication evidence</h3><dl><dt>QUALIFYING MOMENTS WITH AN OFFICIAL UPLOAD</dt><dd>${fmt.format(historical.qualifying_moments_with_uploads)}</dd><dt>UPLOADS · DAY 0–1 / DAYS 2–3 / DAYS 4–7</dt><dd>${fmt.format(historical.official_uploads_by_window.immediate||0)} / ${fmt.format(historical.official_uploads_by_window.short_persistence||0)} / ${fmt.format(historical.official_uploads_by_window.sustained_attention||0)}</dd><dt>COMMENT TARGETS CONFIRMED</dt><dd>${fmt.format(historical.comment_targets_confirmed)} OF ${fmt.format(historical.comment_target_count)}</dd><dt>SURVIVING TOP-LEVEL COMMENTS · DAY 0–1 / DAYS 2–3 / DAYS 4–7</dt><dd>${fmt.format(historical.surviving_top_level_comments_by_window.immediate||0)} / ${fmt.format(historical.surviving_top_level_comments_by_window.short_persistence||0)} / ${fmt.format(historical.surviving_top_level_comments_by_window.sustained_attention||0)}</dd></dl><p class="method-note">${esc(row.historical_publication_scope)}</p></div>`
    : `<div class="no-signal"><strong>No event-time official-upload observation is registered for this moment selection.</strong><p>The interface does not substitute current view totals for missing historical performance.</p></div>`;
  document.querySelector('#youtube-videos').innerHTML=historicalBlock+`<h3>Largest current public view snapshots</h3><table class="video-ledger"><tbody>${row.top_current_public_view_snapshots.slice(0,5).map(video=>`<tr><td>${fmt.format(Number(video.view_count||0))} VIEWS</td><td><a href="${esc(video.source_url)}" target="_blank" rel="noreferrer">${esc(video.title)}</a><br><span class="method-note">Published ${esc(video.published_at.slice(0,10))}</span></td></tr>`).join('')}</tbody></table><p class="method-note">${esc(row.limitation)}</p>`;
}

function formatMetric(row){
  if(row.metric_value==null)return 'Unavailable';
  if(row.unit==='persons'||row.metric_name==='population')return fmt.format(Math.round(row.metric_value));
  if(row.metric_name.includes('income'))return `${row.country==='CA'?'CAD':'USD'} ${fmt.format(Math.round(row.metric_value))}`;
  if(row.metric_name.includes('pct')||row.unit==='percent')return `${Number(row.metric_value).toFixed(1)}%`;
  if(row.metric_name.includes('_lq_'))return Number(row.metric_value).toFixed(2);
  return Number(row.metric_value).toLocaleString(undefined,{maximumFractionDigits:2});
}

function renderMarket(profile,market){
  const rows=market.filter(row=>row.club_id===profile.club_id&&row.evidence_status==='confirmed');
  const core=['population','median_age','average_age','median_household_income_usd','median_household_income_cad','unemployment_rate_pct','bachelors_or_higher_pct','regional_price_parity_all_items'];
  const selected=core.map(metric=>rows.find(row=>row.metric_name===metric)).filter(Boolean);
  const lqs=rows.filter(row=>row.metric_name.startsWith('preferred_industry_lq_')).sort((a,b)=>b.metric_value-a.metric_value).slice(0,3);
  document.querySelector('#market-table').innerHTML=`<table class="market-ledger"><thead><tr><th>MEASURE</th><th>VALUE</th></tr></thead><tbody>${selected.map(row=>`<tr><td>${esc(title(row.metric_name))}<br><span class="method-note">${esc(row.reference_period)}</span></td><td>${esc(formatMetric(row))}</td></tr>`).join('')}${lqs.map(row=>`<tr><td>${esc(title(row.metric_name.replace('preferred_industry_lq_','Industry LQ: ')))}<br><span class="method-note">${esc(row.reference_period)} · ${row.fallback_used?'ACS fallback':'QCEW'}</span></td><td>${esc(formatMetric(row))}</td></tr>`).join('')}</tbody></table>`;
}

function renderPlaybooks(profile,playbooks,moment){
  const rows=playbooks.filter(row=>row.club_id===profile.club_id).sort((a,b)=>(a.moment_type===moment?-1:0)-(b.moment_type===moment?-1:0)||a.priority_within_club-b.priority_within_club);
  document.querySelector('#playbook-intro').textContent=`Three ${profile.club_name} test notes selected from the final evidence panel. “Stable” is reserved for agreement across Wikimedia and GDELT; every internal KPI still requires club validation.`;
  document.querySelector('#playbook-list').innerHTML=rows.map(row=>`<article class="playbook-record"><header class="playbook-record__head"><span>${esc(title(row.moment_type))}</span><span>OWNER TYPE: ${esc(row.owner_function.toUpperCase())}</span><span>${esc(title(row.confidence_label))}</span></header><div class="action-strip"><div class="action-step"><b>0–24 HOURS</b><p>${esc(row.action_0_24h)}</p></div><div class="action-step"><b>24–72 HOURS</b><p>${esc(row.action_24_72h)}</p></div><div class="action-step"><b>DAY 4–7</b><p>${esc(row.action_day_4_7)}</p></div></div><footer class="playbook-foot"><div><b>PUBLIC METRIC</b>${esc(row.public_kpi)}</div><div><b>INTERNAL KPI</b>${esc(row.internal_kpi)}</div><div class="validation-flag"><b>REQUIRES INTERNAL VALIDATION</b>${esc(row.internal_data_required)}</div></footer></article>`).join('');
}

function renderLeague(summary){
  const rows=Object.entries(summary.stable_cells_by_moment).sort((a,b)=>b[1]-a[1]);
  document.querySelector('#league-benchmark').innerHTML=(rows.length?rows:[['no_registered_stable_pattern',0]]).map(([moment,count])=>`<tr><td>${esc(title(moment))}</td><td>${fmt.format(count)}</td></tr>`).join('');
  document.querySelector('#coverage-rail').innerHTML=Object.entries(summary.source_coverage).map(([source,status])=>`<dt>${esc(title(source))}</dt><dd class="${status==='confirmed'?'status-confirmed':'status-qualified'}">${esc(title(status))}</dd>`).join('');
  document.querySelector('#stable-rule').textContent=summary.stable_rule;
}

function populateMoments(state,preferred){
  const counts=state.profile.moment_type_counts;
  const moments=Object.keys(counts).sort((a,b)=>counts[b]-counts[a]||a.localeCompare(b));
  const select=document.querySelector('#moment-select');select.innerHTML=moments.map(moment=>`<option value="${esc(moment)}">${esc(title(moment))} · N ${fmt.format(counts[moment])}</option>`).join('');
  const defaultMoment=preferred&&moments.includes(preferred)?preferred:moments[0];select.value=defaultMoment;return defaultMoment;
}

async function main(data){
  const [profiles,league]=data;
  const clubSelect=document.querySelector('#club-select');
  profiles.sort((a,b)=>a.club_name.localeCompare(b.club_name));
  clubSelect.innerHTML=profiles.map(row=>`<option value="${esc(row.club_slug)}">${esc(row.club_name)}</option>`).join('');
  clubSelect.value=profiles.some(row=>row.club_slug===initialSlug())?initialSlug():'carolina-hurricanes';
  const initialParams=new URLSearchParams(location.search);
  if(WINDOWS[initialParams.get('window')])document.querySelector('#window-select').value=initialParams.get('window');
  if(SOURCES[initialParams.get('source')])document.querySelector('#source-select').value=initialParams.get('source');
  let initialMoment=initialParams.get('moment');
  const state={profiles,league};
  renderLeague(league);

  async function loadClub(slug){
    clubSelect.disabled=true;
    const response=await fetch(`${DATA}clubs/${slug}.json`);
    if(!response.ok)throw new Error(`${slug}.json: ${response.status}`);
    const bundle=await response.json();
    Object.assign(state,bundle);
    state.eventWindows=bundle.event_windows;
    clubSelect.disabled=false;
  }

  async function render({clubChanged=false}={}){
    if(clubChanged||state.profile?.club_slug!==clubSelect.value)await loadClub(clubSelect.value);
    if(clubChanged||!document.querySelector('#moment-select').value){state.moment=populateMoments(state,initialMoment);initialMoment=null;}
    else state.moment=document.querySelector('#moment-select').value;
    state.window=document.querySelector('#window-select').value;
    state.source=document.querySelector('#source-select').value;
    document.documentElement.style.setProperty('--club-accent',state.profile.club_accent);
    document.querySelector('#club-name').textContent=state.profile.club_name;
    document.querySelector('#club-market').textContent=state.profile.market_name;
    document.querySelector('#club-coverage').textContent=`${fmt.format(state.profile.moment_records)} MOMENTS · ${fmt.format(state.profile.attention_days_by_channel.wikimedia_pageviews)} WIKIMEDIA DAYS · ${fmt.format(state.profile.attention_days_by_channel.gdelt_earned_media)} GDELT DAYS`;
    document.querySelector('#active-filter').textContent=`Showing ${state.profile.club_name}; ${title(state.moment)}; ${WINDOWS[state.window]}; ${SOURCES[state.source]}.`;
    document.querySelector('#memo-link').href=state.memo_path;
    document.title=`${state.profile.club_name} · NHL Moment-to-Market Lab`;
    renderFinding(state);renderTrace(state);renderDocket(state);renderYouTube(state.profile,state.youtube,state.moment);renderMarket(state.profile,state.market);renderPlaybooks(state.profile,state.playbooks,state.moment);
    history.replaceState({},'',routeFor(state.profile.club_slug,state.moment,state.window,state.source));
  }
  clubSelect.addEventListener('change',()=>render({clubChanged:true}).catch(showFailure));
  document.querySelector('#moment-select').addEventListener('change',()=>render().catch(showFailure));
  document.querySelector('#window-select').addEventListener('change',()=>render().catch(showFailure));
  document.querySelector('#source-select').addEventListener('change',()=>render().catch(showFailure));
  addEventListener('popstate',()=>{const slug=initialSlug(),params=new URLSearchParams(location.search);if(profiles.some(row=>row.club_slug===slug)){clubSelect.value=slug;if(WINDOWS[params.get('window')])document.querySelector('#window-select').value=params.get('window');if(SOURCES[params.get('source')])document.querySelector('#source-select').value=params.get('source');initialMoment=params.get('moment');render({clubChanged:true}).catch(showFailure)}});
  await render({clubChanged:true});
}

function showFailure(error){
  document.querySelector('#finding-title').textContent='The final research release has not been assembled.';
  document.querySelector('#finding-what').textContent='A required curated file is missing or failed validation.';
  document.querySelector('#finding-why').textContent='The interface fails closed instead of rendering stale or fabricated findings.';
  document.querySelector('#finding-falsify').textContent='Complete the registered build and release checks, then reload.';
  document.querySelector('#trace-graphic').innerHTML=`<div class="no-signal"><strong>Validated release data required.</strong><p>${esc(error.message)}</p></div>`;
}

Promise.all(['club_index.json','league_summary.json'].map(file=>fetch(DATA+file).then(response=>{if(!response.ok)throw new Error(`${file}: ${response.status}`);return response.json()}))).then(main).catch(showFailure);
