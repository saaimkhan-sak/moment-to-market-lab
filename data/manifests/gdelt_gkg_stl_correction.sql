-- Correct St. Louis Blues extraction after the dynamic regex escaped the period incorrectly.
-- Returns the complete daily series and one deterministic matched URL per positive day.
SELECT
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS article_date,
  COUNT(DISTINCT DocumentIdentifier) AS daily_gkg_web_article_count,
  COUNT(DISTINCT IF(
    REGEXP_CONTAINS(AllNames, r'(^|;)Louis Blues,[0-9]+($|;)'),
    DocumentIdentifier,
    NULL
  )) AS article_count,
  ARRAY_AGG(
    DISTINCT IF(
      REGEXP_CONTAINS(AllNames, r'(^|;)Louis Blues,[0-9]+($|;)'),
      DocumentIdentifier,
      NULL
    ) IGNORE NULLS
    LIMIT 1
  )[SAFE_OFFSET(0)] AS audit_candidate_url
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2023-10-01') AND TIMESTAMP('2026-07-31 23:59:59')
  AND SourceCollectionIdentifier = 1
GROUP BY article_date
ORDER BY article_date;
