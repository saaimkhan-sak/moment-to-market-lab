"""Remove locally configured API keys from generated provenance artifacts."""
from pathlib import Path
import sys
import re

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from common import load_env
import os

def main():
    load_env(); secrets=[os.getenv("YOUTUBE_API_KEY"),os.getenv("BEA_API_KEY")]
    secrets=[secret for secret in secrets if secret]
    changed=[]
    for base in (ROOT/"data",ROOT/"app",ROOT/"config",ROOT/"outputs"):
        if not base.exists(): continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json",".csv",".yml",".yaml",".md",".txt"}: continue
            try: text=path.read_text()
            except UnicodeDecodeError: continue
            clean=text
            for secret in secrets: clean=clean.replace(secret,"[REDACTED]")
            clean=re.sub(r"AIza[0-9A-Za-z_-]{30,50}","[REDACTED]",clean)
            clean=re.sub(r"AIza[0-9A-Za-z_-]{3,29}","[REDACTED]",clean)
            clean=clean.replace("AIza...","[REDACTED]")
            if clean!=text:
                path.write_text(clean);changed.append(str(path.relative_to(ROOT)))
    print(f"Sanitized {len(changed)} generated files; .env was not modified.")

if __name__=="__main__": main()
