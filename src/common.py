"""Shared provenance and validation utilities; standard library only."""
from __future__ import annotations
import hashlib, json, os, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def load_env() -> None:
    """Load local key=value pairs without a third-party dotenv dependency."""
    path = ROOT / ".env"
    if not path.exists(): return
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"): continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def fetch_json(url: str, attempts: int = 4, timeout: int = 30) -> tuple[dict, dict]:
    request = Request(url, headers={"User-Agent": "nhl-moment-to-market-lab/0.1 (public research)"})
    error = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response: body = response.read()
            break
        except (HTTPError, URLError) as exc:
            error = exc
            if isinstance(exc, HTTPError) and exc.code not in {429, 500, 502, 503, 504}: raise
            time.sleep(min(2 ** attempt, 8))
    else: raise error
    return json.loads(body), {"source_url": url, "retrieved_at": now_utc(), "checksum": digest(body), "schema_hash": digest(json.dumps(sorted(json.loads(body).keys())).encode())}

def fetch_bytes(url: str, attempts: int = 4, headers: dict | None = None) -> tuple[bytes, dict]:
    request = Request(url, headers={"User-Agent":"nhl-moment-to-market-lab/0.1 (public research)", **(headers or {})})
    error=None
    for attempt in range(attempts):
        try:
            with urlopen(request,timeout=60) as response: body=response.read()
            return body,{"source_url":url,"retrieved_at":now_utc(),"checksum":digest(body),"content_length":len(body)}
        except (HTTPError,URLError) as exc:
            error=exc
            if isinstance(exc,HTTPError) and exc.code not in {429,500,502,503,504}: raise
            time.sleep(min(2**attempt,8))
    raise error

def archive_json(source: str, name: str, payload: dict, provenance: dict) -> Path:
    target = ROOT / "data" / "raw" / source
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{name}.json"
    path.write_text(json.dumps({"provenance": provenance, "payload": payload}, indent=2, sort_keys=True))
    return path

def write_json(relative: str, value: dict | list) -> Path:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True))
    return path

def evidence_record(source_id: str, status: str, reason: str | None = None, **fields) -> dict:
    if status not in {"confirmed", "unknown", "unavailable", "blocked", "missing", "planned"}:
        raise ValueError(f"Invalid evidence state: {status}")
    return {"source_id": source_id, "evidence_status": status, "retrieved_at": now_utc(), "reason": reason, **fields}
