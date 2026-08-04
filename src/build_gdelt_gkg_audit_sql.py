"""Build the validity-aware GDELT GKG article sample used for precision review."""
from __future__ import annotations

import csv
from pathlib import Path
import re

from common import ROOT
from analysis_window import ANALYSIS_START, ANALYSIS_END

START = ANALYSIS_START
END = ANALYSIS_END


def sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def main() -> None:
    identities = []
    with (ROOT / "config/entity_dictionary.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "confirmed":
                continue
            identities.append(
                "STRUCT('{mapping_id}' AS mapping_id, '{club_id}' AS club_id, "
                "'{entity_id}' AS entity_id, '{label}' AS entity_label, "
                "r'{pattern}' AS entity_pattern, "
                "DATE '{valid_from}' AS valid_from, DATE '{valid_to}' AS valid_to)".format(
                    mapping_id=sql_string(row["mapping_id"]),
                    club_id=sql_string(row["club_id"]),
                    entity_id=sql_string(row["entity_id"]),
                    label=sql_string(row["entity_label"]),
                    pattern=(r"Louis Blues" if row["mapping_id"] == "STL-current" else re.escape(row["entity_label"])),
                    valid_from=max(row.get("valid_from") or START, START),
                    valid_to=min(row.get("valid_to") or END, END),
                )
            )

    identity_sql = ",\n    ".join(identities)
    query = f"""-- GDELT GKG precision-audit sample; generated from config/entity_dictionary.csv.
-- Five deterministic article URLs per validity-aware entity mapping (34 mappings / 170 rows).
WITH identities AS (
  SELECT * FROM UNNEST([
    {identity_sql}
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
  WHERE _PARTITIONTIME BETWEEN TIMESTAMP('{START}') AND TIMESTAMP('{END} 23:59:59')
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
"""
    output = ROOT / "data/manifests/gdelt_gkg_precision_audit.sql"
    output.write_text(query)
    print(output)


if __name__ == "__main__":
    main()
