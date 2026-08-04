import json,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from reconcile_nhl_moneypuck import build_audit, club_id
class ReconciliationTests(unittest.TestCase):
 def test_raw_moneypuck_manifests_have_checksums_and_variables(self):
  manifests=list((ROOT/'data/raw/moneypuck').glob('*.manifest.json')); self.assertGreaterEqual(len(manifests),4)
  for path in manifests:
   record=json.loads(path.read_text()); self.assertEqual(len(record['checksum']),64); self.assertTrue(record['variables_used'])
 def test_audit_preserves_mismatches(self):
  build_audit(); data=json.loads((ROOT/'data/curated/nhl_moneypuck_reconciliation.json').read_text()); self.assertEqual(data['status'],'confirmed'); self.assertGreater(data['sample_size'],14000); self.assertGreaterEqual(data['match_rate'],data['minimum_match_rate']); self.assertEqual(data['missing_moneypuck_games'],0); self.assertEqual(data['team_mismatches'],0); self.assertTrue(all(row['status'] in {'matched','mismatch'} for row in data['rows']))
 def test_historical_moneypuck_team_aliases_normalize_to_nhl_ids(self):
  self.assertEqual(club_id('L.A'),'LAK'); self.assertEqual(club_id('N.J'),'NJD'); self.assertEqual(club_id('S.J'),'SJS'); self.assertEqual(club_id('T.B'),'TBL')
 def test_game_context_has_xg_and_score_state_variables(self):
  rows=json.loads((ROOT/'data/curated/moneypuck_game_context.json').read_text());self.assertGreater(len(rows),14000)
  required={'home_xg_all','away_xg_all','home_xg_5on5','away_xg_5on5','home_xg_while_leading','away_xg_while_trailing','home_xg_share_all'}
  self.assertTrue(all(required.issubset(row) and all(row[field] is not None for field in required) for row in rows))
