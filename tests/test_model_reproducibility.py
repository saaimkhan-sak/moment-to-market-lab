import hashlib,json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Reproducibility(unittest.TestCase):
 def test_profile_build_is_deterministic(self):
  model=json.loads((ROOT/'data/curated/club_moment_estimate.json').read_text())
  command=[sys.executable,'src/build_club_profiles.py']
  if model.get('status')!='confirmed':
   blocked=subprocess.run(command,cwd=ROOT,check=False,capture_output=True,text=True)
   self.assertNotEqual(blocked.returncode,0)
   self.assertIn('confirmed two-channel model',blocked.stderr)
   return
  subprocess.run(command,cwd=ROOT,check=True,capture_output=True)
  path=ROOT/'data/curated/club_profiles.json'
  first=hashlib.sha256(path.read_bytes()).hexdigest()
  subprocess.run(command,cwd=ROOT,check=True,capture_output=True)
  self.assertEqual(first,hashlib.sha256(path.read_bytes()).hexdigest())
