import unittest
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from detect_moments import boxscore_player_moments, goalie_moment, comeback_moment, official_announcement_moment
class Taxonomy(unittest.TestCase):
 def test_all_registered_moments_exist(self):
  text=(ROOT/'config/moment_taxonomy.yml').read_text()
  for moment in ['rivalry_win','rivalry_loss','two_goal_third_period_comeback_win','overtime_win','shootout_win','hat_trick','four_point_game','goalie_high_volume_shutout','playoff_clinch','official_roster_event','community_or_heritage_event']: self.assertIn(moment+':',text)
 def test_version_and_overlap_policy_exist(self): self.assertIn('version: 1.1.0',(ROOT/'config/moment_taxonomy.yml').read_text()); self.assertIn('overlap_policy:',(ROOT/'config/moment_taxonomy.yml').read_text())
 def test_objective_player_goalie_and_comeback_rules(self):
  self.assertEqual(boxscore_player_moments({'goals':3,'points':4}),['hat_trick','four_point_game']); self.assertEqual(goalie_moment({'shutout':True,'saves':40}),['goalie_high_volume_shutout']); self.assertTrue(comeback_moment(2,True)); self.assertFalse(comeback_moment(None,True))
 def test_official_announcement_fails_closed(self):
  self.assertIsNone(official_announcement_moment({'moment_type':'playoff_clinch','evidence_status':'confirmed'})); self.assertEqual(official_announcement_moment({'moment_type':'playoff_clinch','evidence_status':'confirmed','source_url':'https://nhl.com/x','announcement_time_utc':'2026-01-01T00:00:00Z'}),'playoff_clinch')
 def test_official_announcement_classes_are_materialized(self):
  import json
  rows=json.loads((ROOT/'data/curated/official_announcement.json').read_text())
  clubs={row['club_id'] for row in rows if row['moment_type']=='official_roster_event'}
  self.assertEqual(len(clubs),32)
  self.assertEqual({row['moment_type'] for row in rows},{'playoff_clinch','official_roster_event','community_or_heritage_event'})
  self.assertTrue(all(row['evidence_status']=='confirmed' and row['source_url'].startswith('https://www.youtube.com/watch?v=') for row in rows))
  self.assertTrue(all(row['timestamp_semantics']=='official_publication_time_not_inferred_transaction_time' for row in rows))
