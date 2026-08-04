"""Generate a single-scan daily GDELT GKG exact-name volume query."""
from __future__ import annotations

import csv
from datetime import date
import re

from common import ROOT
from analysis_window import ANALYSIS_START, ANALYSIS_END

START = date.fromisoformat(ANALYSIS_START)
END = date.fromisoformat(ANALYSIS_END)


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "\\'") + "'"


def raw_sql_string(value: str) -> str:
    return "r'" + value.replace("'", "\\'") + "'"


def field_name(mapping_id: str) -> str:
    return "m_" + re.sub(r"[^a-z0-9]+", "_", mapping_id.lower()).strip("_")


def all_names_pattern(label: str) -> str:
    # AllNames is a semicolon-delimited list of "name,character_offset" pairs.
    if label == "St. Louis Blues":
        # Audited GKG rows omit the "St." token and store "Louis Blues".
        return r"(^|;)louis\s+blues,[0-9]+($|;)"
    escaped = re.escape(label.lower()).replace(r"\ ", r"\s+")
    return rf"(^|;){escaped},[0-9]+($|;)"


URL_SUBJECT_RECOVERY = {
    "BOS-current": r"(^|[^a-z])(boston[-_/]+bruins|bruins)([^a-z]|$)",
    "CHI-current": r"(^|[^a-z])(chicago[-_/]+blackhawks|blackhawks)([^a-z]|$)",
    "NSH-current": r"(^|[^a-z])(nashville[-_/]+predators|predators)([^a-z]|$)",
    "WPG-current": r"(^|[^a-z])(winnipeg[-_/]+jets|jets)([^a-z]|$)",
}


def build() -> str:
    mappings = []
    with (ROOT / "config/entity_dictionary.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "confirmed":
                continue
            valid_from = max(date.fromisoformat(row.get("valid_from") or START.isoformat()), START)
            valid_to = min(date.fromisoformat(row.get("valid_to") or END.isoformat()), END)
            if valid_from > valid_to:
                continue
            mappings.append({
                "mapping_id": row["mapping_id"],
                "mapping_column": field_name(row["mapping_id"]),
                "club_id": row["club_id"],
                "entity_id": row["entity_id"],
                "entity_label": row["entity_label"],
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
                "pattern": all_names_pattern(row["entity_label"]),
            })

    structs = []
    measures = []
    unpivot_fields = []
    for item in mappings:
        structs.append(
            "    STRUCT(" + ", ".join([
                f"{sql_string(item['mapping_id'])} AS mapping_id",
                f"{sql_string(item['mapping_column'])} AS mapping_column",
                f"{sql_string(item['club_id'])} AS club_id",
                f"{sql_string(item['entity_id'])} AS entity_id",
                f"{sql_string(item['entity_label'])} AS entity_label",
                f"DATE {sql_string(item['valid_from'])} AS valid_from",
                f"DATE {sql_string(item['valid_to'])} AS valid_to",
            ]) + ")"
        )
        conditions = [
            f"date_utc BETWEEN DATE {sql_string(item['valid_from'])} AND DATE {sql_string(item['valid_to'])}",
            f"REGEXP_CONTAINS(all_names, {raw_sql_string(item['pattern'])})",
        ]
        if item["mapping_id"] in URL_SUBJECT_RECOVERY:
            conditions.append(
                f"REGEXP_CONTAINS(url_lower, {raw_sql_string(URL_SUBJECT_RECOVERY[item['mapping_id']])})"
            )
        measures.append(
            "    COUNT(DISTINCT IF("
            + " AND ".join(conditions)
            + f", url, NULL)) AS {item['mapping_column']}"
        )
        unpivot_fields.append(item["mapping_column"])

    query = f"""-- GDELT GKG 2.1 exact-name daily article observations.
-- Generated from validity-aware config/entity_dictionary.csv.
-- AllNames is GDELT's extracted named-entity field, not full article text.
-- SourceCollectionIdentifier=1 restricts the denominator to web-source records.
-- Dry-run and cap maximum bytes billed before execution.
WITH mappings AS (
  SELECT * FROM UNNEST([
{',\n'.join(structs)}
  ])
),
articles AS (
  SELECT
    PARSE_DATE('%Y%m%d', SUBSTR(CAST(DATE AS STRING), 1, 8)) AS date_utc,
    DocumentIdentifier AS url,
    LOWER(AllNames) AS all_names,
    LOWER(DocumentIdentifier) AS url_lower
  FROM `gdelt-bq.gdeltv2.gkg_partitioned`
  WHERE _PARTITIONTIME >= TIMESTAMP('{START.isoformat()}')
    AND _PARTITIONTIME < TIMESTAMP('{END.isoformat()}') + INTERVAL 1 DAY
    AND DATE BETWEEN {START.strftime('%Y%m%d')}000000 AND {END.strftime('%Y%m%d')}235959
    AND SourceCollectionIdentifier = 1
),
daily_wide AS (
  SELECT
    date_utc,
    COUNT(DISTINCT url) AS daily_gkg_web_article_count,
{',\n'.join(measures)}
  FROM articles
  GROUP BY date_utc
),
daily_long AS (
  SELECT date_utc, daily_gkg_web_article_count, mapping_column, article_count
  FROM daily_wide
  UNPIVOT(article_count FOR mapping_column IN ({', '.join(unpivot_fields)}))
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
"""
    target = ROOT / "data/manifests/gdelt_gkg_daily_volume.sql"
    target.write_text(query)
    return str(target)


if __name__ == "__main__":
    print(build())
