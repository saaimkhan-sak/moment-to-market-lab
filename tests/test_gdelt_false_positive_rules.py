import csv,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class GdeltTests(unittest.TestCase):
 def test_full_names_and_exclusions_are_registered(self):
  text=(ROOT/'config/gdelt_query_rules.yml').read_text()
  self.assertIn('exact_full_name',text); self.assertIn('Texas Rangers',text); self.assertIn('hurricane weather',text)
  with (ROOT/'config/clubs.csv').open() as handle:
   clubs={row['club_id'] for row in csv.DictReader(handle)}
  club_section=text.split('clubs:',1)[1].split('historical_identities:',1)[0]
  registered=set(re.findall(r'^  ([A-Z]{3}):$',club_section,re.MULTILINE))
  self.assertEqual(clubs,registered)
  self.assertIn('historical_identities:',text)
  self.assertIn('"Arizona Coyotes"',text)
  with (ROOT/'config/entity_dictionary.csv').open() as handle:
   mappings=[row for row in csv.DictReader(handle) if row['status']=='confirmed']
  self.assertTrue(all(f'"{row["entity_label"]}"' in text for row in mappings))
