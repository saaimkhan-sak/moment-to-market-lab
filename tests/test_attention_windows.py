import unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fit_attention_model import cross_channel_assessments, eligible_for_ranking, overlaps
def lift(post,baseline): return (post-baseline)/max(baseline,1)
class AttentionWindows(unittest.TestCase):
 def test_formula_guards_zero_baseline(self): self.assertEqual(lift(3,0),3)
 def test_registered_windows_present(self):
  text=(ROOT/'METHODOLOGY.md').read_text(); self.assertIn('Days 0–1',text);self.assertIn('Days 2–3',text);self.assertIn('Days 4–7',text)
 def test_small_samples_and_unavailable_cells_are_suppressed(self): self.assertFalse(eligible_for_ranking(9,'confirmed')); self.assertFalse(eligible_for_ranking(10,'unavailable')); self.assertTrue(eligible_for_ranking(10,'confirmed'))
 def test_cross_channel_stability_requires_club_local_raw_agreement(self):
  rows=[]
  for channel,raw in [('wikimedia_pageviews',.2),('gdelt_earned_media',-.1)]:
   rows.append({'club_id':'CAR','moment_type':'overtime_win','post_window':'immediate','attention_channel':channel,'ranking_eligible':True,'estimate':.15,'confidence_interval_low':.05,'confidence_interval_high':.25,'raw_median_lift':raw,'raw_confidence_interval_low':raw-.02,'raw_confidence_interval_high':raw+.02})
  result=cross_channel_assessments(rows)[0]
  self.assertEqual(result['cross_channel_status'],'mixed_direction')
  self.assertFalse(result['stable'])
