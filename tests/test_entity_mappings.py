import csv,json,unittest,sys
from datetime import date,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_entity_mapping import validate
class EntityTests(unittest.TestCase):
 def test_auditable_entity_mappings(self): self.assertTrue(validate())
 def test_franchise_era_page_mappings_are_explicit(self):
  with (ROOT/'config/entity_dictionary.csv').open() as handle: rows=list(csv.DictReader(handle))
  self.assertTrue(any(r['club_id']=='WPG' and r['entity_id']=='Q472741' and r['wikipedia_article']=='Winnipeg Jets' for r in rows))
  self.assertFalse(any(r['club_id']=='WPG' and '1972' in r['wikipedia_article'] for r in rows))
  self.assertTrue(any(r['club_id']=='ARI' and r['entity_id']=='Q206312' and r['valid_to']=='2024-06-30' for r in rows))
  self.assertEqual({r['wikipedia_article'] for r in rows if r['club_id']=='UTA'},{'Utah Hockey Club','Utah Mammoth'})
  for row in [r for r in rows if r['club_id'] in {'ARI','WPG'}]:
   archive=json.loads(Path(row['entity_archive']).read_text())
   self.assertIn(row['entity_id'],archive['payload']['entities'])
  self.assertEqual([(r['valid_from'],r['valid_to']) for r in rows if r['club_id']=='UTA'],[('2024-06-13','2025-05-06'),('2025-05-07','')])
 def test_arizona_and_utah_identity_periods_are_separate(self):
  with (ROOT/'config/franchise_history.csv').open() as handle: rows=list(csv.DictReader(handle))
  by_id={row['identity_id']:row for row in rows}
  self.assertEqual(set(by_id),{'ARI-coyotes','UTA-hockey-club','UTA-mammoth'})
  self.assertNotEqual(by_id['ARI-coyotes']['franchise_id'],by_id['UTA-hockey-club']['franchise_id'])
  self.assertEqual(by_id['UTA-hockey-club']['successor_identity_id'],'UTA-mammoth')
  self.assertEqual(date.fromisoformat(by_id['UTA-hockey-club']['valid_to'])+timedelta(days=1),date.fromisoformat(by_id['UTA-mammoth']['valid_from']))
