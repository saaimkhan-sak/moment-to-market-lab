-- Diagnose GDELT AllNames tokenization for St. Louis Blues references in a bounded month.
SELECT
  DATE(PARSE_TIMESTAMP('%Y%m%d%H%M%S', CAST(DATE AS STRING))) AS article_date,
  DocumentIdentifier AS article_url,
  AllNames AS matched_all_names,
  V2Themes AS matched_themes
FROM `gdelt-bq.gdeltv2.gkg_partitioned`
WHERE _PARTITIONTIME BETWEEN TIMESTAMP('2026-01-01') AND TIMESTAMP('2026-01-31 23:59:59')
  AND SourceCollectionIdentifier = 1
  AND REGEXP_CONTAINS(LOWER(AllNames), r'louis')
  AND REGEXP_CONTAINS(LOWER(AllNames), r'blues')
LIMIT 50;
