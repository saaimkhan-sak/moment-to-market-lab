-- Precision-recovery extraction for the four GKG clubs below 90%.
-- Requires an exact AllNames entity and a club-bearing article URL.
-- The URL rule prioritizes precision over recall and requires a new audit.
-- Dry-run first. Execute only with maximum bytes billed <= 150,000,000,000.
CREATE TEMP TABLE matched AS
WITH articles AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS date_utc,
    DocumentIdentifier AS article_url,
    LOWER(DocumentIdentifier) AS url_lower,
    LOWER(AllNames) AS all_names
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP('2023-10-01')
    AND _PARTITIONTIME < TIMESTAMP('2026-08-01')
    AND DATE BETWEEN 20231001000000 AND 20260731235959
    AND SourceCollectionIdentifier = 1
    AND DocumentIdentifier IS NOT NULL
)
SELECT DISTINCT
  CASE
    WHEN REGEXP_CONTAINS(all_names, r'(^|;)boston\s+bruins,[0-9]+($|;)')
      AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(boston[-_/]+bruins|bruins)([^a-z]|$)') THEN 'BOS-current'
    WHEN REGEXP_CONTAINS(all_names, r'(^|;)chicago\s+blackhawks,[0-9]+($|;)')
      AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(chicago[-_/]+blackhawks|blackhawks)([^a-z]|$)') THEN 'CHI-current'
    WHEN REGEXP_CONTAINS(all_names, r'(^|;)nashville\s+predators,[0-9]+($|;)')
      AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(nashville[-_/]+predators|predators)([^a-z]|$)') THEN 'NSH-current'
    WHEN REGEXP_CONTAINS(all_names, r'(^|;)winnipeg\s+jets,[0-9]+($|;)')
      AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(winnipeg[-_/]+jets|jets)([^a-z]|$)') THEN 'WPG-current'
  END AS mapping_id,
  date_utc,
  article_url
FROM articles
WHERE
  (REGEXP_CONTAINS(all_names, r'(^|;)boston\s+bruins,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(boston[-_/]+bruins|bruins)([^a-z]|$)'))
  OR (REGEXP_CONTAINS(all_names, r'(^|;)chicago\s+blackhawks,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(chicago[-_/]+blackhawks|blackhawks)([^a-z]|$)'))
  OR (REGEXP_CONTAINS(all_names, r'(^|;)nashville\s+predators,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(nashville[-_/]+predators|predators)([^a-z]|$)'))
  OR (REGEXP_CONTAINS(all_names, r'(^|;)winnipeg\s+jets,[0-9]+($|;)') AND REGEXP_CONTAINS(url_lower, r'(^|[^a-z])(winnipeg[-_/]+jets|jets)([^a-z]|$)'));

WITH identities AS (
  SELECT * FROM UNNEST([
    STRUCT('BOS-current' AS mapping_id, 'BOS' AS club_id, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('CHI-current' AS mapping_id, 'CHI' AS club_id, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('NSH-current' AS mapping_id, 'NSH' AS club_id, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to),
    STRUCT('WPG-current' AS mapping_id, 'WPG' AS club_id, DATE '2023-10-01' AS valid_from, DATE '2026-07-31' AS valid_to)
  ])
),
daily_counts AS (
  SELECT mapping_id, date_utc, COUNT(DISTINCT article_url) AS article_count
  FROM matched
  WHERE mapping_id IS NOT NULL
  GROUP BY mapping_id, date_utc
),
date_spine AS (
  SELECT identity.mapping_id, identity.club_id, day AS date_utc
  FROM identities AS identity,
       UNNEST(GENERATE_DATE_ARRAY(identity.valid_from, identity.valid_to)) AS day
),
audit_sample AS (
  SELECT
    mapping_id,
    article_url,
    ROW_NUMBER() OVER (
      PARTITION BY mapping_id
      ORDER BY FARM_FINGERPRINT(CONCAT(mapping_id, '|', article_url))
    ) AS sample_rank
  FROM (SELECT DISTINCT mapping_id, article_url FROM matched WHERE mapping_id IS NOT NULL)
),
daily_rows AS (
  SELECT
    'daily' AS row_type,
    spine.mapping_id,
    spine.club_id,
    spine.date_utc,
    COALESCE(counts.article_count, 0) AS article_count,
    CAST(NULL AS STRING) AS article_url,
    CAST(NULL AS INT64) AS sample_rank
  FROM date_spine AS spine
  LEFT JOIN daily_counts AS counts USING (mapping_id, date_utc)
),
sample_rows AS (
  SELECT
    'audit_sample' AS row_type,
    sample.mapping_id,
    SPLIT(sample.mapping_id, '-')[OFFSET(0)] AS club_id,
    CAST(NULL AS DATE) AS date_utc,
    CAST(NULL AS INT64) AS article_count,
    sample.article_url,
    sample.sample_rank
  FROM audit_sample AS sample
  WHERE sample.sample_rank <= 10
)
SELECT * FROM daily_rows
UNION ALL
SELECT * FROM sample_rows
ORDER BY mapping_id, row_type, date_utc, sample_rank;
