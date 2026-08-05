const DATA = '/data/';

const WINDOWS = {
  immediate: 'first 48 hours',
  short_persistence: 'next two days',
  sustained_attention: 'rest of the week'
};

const SOURCES = {
  both: 'Wikipedia interest and news coverage',
  wikimedia_pageviews: 'Wikipedia interest',
  gdelt_earned_media: 'news coverage'
};

const MOMENTS = {
  rivalry_win: {label: 'Rivalry wins', singular: 'rivalry win'},
  rivalry_loss: {label: 'Rivalry losses', singular: 'rivalry loss'},
  two_goal_third_period_comeback_win: {label: 'Two-goal third-period comebacks', singular: 'two-goal third-period comeback'},
  overtime_win: {label: 'Overtime wins', singular: 'overtime win'},
  shootout_win: {label: 'Shootout wins', singular: 'shootout win'},
  hat_trick: {label: 'Hat tricks', singular: 'hat trick'},
  four_point_game: {label: 'Four-point nights', singular: 'four-point night'},
  goalie_high_volume_shutout: {label: '40-save shutouts', singular: '40-save shutout'},
  playoff_clinch: {label: 'Playoff clinches', singular: 'playoff clinch'},
  official_roster_event: {label: 'Major roster news', singular: 'major roster announcement'},
  community_or_heritage_event: {label: 'Community and heritage events', singular: 'community or heritage event'}
};

const HISTORICAL_CLUBS = {
  ARI: {
    club_name: 'Arizona Coyotes',
    club_logo_url: 'https://assets.nhle.com/logos/nhl/svg/ARI_light.svg'
  }
};

const fmt = new Intl.NumberFormat('en-US');
const pct = value => value == null ? '—' : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(0)}%`;
const esc = value => String(value ?? '').replace(/[&<>'"]/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[character]));
const momentLabel = value => MOMENTS[value]?.label || String(value || '').replaceAll('_', ' ').replace(/\b\w/g, character => character.toUpperCase());
const momentSingular = value => MOMENTS[value]?.singular || String(value || '').replaceAll('_', ' ');
const youtubeThumbnail = video => video.video_id ? `https://i.ytimg.com/vi/${encodeURIComponent(video.video_id)}/hqdefault.jpg` : '';
const youtubeDisplayTitle = value => String(value || '').replace(/(^|\s)#[\w-]+/g, '$1').replace(/\s+/g, ' ').trim() || 'Untitled video';
const cleanSentence = value => String(value || '')
  .replace(/registered/gi, 'tracked')
  .replace(/taxonomy v1\.1\.0/gi, 'the published moment rules')
  .replace(/source coverage/gi, 'the available public record')
  .replace(/modeled/gi, 'adjusted');

function initialSlug() {
  const pathMatch = location.pathname.match(/\/clubs\/([^/]+)/);
  return pathMatch?.[1] || new URLSearchParams(location.search).get('club') || 'boston-bruins';
}

function routeFor(slug, moment, window, source) {
  const parameters = new URLSearchParams({moment, window, source});
  if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    parameters.set('club', slug);
    return `/explore/?${parameters}`;
  }
  return `/clubs/${slug}?${parameters}`;
}

function assessment(model, club, moment, window) {
  return model.cross_channel_assessments.find(row => row.club_id === club && row.moment_type === moment && row.post_window === window);
}

function estimate(model, club, moment, window, source) {
  return model.estimates.find(row => row.club_id === club && row.moment_type === moment && row.post_window === window && row.attention_channel === source);
}

function evidencePair(state) {
  return {
    wiki: estimate(state.model, state.profile.club_id, state.moment, state.window, 'wikimedia_pageviews'),
    news: estimate(state.model, state.profile.club_id, state.moment, state.window, 'gdelt_earned_media')
  };
}

function minimumCleanSample(pair) {
  const values = [pair.wiki?.isolated_sample_size, pair.news?.isolated_sample_size].filter(value => Number.isFinite(value));
  return values.length ? Math.min(...values) : null;
}

function rangeCrossesNoChange(row) {
  return !row || row.raw_confidence_interval_low == null || row.raw_confidence_interval_high == null || (row.raw_confidence_interval_low <= 0 && row.raw_confidence_interval_high >= 0);
}

function numericRead(pair) {
  if (!pair.wiki || !pair.news) return 'The two parts of the public trail are not both available for this selection.';
  return `Across <strong class="finding-number">${esc(fmt.format(minimumCleanSample(pair) || 0))}</strong> cleaner examples, the typical change was <strong class="finding-number">${esc(pct(pair.wiki.raw_median_lift))}</strong> in Wikipedia interest and <strong class="finding-number">${esc(pct(pair.news.raw_median_lift))}</strong> in the club’s share of monitored news coverage.`;
}

function renderFinding(state) {
  const {profile, moment, window, source, model} = state;
  const comparableCount = profile.moment_type_counts[moment] || 0;
  const pair = evidencePair(state);
  const joint = assessment(model, profile.club_id, moment, window);
  let headline;
  let dek;
  let meaning;
  let limit;
  let status;
  let stateName = 'no-signal';
  let sample;

  document.querySelector('#finding-context').textContent = `${profile.club_name.toUpperCase()} · ${momentLabel(moment).toUpperCase()} · ${WINDOWS[window].toUpperCase()}`;

  if (source === 'both') {
    sample = minimumCleanSample(pair);
    if (joint?.stable && joint.cross_channel_status === 'stable_positive') {
      headline = `${momentLabel(moment)} gave ${profile.club_name} a public aftershock that held up.`;
      dek = numericRead(pair);
      meaning = `People went looking for more information and the club occupied more of the news cycle during the ${WINDOWS[window]}. Those two behaviours moved together often enough to treat the timing as a real content test.`;
      limit = 'This still cannot tell us who paid attention, how they felt, or whether anyone bought, watched, subscribed, or attended because of the moment.';
      status = 'A PATTERN WORTH TESTING';
      stateName = 'confirmed';
    } else if (joint?.stable && joint.cross_channel_status === 'stable_negative') {
      headline = `${momentLabel(moment)} were followed by a repeatable cooling in public attention for ${profile.club_name}.`;
      dek = numericRead(pair);
      meaning = `The two public signals moved down together during the ${WINDOWS[window]}. That is a useful warning against assuming every dramatic hockey moment creates a longer story.`;
      limit = 'A lower public signal does not mean supporters disliked the moment or disengaged from the club. It only describes these two public measures.';
      status = 'A REPEATABLE COOLING';
      stateName = 'confirmed';
    } else if (joint?.cross_channel_status === 'mixed_direction') {
      headline = `${momentLabel(moment)} did not tell one clean public story for ${profile.club_name}.`;
      dek = numericRead(pair);
      meaning = `One part of the public trail moved differently from the other during the ${WINDOWS[window]}. That split matters more than an eye-catching number from either source on its own.`;
      limit = 'The responsible read is mixed. A club could measure the next example, but should not build a repeatable plan around this history.';
      status = 'THE PUBLIC SIGNALS SPLIT';
      stateName = 'caution';
    } else {
      const promising = pair.wiki?.raw_median_lift > 0 && pair.news?.raw_median_lift > 0;
      headline = promising
        ? `${momentLabel(moment)} produced an interesting first glance for ${profile.club_name}. The repeat check says wait.`
        : `The honest read: ${momentLabel(moment).toLowerCase()} did not leave a clear, repeatable public trail for ${profile.club_name}.`;
      dek = numericRead(pair);
      meaning = promising
        ? `Both topline numbers rose, but at least one result varied too much from event to event to call it dependable during the ${WINDOWS[window]}.`
        : `The available examples do not move together consistently enough across Wikipedia and news coverage during the ${WINDOWS[window]}.`;
      limit = 'More clean examples—or a more consistent response in both public signals—would be needed before this becomes an operating pattern.';
      status = promising ? 'PROMISING, NOT SETTLED' : 'NO CLEAR PUBLIC PATTERN';
    }
  } else {
    const row = source === 'wikimedia_pageviews' ? pair.wiki : pair.news;
    sample = row?.isolated_sample_size ?? null;
    const clear = row?.ranking_eligible && !rangeCrossesNoChange(row);
    headline = clear
      ? `${momentLabel(moment)} were followed by a clear ${row.raw_median_lift >= 0 ? 'rise' : 'drop'} in ${SOURCES[source].toLowerCase()} for ${profile.club_name}.`
      : `${SOURCES[source]} alone does not give ${profile.club_name} a settled read on ${momentLabel(moment).toLowerCase()}.`;
    dek = row ? `Across ${fmt.format(sample || 0)} cleaner examples, the typical change was ${pct(row.raw_median_lift)} against the club’s own previous two weeks.` : 'This part of the public record is unavailable for the selected view.';
    meaning = clear ? 'This is a useful clue from one public behaviour.' : 'The response is either too inconsistent or too thin to stand on its own.';
    limit = 'A one-source view is deliberately incomplete. Check the full public trail before treating this as a repeatable pattern.';
    status = clear ? 'ONE CLEAR CLUE' : 'ONE SOURCE, NO SETTLED READ';
    stateName = clear ? 'caution' : 'no-signal';
  }

  document.querySelector('#finding-title').textContent = headline;
  document.querySelector('#finding-dek').innerHTML = dek.includes('finding-number') ? dek : esc(dek);
  document.querySelector('#finding-what').textContent = `The archive contains ${fmt.format(comparableCount)} ${momentLabel(moment).toLowerCase()} for ${profile.club_name}. The chart below shows the cleaner examples that were not crowded by another major club moment in the same week.`;
  document.querySelector('#finding-why').textContent = meaning;
  document.querySelector('#finding-falsify').textContent = limit;
  const stamp = document.querySelector('.evidence-stamp');
  stamp.dataset.state = stateName;
  document.querySelector('#stamp-status').textContent = status;
  document.querySelector('#stamp-sources').textContent = SOURCES[source].toUpperCase();
  document.querySelector('#stamp-sample').textContent = sample == null ? 'COMPARABLE EVENTS: NOT AVAILABLE' : `CLEAN COMPARABLE EVENTS: ${fmt.format(sample)}`;
  document.querySelector('#stamp-window').textContent = `TIMING: ${WINDOWS[window].toUpperCase()}`;
}

function tracePath(points, x, y) {
  const segments = [];
  let active = [];
  points.forEach(point => {
    if (point.median_difference == null) {
      if (active.length) segments.push(active);
      active = [];
    } else active.push(point);
  });
  if (active.length) segments.push(active);
  return segments.map(segment => `M${segment.map(point => `${x(point.day_offset).toFixed(1)},${y(point.median_difference).toFixed(1)}`).join(' L')}`).join(' ');
}

function renderTrace(state) {
  const wanted = state.source === 'both' ? ['wikimedia_pageviews', 'gdelt_earned_media'] : [state.source];
  const series = wanted.map(channel => state.traces.find(row => row.club_id === state.profile.club_id && row.moment_type === state.moment && row.attention_channel === channel)).filter(Boolean);
  const values = series.flatMap(row => row.points.map(point => point.median_difference).filter(value => value != null));
  document.querySelector('#trace-title').textContent = `Did ${momentLabel(state.moment).toLowerCase()} stay in the public conversation?`;
  document.querySelector('#trace-subtitle').textContent = `Each line compares the typical day around a ${momentSingular(state.moment)} with the club’s own average over the previous two weeks. Day 0 is the moment.`;
  const graphic = document.querySelector('#trace-graphic');
  const table = document.querySelector('#trace-table');
  if (!values.length) {
    graphic.innerHTML = '<div class="no-signal"><strong>There is no clean response line for this selection.</strong><p>Another major moment overlapped too often, or part of the public record is missing. The individual events remain available below.</p></div>';
    table.innerHTML = '<p>No chart values are available for this selection.</p>';
    return;
  }

  const width = 820;
  const height = 320;
  // Reserve a quiet right gutter for the series labels so they never sit on top
  // of the plotted lines or compete with the explanatory panel beside the chart.
  const margin = {left: 58, right: 230, top: 34, bottom: 46};
  let minimum = Math.min(0, ...values);
  let maximum = Math.max(0, ...values);
  if (minimum === maximum) { minimum -= 0.1; maximum += 0.1; }
  const padding = (maximum - minimum) * 0.12;
  minimum -= padding;
  maximum += padding;
  const x = value => margin.left + (value + 7) / 14 * (width - margin.left - margin.right);
  const y = value => margin.top + (maximum - value) / (maximum - minimum) * (height - margin.top - margin.bottom);
  const grid = [minimum, 0, maximum];
  let svg = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="trace-svg-title trace-svg-desc"><title id="trace-svg-title">Public response around ${esc(momentLabel(state.moment).toLowerCase())}</title><desc id="trace-svg-desc">Typical change in public attention from seven days before to seven days after the selected moment. Day zero marks the event.</desc>`;
  grid.forEach(value => {
    svg += `<line class="${Math.abs(value) < 1e-9 ? 'chart-zero' : 'chart-rule'}" x1="${margin.left}" x2="${width - margin.right}" y1="${y(value)}" y2="${y(value)}"/><text class="chart-label" x="${margin.left - 9}" y="${y(value) + 4}" text-anchor="end">${pct(value)}</text>`;
  });
  svg += `<line class="chart-event" x1="${x(0)}" x2="${x(0)}" y1="${margin.top}" y2="${height - margin.bottom}"/><text class="chart-label chart-label--event" x="${x(0)}" y="18" text-anchor="middle">THE MOMENT</text>`;
  [-7, -3, 0, 3, 7].forEach(value => {
    svg += `<text class="chart-label" x="${x(value)}" y="${height - 16}" text-anchor="middle">DAY ${value > 0 ? '+' : ''}${value}</text>`;
  });
  const labelRows = series.map(row => {
    const last = [...row.points].reverse().find(point => point.median_difference != null);
    if (!last) return null;
    return {
      row,
      last,
      label: row.attention_channel === 'wikimedia_pageviews' ? 'WIKIPEDIA' : 'NEWS',
      targetY: y(last.median_difference)
    };
  }).filter(Boolean);
  const labelX = width - 12;
  const labelWidth = 220;
  const labelMinY = margin.top + 12;
  const labelMaxY = height - margin.bottom - 12;
  const orderedLabels = [...labelRows].sort((a, b) => a.targetY - b.targetY);
  orderedLabels.forEach((item, index) => {
    item.labelY = Math.max(item.targetY, index ? orderedLabels[index - 1].labelY + 22 : labelMinY);
  });
  const labelOverflow = Math.max(0, orderedLabels.at(-1)?.labelY - labelMaxY || 0);
  if (labelOverflow) orderedLabels.forEach(item => { item.labelY -= labelOverflow; });
  const labelUnderflow = Math.max(0, labelMinY - (orderedLabels[0]?.labelY || labelMinY));
  if (labelUnderflow) orderedLabels.forEach(item => { item.labelY += labelUnderflow; });

  series.forEach(row => {
    const styleClass = row.attention_channel === 'wikimedia_pageviews' ? 'chart-wikimedia' : 'chart-gdelt';
    svg += `<path class="${styleClass}" d="${tracePath(row.points, x, y)}"/>`;
    const labelRow = labelRows.find(item => item.row === row);
    if (labelRow) {
      const boxX = labelX - labelWidth;
      const labelClass = row.attention_channel === 'wikimedia_pageviews' ? 'chart-end--wikimedia' : 'chart-end--gdelt';
      svg += `<rect class="chart-label-bg" x="${boxX}" y="${labelRow.labelY - 11}" width="${labelWidth}" height="22" rx="2"/><text class="chart-end ${labelClass}" x="${labelX - 8}" y="${labelRow.labelY + 4}" text-anchor="end">${labelRow.label} · ${labelRow.last.sample_size} EVENTS</text>`;
    }
  });
  graphic.innerHTML = `${svg}</svg>`;

  const offsets = Array.from({length: 15}, (_, index) => index - 7);
  table.innerHTML = `<table><thead><tr><th>DAY</th>${series.map(row => `<th>${row.attention_channel === 'wikimedia_pageviews' ? 'WIKIPEDIA' : 'NEWS'}</th><th>EVENTS</th>`).join('')}</tr></thead><tbody>${offsets.map(offset => `<tr><td>${offset > 0 ? '+' : ''}${offset}</td>${series.map(row => { const point = row.points.find(item => item.day_offset === offset); return `<td>${pct(point?.median_difference)}</td><td>${point?.sample_size || 0}</td>`; }).join('')}</tr>`).join('')}</tbody></table>`;
}

function inclusionReason(moment) {
  const reasons = {
    rivalry_win: 'The club won a completed game against a pre-published rivalry opponent.',
    rivalry_loss: 'The club lost a completed game against a pre-published rivalry opponent.',
    two_goal_third_period_comeback_win: 'The club trailed by at least two goals entering the third period and won.',
    overtime_win: 'The club won after regulation and before a shootout.',
    shootout_win: 'The club won the game in a shootout.',
    hat_trick: 'One player scored at least three goals in the game.',
    four_point_game: 'One player recorded at least four points in the game.',
    goalie_high_volume_shutout: 'The goaltender recorded a shutout with at least 40 saves.',
    playoff_clinch: 'A dated official NHL or club publication confirmed the clinch.',
    official_roster_event: 'A dated official NHL or club publication announced the roster event.',
    community_or_heritage_event: 'A dated official club or NHL publication announced the event.'
  };
  return reasons[moment] || 'The event met the project’s published rule for this moment.';
}

function renderDocket(state) {
  const gameMap = new Map(state.games.map(row => [row.game_id, row]));
  const individualRows = state.moments.filter(row => row.club_id === state.profile.club_id && row.moment_type === state.moment).sort((a, b) => b.moment_time_utc.localeCompare(a.moment_time_utc));
  const groupedRows = new Map();
  individualRows.forEach(row => {
    const key = row.game_id ? `game-${row.game_id}` : `moment-${row.moment_id}`;
    if (!groupedRows.has(key)) groupedRows.set(key, {...row, moment_ids: [], performance_count: 0});
    groupedRows.get(key).moment_ids.push(row.moment_id);
    groupedRows.get(key).performance_count += 1;
  });
  const rows = [...groupedRows.values()].slice(0, 30);
  document.querySelector('#docket-title').textContent = momentLabel(state.moment);
  const head = '<div class="docket-head"><span>WHEN</span><span>OPPONENT / STORY</span><span>WHAT WE COULD SEE</span><span>TIME CHECKED</span><span>HOW CLEAN?</span><span>RECORD</span></div>';
  const body = rows.map(row => {
    const game = gameMap.get(row.game_id) || {};
    const channels = state.source === 'both' ? ['wikimedia_pageviews', 'gdelt_earned_media'] : [state.source];
    const windows = channels.flatMap(channel => state.eventWindows.filter(item => row.moment_ids.includes(item.moment_id) && item.post_window === state.window && item.attention_channel === channel));
    const states = windows.map(item => item.evidence_status);
    const coverage = !windows.length ? 'Not available' : states.every(value => value === 'eligible') ? 'Clean comparison' : states.includes('excluded_overlapping_major_event') ? 'Another story overlapped' : 'Part of the record is missing';
    const opponentClub = row.opponent_id ? state.clubDirectory.get(row.opponent_id) : null;
    const opponentName = opponentClub?.club_name || (row.opponent_id ? row.opponent_id : momentLabel(row.moment_type));
    const opponent = row.performance_count > 1 ? `${opponentName} · ${row.performance_count} qualifying performances` : opponentName;
    const opponentCell = opponentClub?.club_logo_url
      ? `<span data-label="OPPONENT / STORY" class="docket-opponent"><img src="${esc(opponentClub.club_logo_url)}" alt="" aria-hidden="true"><span>${esc(opponent)}</span></span>`
      : `<span data-label="OPPONENT / STORY">${esc(opponent)}</span>`;
    const sourceUrl = row.source_url || game.source_url || '#';
    return `<details class="docket-row"><summary><span data-label="WHEN">${esc(row.moment_time_utc.slice(0, 10))}</span>${opponentCell}<span data-label="WHAT WE COULD SEE">${esc(SOURCES[state.source])}</span><span data-label="TIME CHECKED">${esc(WINDOWS[state.window])}</span><span data-label="HOW CLEAN?">${esc(coverage)}</span><span data-label="RECORD">OPEN +</span></summary><div class="docket-detail"><p><b>Why this moment is here.</b> ${esc(inclusionReason(row.moment_type))}${row.performance_count > 1 ? ` ${row.performance_count} separate player performances qualified in the same game, so they are grouped here for readability.` : ''} ${coverage === 'Clean comparison' ? 'The surrounding days were clear enough to use in the clean comparison.' : 'The event stays in the public ledger, but is not treated as a clean before-and-after example.'}</p><dl><dt>EVENT RECORD${row.performance_count > 1 ? 'S' : ''}</dt><dd>${esc(row.moment_ids.join(' · '))}</dd><dt>ORIGINAL SOURCE</dt><dd><a href="${esc(sourceUrl)}" target="_blank" rel="noreferrer">Open the public record ↗</a></dd></dl></div></details>`;
  }).join('');
  document.querySelector('#moment-docket').innerHTML = head + (body || '<div class="no-signal"><strong>No qualifying moments are in the record for this selection.</strong><p>The space stays empty rather than being filled with hand-picked examples.</p></div>');
}

function contentFormatLabel(value) {
  const labels = {
    game_highlight_or_recap: 'Game highlights and recaps',
    press_conference_or_media: 'Press conferences and media',
    roster_announcement: 'Roster announcements',
    community_or_heritage: 'Community and heritage stories'
  };
  return labels[value] || value.replaceAll('_', ' ');
}

function renderYouTube(profile, summaries, moment) {
  const row = summaries.find(item => item.club_id === profile.club_id);
  if (!row) return;
  const historical = (row.historical_publication_by_moment || []).find(item => item.moment_type === moment);
  document.querySelector('#youtube-summary').innerHTML = `${esc(profile.club_name)}’s verified channel has <strong class="context-number">${esc(fmt.format(row.video_count))}</strong> accessible videos in this archive, stretching from ${esc(row.oldest_published_at.slice(0, 10))} to ${esc(row.newest_published_at.slice(0, 10))}.`;
  const formats = Object.entries(row.format_counts).sort((a, b) => b[1] - a[1]);
  document.querySelector('#youtube-formats').innerHTML = `<table class="format-ledger"><thead><tr><th>WHAT THE TITLE SUGGESTS</th><th>VIDEOS</th></tr></thead><tbody>${formats.map(([label, count]) => `<tr><td>${esc(contentFormatLabel(label))}</td><td><span class="context-number">${esc(fmt.format(count))}</span></td></tr>`).join('')}</tbody></table>`;
  const historicalBlock = historical
    ? `<div class="publication-evidence"><h3>What the club published after ${esc(momentLabel(moment).toLowerCase())}</h3><p>An upload appeared after <strong class="context-number">${esc(fmt.format(historical.qualifying_moments_with_uploads))}</strong> qualifying moments in the archive.</p><div class="mini-timeline"><div><b class="context-number">${esc(fmt.format(historical.official_uploads_by_window.immediate || 0))}</b><small>OFFICIAL UPLOADS</small><span>FIRST 48 HOURS</span></div><div><b class="context-number">${esc(fmt.format(historical.official_uploads_by_window.short_persistence || 0))}</b><small>OFFICIAL UPLOADS</small><span>NEXT TWO DAYS</span></div><div><b class="context-number">${esc(fmt.format(historical.official_uploads_by_window.sustained_attention || 0))}</b><small>OFFICIAL UPLOADS</small><span>REST OF WEEK</span></div></div><p class="plain-caveat">These are publication times and surviving public-comment timestamps. They are not reconstructed views, likes, or subscriber counts from the date of the event.</p></div>`
    : '<div class="no-signal"><strong>No official-upload timing record is available for this moment.</strong><p>Today’s view totals are not used as a substitute for missing historical performance.</p></div>';
  document.querySelector('#youtube-videos').innerHTML = `${historicalBlock}<h3>Most-viewed public videos as they stand today</h3><table class="video-ledger"><tbody>${row.top_current_public_view_snapshots.slice(0, 5).map(video => { const title = youtubeDisplayTitle(video.title); return `<tr><td><a class="video-thumbnail" href="${esc(video.source_url)}" target="_blank" rel="noreferrer"><img src="${esc(youtubeThumbnail(video))}" alt="Thumbnail for ${esc(title)}" loading="lazy"></a><span class="context-number">${esc(fmt.format(Number(video.view_count || 0)))}</span><br>VIEWS NOW</td><td><a class="video-title" href="${esc(video.source_url)}" target="_blank" rel="noreferrer">${esc(title)}</a><br><span class="quiet-label">Published ${esc(video.published_at.slice(0, 10))}</span></td></tr>`; }).join('')}</tbody></table><p class="plain-caveat">These totals were retrieved on ${esc(row.retrieved_at.slice(0, 10))}.</p>`;
}

function formatMetric(row) {
  if (row.metric_value == null) return 'Not available';
  if (row.unit === 'persons' || row.metric_name === 'population') return fmt.format(Math.round(row.metric_value));
  if (row.metric_name.includes('income')) return `${row.country === 'CA' ? 'CAD' : 'USD'} ${fmt.format(Math.round(row.metric_value))}`;
  if (row.metric_name.includes('pct') || row.unit === 'percent') return `${Number(row.metric_value).toFixed(1)}%`;
  if (row.metric_name.includes('_lq_')) return Number(row.metric_value).toFixed(2);
  return Number(row.metric_value).toLocaleString(undefined, {maximumFractionDigits: 2});
}

function marketMetricLabel(row) {
  const labels = {
    population: 'People in the defined market',
    median_age: 'Median age',
    average_age: 'Average age',
    median_household_income_usd: 'Median household income',
    median_household_income_cad: 'Median household income',
    unemployment_rate_pct: 'Unemployment rate',
    bachelors_or_higher_pct: 'Adults with a bachelor’s degree or higher',
    regional_price_parity_all_items: 'Local price level, U.S. average = 100'
  };
  if (labels[row.metric_name]) return labels[row.metric_name];
  if (row.metric_name.startsWith('preferred_industry_lq_')) {
    const industry = row.metric_name.replace('preferred_industry_lq_', '').replaceAll('_', ' ');
    return `${industry.replace(/\b\w/g, character => character.toUpperCase())} concentration, national average = 1`;
  }
  return row.metric_name.replaceAll('_', ' ');
}

function renderMarket(profile, market) {
  const rows = market.filter(row => row.club_id === profile.club_id && row.evidence_status === 'confirmed');
  const core = ['population', 'median_age', 'average_age', 'median_household_income_usd', 'median_household_income_cad', 'unemployment_rate_pct', 'bachelors_or_higher_pct', 'regional_price_parity_all_items'];
  const selected = core.map(metric => rows.find(row => row.metric_name === metric)).filter(Boolean);
  const concentrations = rows.filter(row => row.metric_name.startsWith('preferred_industry_lq_')).sort((a, b) => b.metric_value - a.metric_value).slice(0, 3);
  document.querySelector('#market-table').innerHTML = `<table class="market-ledger"><thead><tr><th>MARKET MEASURE</th><th>PUBLIC FIGURE</th></tr></thead><tbody>${[...selected, ...concentrations].map(row => { const value = formatMetric(row); const valueMarkup = value === 'Not available' ? esc(value) : `<span class="context-number">${esc(value)}</span>`; return `<tr><td>${esc(marketMetricLabel(row))}<br><span class="quiet-label">${esc(row.reference_period)}${row.fallback_used ? ' · Census estimate used because the employment cell was withheld' : ''}</span></td><td>${valueMarkup}</td></tr>`; }).join('')}</tbody></table>`;
}

function publicMeasure(value) {
  if (String(value).toLowerCase().includes('wikimedia')) return 'Wikipedia interest, checked against the club’s share of monitored news coverage';
  return cleanSentence(value);
}

function renderPlaybooks(profile, playbooks, moment, clubIdentity) {
  const rows = playbooks.filter(row => row.club_id === profile.club_id).sort((a, b) => (a.moment_type === moment ? -1 : 0) - (b.moment_type === moment ? -1 : 0) || a.priority_within_club - b.priority_within_club);
  const logo = document.querySelector('#playbook-logo');
  logo.src = clubIdentity?.club_logo_url || '';
  logo.alt = `${profile.club_name} logo`;
  logo.hidden = !clubIdentity?.club_logo_url;
  document.querySelector('#playbook-intro').innerHTML = `These are three publishing and measurement ideas for <span class="club-name-highlight">${esc(profile.club_name)}</span>.`;
  document.querySelector('#playbook-list').innerHTML = rows.map(row => `<article class="playbook-record"><header class="playbook-record__head"><span>${esc(momentLabel(row.moment_type))}</span></header><div class="action-strip"><div class="action-step"><b>FIRST NIGHT</b><p>${esc(cleanSentence(row.action_0_24h))}</p></div><div class="action-step"><b>NEXT TWO DAYS</b><p>${esc(cleanSentence(row.action_24_72h))}</p></div><div class="action-step"><b>REST OF THE WEEK</b><p>${esc(cleanSentence(row.action_day_4_7))}</p></div></div><footer class="playbook-foot"><div><b>WHAT THE PUBLIC RECORD CAN CHECK</b>${esc(publicMeasure(row.public_kpi))}</div><div><b>WHAT ONLY THE CLUB CAN CHECK</b>${esc(cleanSentence(row.internal_kpi))}</div><div class="validation-flag"><b>PRIVATE INFORMATION NEEDED</b>${esc(cleanSentence(row.internal_data_required))}</div></footer></article>`).join('');
}

function renderLeague(summary) {
  const rows = Object.entries(summary.stable_cells_by_moment).sort((a, b) => b[1] - a[1]);
  document.querySelector('#league-benchmark').innerHTML = rows.map(([moment, count]) => `<tr><td>${esc(momentLabel(moment))}</td><td>${fmt.format(count)}</td></tr>`).join('');
  const sourceLabels = {
    nhl_gamecenter: 'Games and play-by-play',
    moneypuck: 'On-ice context check',
    wikimedia: 'Wikipedia history',
    gdelt: 'News history',
    youtube: 'Official YouTube archive',
    youtube_event_time: 'YouTube publishing times',
    market_context: 'Market background'
  };
  const statusText = value => value.startsWith('confirmed') ? 'In the release' : 'Qualified';
  document.querySelector('#coverage-rail').innerHTML = Object.entries(summary.source_coverage).map(([source, status]) => `<dt>${esc(sourceLabels[source] || source)}</dt><dd class="${status.startsWith('confirmed') ? 'status-confirmed' : 'status-qualified'}">${statusText(status)}</dd>`).join('');
  document.querySelector('#stable-rule').textContent = `Only ${fmt.format(summary.stable_cell_count)} club–moment–timing combinations across the league produced a clear read in both public signals.`;
}

function chooseInitialMoment(state, preferred) {
  const counts = state.profile.moment_type_counts;
  const moments = Object.keys(counts).sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
  const select = document.querySelector('#moment-select');
  select.innerHTML = moments.map(moment => `<option value="${esc(moment)}">${esc(momentLabel(moment))} · ${fmt.format(counts[moment])} in archive</option>`).join('');
  const stable = state.model.cross_channel_assessments.find(row => row.stable && moments.includes(row.moment_type));
  const chosen = preferred && moments.includes(preferred) ? preferred : stable?.moment_type || moments[0];
  select.value = chosen;
  if (!preferred && stable) document.querySelector('#window-select').value = stable.post_window;
  return chosen;
}

async function main([profiles, league]) {
  profiles.sort((a, b) => a.club_name.localeCompare(b.club_name));
  const clubSelect = document.querySelector('#club-select');
  clubSelect.innerHTML = profiles.map(row => `<option value="${esc(row.club_slug)}">${esc(row.club_name)}</option>`).join('');
  clubSelect.value = profiles.some(row => row.club_slug === initialSlug()) ? initialSlug() : 'boston-bruins';
  const initialParameters = new URLSearchParams(location.search);
  if (WINDOWS[initialParameters.get('window')]) document.querySelector('#window-select').value = initialParameters.get('window');
  if (SOURCES[initialParameters.get('source')]) document.querySelector('#source-select').value = initialParameters.get('source');
  let preferredMoment = initialParameters.get('moment');
  const clubDirectory = new Map(profiles.map(row => [row.club_id, row]));
  Object.entries(HISTORICAL_CLUBS).forEach(([clubId, row]) => clubDirectory.set(clubId, row));
  const state = {profiles, league, clubDirectory};
  renderLeague(league);

  async function loadClub(slug) {
    clubSelect.disabled = true;
    const response = await fetch(`${DATA}clubs/${slug}.json`);
    if (!response.ok) throw new Error(`${slug}.json could not be opened`);
    Object.assign(state, await response.json());
    state.eventWindows = state.event_windows;
    clubSelect.disabled = false;
  }

  async function render({clubChanged = false} = {}) {
    if (clubChanged || state.profile?.club_slug !== clubSelect.value) await loadClub(clubSelect.value);
    if (clubChanged || !document.querySelector('#moment-select').value) {
      state.moment = chooseInitialMoment(state, preferredMoment);
      preferredMoment = null;
    } else state.moment = document.querySelector('#moment-select').value;
    state.window = document.querySelector('#window-select').value;
    state.source = document.querySelector('#source-select').value;
    document.documentElement.style.setProperty('--club-accent', state.profile.club_accent);
    const clubIndexRow = state.profiles.find(row => row.club_slug === state.profile.club_slug);
    const logoUrl = clubIndexRow?.club_logo_url || '';
    const logoAlt = `${state.profile.club_name} logo`;
    for (const selector of ['#club-logo', '#club-select-logo']) {
      const logo = document.querySelector(selector);
      logo.src = logoUrl;
      logo.alt = selector === '#club-logo' ? logoAlt : '';
      logo.hidden = !logoUrl;
    }
    document.querySelector('#club-name').textContent = state.profile.club_name;
    document.querySelector('#club-market').textContent = state.profile.market_name;
    document.querySelector('#club-coverage').textContent = `${fmt.format(state.profile.moment_records)} TRACKED MOMENTS · ${fmt.format(state.profile.game_records)} GAMES`;
    document.querySelector('#memo-link').href = state.memo_path;
    document.title = `${state.profile.club_name} findings · Moment-to-Market Lab`;
    renderFinding(state);
    renderTrace(state);
    renderDocket(state);
    renderYouTube(state.profile, state.youtube, state.moment);
    renderMarket(state.profile, state.market);
    renderPlaybooks(state.profile, state.playbooks, state.moment, state.clubDirectory.get(state.profile.club_id));
    history.replaceState({}, '', routeFor(state.profile.club_slug, state.moment, state.window, state.source));
  }

  clubSelect.addEventListener('change', () => render({clubChanged: true}).catch(showFailure));
  document.querySelector('#moment-select').addEventListener('change', () => render().catch(showFailure));
  document.querySelector('#window-select').addEventListener('change', () => render().catch(showFailure));
  document.querySelector('#source-select').addEventListener('change', () => render().catch(showFailure));
  addEventListener('popstate', () => {
    const slug = initialSlug();
    const parameters = new URLSearchParams(location.search);
    if (profiles.some(row => row.club_slug === slug)) {
      clubSelect.value = slug;
      if (WINDOWS[parameters.get('window')]) document.querySelector('#window-select').value = parameters.get('window');
      if (SOURCES[parameters.get('source')]) document.querySelector('#source-select').value = parameters.get('source');
      preferredMoment = parameters.get('moment');
      render({clubChanged: true}).catch(showFailure);
    }
  });
  await render({clubChanged: true});
}

function showFailure(error) {
  document.querySelector('#finding-title').textContent = 'The public record could not be opened.';
  document.querySelector('#finding-dek').textContent = 'This page stops rather than showing an old or invented result.';
  document.querySelector('#finding-what').textContent = 'A required release file is missing or failed its check.';
  document.querySelector('#finding-why').textContent = 'The evidence must be rebuilt before this club can be shown.';
  document.querySelector('#finding-falsify').textContent = 'Complete the published release checks, then reload the page.';
  document.querySelector('#trace-graphic').innerHTML = `<div class="no-signal"><strong>Validated public data required.</strong><p>${esc(error.message)}</p></div>`;
}

Promise.all(['club_index.json', 'league_summary.json'].map(file => fetch(DATA + file).then(response => {
  if (!response.ok) throw new Error(`${file} could not be opened`);
  return response.json();
}))).then(main).catch(showFailure);
