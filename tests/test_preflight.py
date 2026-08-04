import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PreflightTests(unittest.TestCase):
 def test_preflight_records_status_without_secret(self):
  record=json.loads((ROOT/'data/evidence/preflight.json').read_text())
  self.assertTrue(record['youtube']['key_present']); self.assertEqual(record['bea']['status'],'confirmed')
  self.assertNotIn('key', json.dumps(record).lower().replace('key_present',''))
