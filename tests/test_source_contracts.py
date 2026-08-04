import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Contracts(unittest.TestCase):
 def test_core_sources_and_missing_policy_are_explicit(self):
  text=(ROOT/'config/source_contracts.yml').read_text()
  for source in ['nhl-public','moneypuck','wikimedia','gdelt','youtube','market']: self.assertIn(source+':',text)
  self.assertIn('preserve_missing_never_zero',text); self.assertIn('club_precision_gte_0_90',text)
 def test_youtube_key_is_example_only(self):
  text=(ROOT/'.env.example').read_text(); self.assertIn('YOUTUBE_API_KEY=\n',text); self.assertIn('BEA_API_KEY=\n',text); self.assertNotIn('AIza',text)
 def test_no_unverified_channel_handle_is_usable(self):
  import csv
  with (ROOT/'config/official_channel_registry.csv').open() as handle: rows=list(csv.DictReader(handle))
  self.assertTrue(rows); self.assertTrue(all(r['evidence_status']=='confirmed' and r['official_channel_id'] for r in rows))
