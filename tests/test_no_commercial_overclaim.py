import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CommercialClaims(unittest.TestCase):
 def test_charter_denies_unsupported_commercial_outputs(self):
  text=(ROOT/'PROJECT_CHARTER.md').read_text().lower()
  for term in ['ticket revenue','sponsor value','renewal likelihood','purchase intent']: self.assertIn(term,text)
 def test_app_has_no_banned_growth_claims(self):
  text=(ROOT/'app/index.html').read_text().lower()
  for term in ['unlock','supercharge','ai-powered','revenue forecast']: self.assertNotIn(term,text)
 def test_story_home_explains_the_reasoning_and_registered_math(self):
  text=(ROOT/'app/index.html').read_text().lower()
  for term in ['the genesis','public-attention difference','prior 14 days','log(attention + 1)','overlap rule','ensuring signal agreement before labeling']:
   self.assertIn(term,text)
 def test_club_explorer_uses_plain_public_language(self):
  text=(ROOT/'app/explore/index.html').read_text().lower()
  for term in ['what we saw','what it suggests','what this cannot tell us','what happened after the moment?']:
   self.assertIn(term,text)
  self.assertIn('what only the club can check',(ROOT/'app/app.js').read_text().lower())
  for term in ['hierarchical','confidence interval','taxonomy','algorithm']:
   self.assertNotIn(term,text)
 def test_playbooks_require_internal_validation_and_deny_public_commercial_inference(self):
  rows=json.loads((ROOT/'data/curated/activation_playbook.json').read_text())
  if len(rows)==96:
   self.assertTrue(all(row['requires_internal_validation'] is True for row in rows))
   self.assertTrue(all('public attention is not' in row['guardrails'].lower() for row in rows))
   text=json.dumps(rows).lower()
   for claim in ['will increase revenue','will increase attendance','will improve conversion','guaranteed sponsor value']:
    self.assertNotIn(claim,text)
