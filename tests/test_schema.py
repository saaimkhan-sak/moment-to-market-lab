import csv,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
class SchemaTests(unittest.TestCase):
 def test_registry_has_exactly_32_current_clubs(self):
  with (ROOT/'CLUB_REGISTRY.csv').open() as handle: rows=list(csv.DictReader(handle))
  self.assertEqual(len(rows),32); self.assertEqual(len({r['club_id'] for r in rows}),32); self.assertIn('Utah Mammoth',[r['club_name'] for r in rows])
 def test_required_canonical_tables_are_documented(self):
  text=(ROOT/'DATA_DICTIONARY.md').read_text();
  for name in ['game','game_event','moment','official_announcement','entity_mapping','attention_daily','gdelt_attention_daily','gdelt_article_observation','content_video','market_context','club_moment_estimate','activation_playbook','evidence_coverage','release_manifest']: self.assertIn(f'`{name}`',text)
 def test_nhl_archives_have_provenance(self):
  for path in (ROOT/'data/raw/nhl').glob('*.json'):
   r=json.loads(path.read_text()); self.assertIn('source_url',r['provenance']); self.assertIn('retrieved_at',r['provenance'])
 def test_canonical_game_event_keys_pass_build_audit(self):
  audit=json.loads((ROOT/'data/manifests/canonical_key_audit.json').read_text())
  self.assertEqual(audit['evidence_status'],'confirmed')
  self.assertEqual(audit['event_count'],audit['unique_event_key_count'])
  self.assertEqual(audit['duplicate_event_key_count'],0)
  self.assertEqual(audit['missing_event_key_count'],0)
  self.assertEqual(audit['orphan_game_id_count'],0)
 def test_moment_and_attention_keys_are_unique(self):
  moments=json.loads((ROOT/'data/curated/moment.json').read_text())
  wikimedia=json.loads((ROOT/'data/curated/attention_daily.json').read_text())
  gdelt=json.loads((ROOT/'data/curated/gdelt_attention_daily.json').read_text())
  self.assertEqual(len(moments),len({row['moment_id'] for row in moments}))
  self.assertEqual(len(wikimedia),len({(row['club_id'],row['entity_id'],row['date_utc'],row['channel'],row['metric_name']) for row in wikimedia}))
  self.assertEqual(len(gdelt),len({(row['club_id'],row['mapping_id'],row['date_utc'],row['channel'],row['metric_name']) for row in gdelt}))
