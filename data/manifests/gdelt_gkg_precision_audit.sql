-- GDELT GKG precision-audit sample; generated from config/entity_dictionary.csv.
-- Five deterministic article URLs per validity-aware entity mapping (34 mappings / 170 rows).
WITH identities AS (
  SELECT * FROM UNNEST([
    STRUCT('ANA-current' AS mapping_id, 'ANA' AS club_id, 'Q192751' AS entity_id, 'Anaheim Ducks' AS entity_label, r'Anaheim\ Ducks' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('ARI-2023-24' AS mapping_id, 'ARI' AS club_id, 'Q206312' AS entity_id, 'Arizona Coyotes' AS entity_label, r'Arizona\ Coyotes' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2024-06-30' AS valid_to),
    STRUCT('BOS-current' AS mapping_id, 'BOS' AS club_id, 'Q194121' AS entity_id, 'Boston Bruins' AS entity_label, r'Boston\ Bruins' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('BUF-current' AS mapping_id, 'BUF' AS club_id, 'Q131206' AS entity_id, 'Buffalo Sabres' AS entity_label, r'Buffalo\ Sabres' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CAR-current' AS mapping_id, 'CAR' AS club_id, 'Q201857' AS entity_id, 'Carolina Hurricanes' AS entity_label, r'Carolina\ Hurricanes' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CBJ-current' AS mapping_id, 'CBJ' AS club_id, 'Q207507' AS entity_id, 'Columbus Blue Jackets' AS entity_label, r'Columbus\ Blue\ Jackets' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CGY-current' AS mapping_id, 'CGY' AS club_id, 'Q194126' AS entity_id, 'Calgary Flames' AS entity_label, r'Calgary\ Flames' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CHI-current' AS mapping_id, 'CHI' AS club_id, 'Q209636' AS entity_id, 'Chicago Blackhawks' AS entity_label, r'Chicago\ Blackhawks' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('COL-current' AS mapping_id, 'COL' AS club_id, 'Q206297' AS entity_id, 'Colorado Avalanche' AS entity_label, r'Colorado\ Avalanche' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('DAL-current' AS mapping_id, 'DAL' AS club_id, 'Q208652' AS entity_id, 'Dallas Stars' AS entity_label, r'Dallas\ Stars' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('DET-current' AS mapping_id, 'DET' AS club_id, 'Q194116' AS entity_id, 'Detroit Red Wings' AS entity_label, r'Detroit\ Red\ Wings' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('EDM-current' AS mapping_id, 'EDM' AS club_id, 'Q205973' AS entity_id, 'Edmonton Oilers' AS entity_label, r'Edmonton\ Oilers' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('FLA-current' AS mapping_id, 'FLA' AS club_id, 'Q204623' AS entity_id, 'Florida Panthers' AS entity_label, r'Florida\ Panthers' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('LAK-current' AS mapping_id, 'LAK' AS club_id, 'Q203008' AS entity_id, 'Los Angeles Kings' AS entity_label, r'Los\ Angeles\ Kings' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('MIN-current' AS mapping_id, 'MIN' AS club_id, 'Q206357' AS entity_id, 'Minnesota Wild' AS entity_label, r'Minnesota\ Wild' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('MTL-current' AS mapping_id, 'MTL' AS club_id, 'Q188143' AS entity_id, 'Montreal Canadiens' AS entity_label, r'Montreal\ Canadiens' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NJD-current' AS mapping_id, 'NJD' AS club_id, 'Q192081' AS entity_id, 'New Jersey Devils' AS entity_label, r'New\ Jersey\ Devils' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NSH-current' AS mapping_id, 'NSH' AS club_id, 'Q207980' AS entity_id, 'Nashville Predators' AS entity_label, r'Nashville\ Predators' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NYI-current' AS mapping_id, 'NYI' AS club_id, 'Q194369' AS entity_id, 'New York Islanders' AS entity_label, r'New\ York\ Islanders' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NYR-current' AS mapping_id, 'NYR' AS club_id, 'Q188984' AS entity_id, 'New York Rangers' AS entity_label, r'New\ York\ Rangers' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('OTT-current' AS mapping_id, 'OTT' AS club_id, 'Q203013' AS entity_id, 'Ottawa Senators' AS entity_label, r'Ottawa\ Senators' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('PHI-current' AS mapping_id, 'PHI' AS club_id, 'Q192083' AS entity_id, 'Philadelphia Flyers' AS entity_label, r'Philadelphia\ Flyers' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('PIT-current' AS mapping_id, 'PIT' AS club_id, 'Q193643' AS entity_id, 'Pittsburgh Penguins' AS entity_label, r'Pittsburgh\ Penguins' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('SEA-current' AS mapping_id, 'SEA' AS club_id, 'Q59422166' AS entity_id, 'Seattle Kraken' AS entity_label, r'Seattle\ Kraken' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('SJS-current' AS mapping_id, 'SJS' AS club_id, 'Q206381' AS entity_id, 'San Jose Sharks' AS entity_label, r'San\ Jose\ Sharks' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('STL-current' AS mapping_id, 'STL' AS club_id, 'Q207735' AS entity_id, 'St. Louis Blues' AS entity_label, r'Louis Blues' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('TBL-current' AS mapping_id, 'TBL' AS club_id, 'Q201864' AS entity_id, 'Tampa Bay Lightning' AS entity_label, r'Tampa\ Bay\ Lightning' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('TOR-current' AS mapping_id, 'TOR' AS club_id, 'Q203384' AS entity_id, 'Toronto Maple Leafs' AS entity_label, r'Toronto\ Maple\ Leafs' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('UTA-hockey-club' AS mapping_id, 'UTA' AS club_id, 'Q125520712' AS entity_id, 'Utah Hockey Club' AS entity_label, r'Utah\ Hockey\ Club' AS entity_pattern, DATE '2024-06-13' AS valid_from, DATE '2025-05-06' AS valid_to),
    STRUCT('UTA-mammoth' AS mapping_id, 'UTA' AS club_id, 'Q125520712' AS entity_id, 'Utah Mammoth' AS entity_label, r'Utah\ Mammoth' AS entity_pattern, DATE '2025-05-07' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('VAN-current' AS mapping_id, 'VAN' AS club_id, 'Q192890' AS entity_id, 'Vancouver Canucks' AS entity_label, r'Vancouver\ Canucks' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('VGK-current' AS mapping_id, 'VGK' AS club_id, 'Q24725640' AS entity_id, 'Vegas Golden Knights' AS entity_label, r'Vegas\ Golden\ Knights' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('WPG-current' AS mapping_id, 'WPG' AS club_id, 'Q472741' AS entity_id, 'Winnipeg Jets' AS entity_label, r'Winnipeg\ Jets' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('WSH-current' AS mapping_id, 'WSH' AS club_id, 'Q204627' AS entity_id, 'Washington Capitals' AS entity_label, r'Washington\ Capitals' AS entity_pattern, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to)
  ])
),
candidates AS (
  SELECT
    i.mapping_id,
    i.club_id,
    i.entity_id,
    i.entity_label,
    DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(g.DATE AS STRING))) AS article_date,
    g.DocumentIdentifier AS article_url,
    g.SourceCommonName AS source_common_name,
    g.V2Locations AS source_locations,
    g.AllNames AS matched_all_names,
    ROW_NUMBER() OVER (
      PARTITION BY i.mapping_id
      ORDER BY FARM_FINGERPRINT(CONCAT(i.mapping_id, '|', g.DocumentIdentifier))
    ) AS sample_rank
  FROM `gdelt-bq.gdeltv2.gkg_partitioned` AS g
  CROSS JOIN identities AS i
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2023-10-01') AND TIMESTAMP('2026-07-31 23:59:59')
    AND g.SourceCollectionIdentifier = 1
    AND DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(g.DATE AS STRING))) BETWEEN i.valid_from AND i.valid_to
    AND REGEXP_CONTAINS(
      g.AllNames,
      CONCAT(r'(^|;)', i.entity_pattern, r',[0-9]+($|;)')
    )
    AND g.DocumentIdentifier IS NOT NULL
)
SELECT
  mapping_id, club_id, entity_id, entity_label, article_date, article_url,
  source_common_name, source_locations, matched_all_names, sample_rank
FROM candidates
WHERE sample_rank <= 5
ORDER BY club_id, mapping_id, sample_rank;
