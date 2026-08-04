-- GDELT GKG 2.1 exact-name daily article observations.
-- Generated from validity-aware config/entity_dictionary.csv.
-- AllNames is GDELT's extracted named-entity field, not full article text.
-- SourceCollectionIdentifier=1 restricts the denominator to web-source records.
-- Dry-run and cap maximum bytes billed before execution.
WITH mappings AS (
  SELECT * FROM UNNEST([
    STRUCT('ANA-current' AS mapping_id, 'm_ana_current' AS mapping_column, 'ANA' AS club_id, 'Q192751' AS entity_id, 'Anaheim Ducks' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('ARI-2015-2024' AS mapping_id, 'm_ari_2015_2024' AS mapping_column, 'ARI' AS club_id, 'Q206312' AS entity_id, 'Arizona Coyotes' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2024-06-30' AS valid_to),
    STRUCT('BOS-current' AS mapping_id, 'm_bos_current' AS mapping_column, 'BOS' AS club_id, 'Q194121' AS entity_id, 'Boston Bruins' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('BUF-current' AS mapping_id, 'm_buf_current' AS mapping_column, 'BUF' AS club_id, 'Q131206' AS entity_id, 'Buffalo Sabres' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CAR-current' AS mapping_id, 'm_car_current' AS mapping_column, 'CAR' AS club_id, 'Q201857' AS entity_id, 'Carolina Hurricanes' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CBJ-current' AS mapping_id, 'm_cbj_current' AS mapping_column, 'CBJ' AS club_id, 'Q207507' AS entity_id, 'Columbus Blue Jackets' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CGY-current' AS mapping_id, 'm_cgy_current' AS mapping_column, 'CGY' AS club_id, 'Q194126' AS entity_id, 'Calgary Flames' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CHI-current' AS mapping_id, 'm_chi_current' AS mapping_column, 'CHI' AS club_id, 'Q209636' AS entity_id, 'Chicago Blackhawks' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('COL-current' AS mapping_id, 'm_col_current' AS mapping_column, 'COL' AS club_id, 'Q206297' AS entity_id, 'Colorado Avalanche' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('DAL-current' AS mapping_id, 'm_dal_current' AS mapping_column, 'DAL' AS club_id, 'Q208652' AS entity_id, 'Dallas Stars' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('DET-current' AS mapping_id, 'm_det_current' AS mapping_column, 'DET' AS club_id, 'Q194116' AS entity_id, 'Detroit Red Wings' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('EDM-current' AS mapping_id, 'm_edm_current' AS mapping_column, 'EDM' AS club_id, 'Q205973' AS entity_id, 'Edmonton Oilers' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('FLA-current' AS mapping_id, 'm_fla_current' AS mapping_column, 'FLA' AS club_id, 'Q204623' AS entity_id, 'Florida Panthers' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('LAK-current' AS mapping_id, 'm_lak_current' AS mapping_column, 'LAK' AS club_id, 'Q203008' AS entity_id, 'Los Angeles Kings' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('MIN-current' AS mapping_id, 'm_min_current' AS mapping_column, 'MIN' AS club_id, 'Q206357' AS entity_id, 'Minnesota Wild' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('MTL-current' AS mapping_id, 'm_mtl_current' AS mapping_column, 'MTL' AS club_id, 'Q188143' AS entity_id, 'Montreal Canadiens' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NJD-current' AS mapping_id, 'm_njd_current' AS mapping_column, 'NJD' AS club_id, 'Q192081' AS entity_id, 'New Jersey Devils' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NSH-current' AS mapping_id, 'm_nsh_current' AS mapping_column, 'NSH' AS club_id, 'Q207980' AS entity_id, 'Nashville Predators' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NYI-current' AS mapping_id, 'm_nyi_current' AS mapping_column, 'NYI' AS club_id, 'Q194369' AS entity_id, 'New York Islanders' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NYR-current' AS mapping_id, 'm_nyr_current' AS mapping_column, 'NYR' AS club_id, 'Q188984' AS entity_id, 'New York Rangers' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('OTT-current' AS mapping_id, 'm_ott_current' AS mapping_column, 'OTT' AS club_id, 'Q203013' AS entity_id, 'Ottawa Senators' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('PHI-current' AS mapping_id, 'm_phi_current' AS mapping_column, 'PHI' AS club_id, 'Q192083' AS entity_id, 'Philadelphia Flyers' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('PIT-current' AS mapping_id, 'm_pit_current' AS mapping_column, 'PIT' AS club_id, 'Q193643' AS entity_id, 'Pittsburgh Penguins' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('SEA-current' AS mapping_id, 'm_sea_current' AS mapping_column, 'SEA' AS club_id, 'Q59422166' AS entity_id, 'Seattle Kraken' AS entity_label, DATE '2021-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('SJS-current' AS mapping_id, 'm_sjs_current' AS mapping_column, 'SJS' AS club_id, 'Q206381' AS entity_id, 'San Jose Sharks' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('STL-current' AS mapping_id, 'm_stl_current' AS mapping_column, 'STL' AS club_id, 'Q207735' AS entity_id, 'St. Louis Blues' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('TBL-current' AS mapping_id, 'm_tbl_current' AS mapping_column, 'TBL' AS club_id, 'Q201864' AS entity_id, 'Tampa Bay Lightning' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('TOR-current' AS mapping_id, 'm_tor_current' AS mapping_column, 'TOR' AS club_id, 'Q203384' AS entity_id, 'Toronto Maple Leafs' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('UTA-hockey-club' AS mapping_id, 'm_uta_hockey_club' AS mapping_column, 'UTA' AS club_id, 'Q125520712' AS entity_id, 'Utah Hockey Club' AS entity_label, DATE '2024-06-13' AS valid_from, DATE '2025-05-06' AS valid_to),
    STRUCT('UTA-mammoth' AS mapping_id, 'm_uta_mammoth' AS mapping_column, 'UTA' AS club_id, 'Q125520712' AS entity_id, 'Utah Mammoth' AS entity_label, DATE '2025-05-07' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('VAN-current' AS mapping_id, 'm_van_current' AS mapping_column, 'VAN' AS club_id, 'Q192890' AS entity_id, 'Vancouver Canucks' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('VGK-current' AS mapping_id, 'm_vgk_current' AS mapping_column, 'VGK' AS club_id, 'Q24725640' AS entity_id, 'Vegas Golden Knights' AS entity_label, DATE '2017-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('WPG-current' AS mapping_id, 'm_wpg_current' AS mapping_column, 'WPG' AS club_id, 'Q472741' AS entity_id, 'Winnipeg Jets' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('WSH-current' AS mapping_id, 'm_wsh_current' AS mapping_column, 'WSH' AS club_id, 'Q204627' AS entity_id, 'Washington Capitals' AS entity_label, DATE '2015-07-01' AS valid_from, DATE '2026-07-31' AS valid_to)
  ])
),
articles AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS date_utc,
    DocumentIdentifier AS url,
    LOWER(AllNames) AS all_names,
    LOWER(DocumentIdentifier) AS url_lower
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP('2015-07-01')
    AND _PARTITIONTIME < TIMESTAMP('2026-07-31') + INTERVAL 1 DAY
    AND DATE BETWEEN 20150701000000 AND 20260731235959
    AND SourceCollectionIdentifier = 1
),
daily_wide AS (
  SELECT
    date_utc,
    COUNT(DISTINCT url) AS daily_gkg_web_article_count,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)anaheim\s+ducks,[0-9]+($|;)'), url, NULL)) AS m_ana_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2024-06-30' AND REGEXP_CONTAINS(all_names, r'(^|;)arizona\s+coyotes,[0-9]+($|;)'), url, NULL)) AS m_ari_2015_2024,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)boston\s+bruins,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(boston[-_/]+bruins|bruins)([^a-z]|$)'), url, NULL)) AS m_bos_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)buffalo\s+sabres,[0-9]+($|;)'), url, NULL)) AS m_buf_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)carolina\s+hurricanes,[0-9]+($|;)'), url, NULL)) AS m_car_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)columbus\s+blue\s+jackets,[0-9]+($|;)'), url, NULL)) AS m_cbj_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)calgary\s+flames,[0-9]+($|;)'), url, NULL)) AS m_cgy_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)chicago\s+blackhawks,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(chicago[-_/]+blackhawks|blackhawks)([^a-z]|$)'), url, NULL)) AS m_chi_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)colorado\s+avalanche,[0-9]+($|;)'), url, NULL)) AS m_col_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)dallas\s+stars,[0-9]+($|;)'), url, NULL)) AS m_dal_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)detroit\s+red\s+wings,[0-9]+($|;)'), url, NULL)) AS m_det_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)edmonton\s+oilers,[0-9]+($|;)'), url, NULL)) AS m_edm_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)florida\s+panthers,[0-9]+($|;)'), url, NULL)) AS m_fla_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)los\s+angeles\s+kings,[0-9]+($|;)'), url, NULL)) AS m_lak_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)minnesota\s+wild,[0-9]+($|;)'), url, NULL)) AS m_min_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)montreal\s+canadiens,[0-9]+($|;)'), url, NULL)) AS m_mtl_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)new\s+jersey\s+devils,[0-9]+($|;)'), url, NULL)) AS m_njd_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)nashville\s+predators,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(nashville[-_/]+predators|predators)([^a-z]|$)'), url, NULL)) AS m_nsh_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)new\s+york\s+islanders,[0-9]+($|;)'), url, NULL)) AS m_nyi_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)new\s+york\s+rangers,[0-9]+($|;)'), url, NULL)) AS m_nyr_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)ottawa\s+senators,[0-9]+($|;)'), url, NULL)) AS m_ott_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)philadelphia\s+flyers,[0-9]+($|;)'), url, NULL)) AS m_phi_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)pittsburgh\s+penguins,[0-9]+($|;)'), url, NULL)) AS m_pit_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2021-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)seattle\s+kraken,[0-9]+($|;)'), url, NULL)) AS m_sea_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)san\s+jose\s+sharks,[0-9]+($|;)'), url, NULL)) AS m_sjs_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)louis\s+blues,[0-9]+($|;)'), url, NULL)) AS m_stl_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)tampa\s+bay\s+lightning,[0-9]+($|;)'), url, NULL)) AS m_tbl_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)toronto\s+maple\s+leafs,[0-9]+($|;)'), url, NULL)) AS m_tor_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2024-06-13' AND DATE '2025-05-06' AND REGEXP_CONTAINS(all_names, r'(^|;)utah\s+hockey\s+club,[0-9]+($|;)'), url, NULL)) AS m_uta_hockey_club,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2025-05-07' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)utah\s+mammoth,[0-9]+($|;)'), url, NULL)) AS m_uta_mammoth,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)vancouver\s+canucks,[0-9]+($|;)'), url, NULL)) AS m_van_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2017-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)vegas\s+golden\s+knights,[0-9]+($|;)'), url, NULL)) AS m_vgk_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)winnipeg\s+jets,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(winnipeg[-_/]+jets|jets)([^a-z]|$)'), url, NULL)) AS m_wpg_current,
    COUNT(DISTINCT IF(date_utc BETWEEN DATE '2015-07-01' AND DATE '2026-07-31' AND REGEXP_CONTAINS(all_names, r'(^|;)washington\s+capitals,[0-9]+($|;)'), url, NULL)) AS m_wsh_current
  FROM articles
  GROUP BY date_utc
),
daily_long AS (
  SELECT date_utc, daily_gkg_web_article_count, mapping_column, article_count
  FROM daily_wide
  UNPIVOT(article_count FOR mapping_column IN (m_ana_current, m_ari_2015_2024, m_bos_current, m_buf_current, m_car_current, m_cbj_current, m_cgy_current, m_chi_current, m_col_current, m_dal_current, m_det_current, m_edm_current, m_fla_current, m_lak_current, m_min_current, m_mtl_current, m_njd_current, m_nsh_current, m_nyi_current, m_nyr_current, m_ott_current, m_phi_current, m_pit_current, m_sea_current, m_sjs_current, m_stl_current, m_tbl_current, m_tor_current, m_uta_hockey_club, m_uta_mammoth, m_van_current, m_vgk_current, m_wpg_current, m_wsh_current))
),
date_spine AS (
  SELECT mapping.mapping_id, mapping.mapping_column, mapping.club_id,
         mapping.entity_id, mapping.entity_label,
         day AS date_utc
  FROM mappings AS mapping,
       UNNEST(GENERATE_DATE_ARRAY(mapping.valid_from, mapping.valid_to)) AS day
)
SELECT
  spine.mapping_id,
  spine.club_id,
  spine.entity_id,
  spine.entity_label,
  spine.date_utc,
  COALESCE(volume.article_count, 0) AS article_count,
  volume.daily_gkg_web_article_count
FROM date_spine AS spine
LEFT JOIN daily_long AS volume
  USING (mapping_column, date_utc)
ORDER BY club_id, mapping_id, date_utc;
