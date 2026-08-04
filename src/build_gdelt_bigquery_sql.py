"""Generate the single-scan, validity-aware GDELT WebNGrams query."""
from __future__ import annotations

import csv
from datetime import date
import re

from common import ROOT
from analysis_window import ANALYSIS_START, ANALYSIS_END

START = date.fromisoformat(ANALYSIS_START)
END = date.fromisoformat(ANALYSIS_END)


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def raw_sql_string(value: str) -> str:
    return "r'" + value.replace("'", "\\'") + "'"


def phrase_pattern(label: str) -> str:
    escaped = re.escape(label.lower()).replace(r"\ ", r"\s+")
    return rf"(^|[^a-z0-9]){escaped}([^a-z0-9]|$)"


def anchor(label: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", label.lower())
    return tokens[len(tokens) // 2] if len(tokens) >= 3 else tokens[0]


def anchor_variants(value: str) -> set[str]:
    cases = {value.lower(), value.title(), value.upper()}
    prefixes = ['"', "'", "“", "‘", "(", "["]
    suffixes = [".", ",", ":", ";", "!", "?", '"', "'", "”", "’", ")", "]"]
    variants = set(cases)
    for token in cases:
        variants.update(prefix + token for prefix in prefixes)
        variants.update(token + suffix for suffix in suffixes)
        variants.update({f'"{token}"', f"'{token}'", f"“{token}”", f"‘{token}’", f"({token})", f"[{token}]"})
    return variants


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
            label = row["entity_label"]
            mappings.append({
                "mapping_id": row["mapping_id"],
                "club_id": row["club_id"],
                "entity_id": row["entity_id"],
                "entity_label": label,
                "valid_from": valid_from.isoformat(),
                "valid_to": valid_to.isoformat(),
                "anchor": anchor(label),
                "pattern": phrase_pattern(label),
            })

    structs = []
    for item in mappings:
        structs.append(
            "    STRUCT("
            + ", ".join([
                f"{sql_string(item['mapping_id'])} AS mapping_id",
                f"{sql_string(item['club_id'])} AS club_id",
                f"{sql_string(item['entity_id'])} AS entity_id",
                f"{sql_string(item['entity_label'])} AS entity_label",
                f"DATE {sql_string(item['valid_from'])} AS valid_from",
                f"DATE {sql_string(item['valid_to'])} AS valid_to",
                f"{sql_string(item['anchor'])} AS anchor_token",
                f"{raw_sql_string(item['pattern'])} AS phrase_pattern",
            ])
            + ")"
        )
    anchors = ", ".join(sql_string(value) for value in sorted({variant for item in mappings for variant in anchor_variants(item["anchor"])}))
    cases = "\n".join(
        "      WHEN date_utc BETWEEN DATE " + sql_string(item["valid_from"])
        + " AND DATE " + sql_string(item["valid_to"])
        + " AND REGEXP_CONTAINS(mention_context, " + raw_sql_string(item["pattern"])
        + ") THEN " + sql_string(item["mapping_id"])
        for item in mappings
    )
    query = f"""-- GDELT Web News NGrams 3.0; generated from config/entity_dictionary.csv.
-- One partition-bounded table scan. Duplicate URLs are removed before daily counts.
-- Dry-run and set maximum bytes billed to 1099511627776 (1 TiB) before execution.
WITH mappings AS (
  SELECT * FROM UNNEST([
{',\n'.join(structs)}
  ])
),
candidate_ngrams AS (
  SELECT
    DATE(date) AS date_utc,
    LOWER(CONCAT(pre, ' ', ngram, ' ', post)) AS mention_context,
    url
  FROM `gdelt-bq.gdeltv2.webngrams`
  WHERE date >= TIMESTAMP('{START.isoformat()}')
    AND date < TIMESTAMP('{END.isoformat()}') + INTERVAL 1 DAY
    AND lang = 'en'
    AND type = 1
    AND ngram IN ({anchors})
),
tagged_mentions AS (
  SELECT
    CASE
{cases}
      ELSE NULL
    END AS mapping_id,
    date_utc,
    url
  FROM candidate_ngrams
),
matched_urls AS (
  SELECT mapping_id, date_utc, url
  FROM tagged_mentions
  WHERE mapping_id IS NOT NULL
  GROUP BY mapping_id, date_utc, url
),
daily_counts AS (
  SELECT mapping_id, date_utc, COUNT(DISTINCT url) AS article_count
  FROM matched_urls
  GROUP BY mapping_id, date_utc
),
date_spine AS (
  SELECT mapping.mapping_id, mapping.club_id, mapping.entity_id,
         mapping.entity_label, day AS date_utc
  FROM mappings AS mapping,
       UNNEST(GENERATE_DATE_ARRAY(mapping.valid_from, mapping.valid_to)) AS day
)
SELECT
  spine.mapping_id,
  spine.club_id,
  spine.entity_id,
  spine.entity_label,
  spine.date_utc,
  COALESCE(counts.article_count, 0) AS article_count
FROM date_spine AS spine
LEFT JOIN daily_counts AS counts
  USING (mapping_id, date_utc)
ORDER BY club_id, mapping_id, date_utc;
"""
    target = ROOT / "data/manifests/gdelt_webngrams_daily_volume.sql"
    target.write_text(query)
    return str(target)


if __name__ == "__main__":
    print(build())
