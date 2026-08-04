import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SeasonSourceCoverageTests(unittest.TestCase):
    def test_expansion_clubs_enter_without_backcasting(self):
        rows = json.loads((ROOT / "data/curated/evidence_coverage.json").read_text())
        seasons = {club: {row["season"] for row in rows if row["club_id"] == club} for club in ("VGK", "SEA", "UTA")}
        self.assertEqual(min(seasons["VGK"]), "20172018")
        self.assertEqual(min(seasons["SEA"]), "20212022")
        self.assertEqual(min(seasons["UTA"]), "20242025")

    def test_coverage_states_do_not_turn_missingness_into_zero(self):
        rows = json.loads((ROOT / "data/curated/evidence_coverage.json").read_text())
        self.assertTrue(rows)
        self.assertTrue(all(row["evidence_status"] in {"confirmed", "confirmed_with_visible_source_gaps"} for row in rows))
        self.assertTrue(all(row["youtube_role"].startswith("descriptive_") for row in rows))
        self.assertTrue(all(row["gdelt_observed_days"] <= row["gdelt_expected_days"] for row in rows))


if __name__ == "__main__":
    unittest.main()
