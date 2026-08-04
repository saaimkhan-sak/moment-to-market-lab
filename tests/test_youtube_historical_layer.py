import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class YouTubeHistoricalLayerTests(unittest.TestCase):
    def test_contract_forbids_backcasting_current_statistics(self):
        text = (ROOT / "config/source_contracts.yml").read_text()
        self.assertIn("never_assign_retrieval_time_views_likes_comments_or_subscribers_to_past_events", text)
        self.assertIn("prospective_daily_trajectory_collection: deferred_by_user", text)

    def test_publication_panel_contains_no_retrieval_time_engagement_metrics(self):
        path = ROOT / "data/curated/youtube_event_publication.json"
        if not path.exists():
            self.skipTest("publication panel is built after the historical moment backfill")
        rows = json.loads(path.read_text())
        forbidden = {"view_count", "like_count", "comment_count", "subscriber_count"}
        self.assertTrue(rows)
        self.assertTrue(all(not (forbidden & set(row)) for row in rows))
        self.assertTrue(all(row["post_window"] in {"immediate", "short_persistence", "sustained"} for row in rows))

    def test_comment_targets_are_selected_without_engagement(self):
        path = ROOT / "data/manifests/youtube_historical_comment_targets.json"
        if not path.exists():
            self.skipTest("comment targets are built after the historical moment backfill")
        manifest = json.loads(path.read_text())
        self.assertTrue(manifest["selection_inputs_exclude_current_engagement"])
        self.assertTrue(all("view_count" not in row and "like_count" not in row and "comment_count" not in row for row in manifest["targets"]))


if __name__ == "__main__":
    unittest.main()
