"""Validate and archive one browser-fetched GDELT DOC timeline response."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

from common import ROOT, now_utc


def main(interval_id: str, source_url: str) -> str:
    body_text = sys.stdin.read()
    payload = json.loads(body_text)
    if not payload.get("timeline") or not payload["timeline"][0].get("data"):
        raise ValueError("GDELT browser response lacks timeline data")
    plan = json.loads((ROOT / "data/manifests/gdelt_timeline_plan.json").read_text())
    planned = {
        interval["interval_id"]: (mapping, interval)
        for mapping in plan["mappings"]
        for interval in mapping["intervals"]
    }
    if interval_id not in planned:
        raise ValueError(f"Unplanned interval: {interval_id}")
    mapping, interval = planned[interval_id]
    if source_url != interval["source_url"]:
        raise ValueError("Source URL does not match the registered plan")
    record = {
        "interval_id": interval_id,
        "mapping_id": mapping["mapping_id"],
        "club_id": mapping["club_id"],
        "source_url": source_url,
        "http_status": 200,
        "retrieved_at": now_utc(),
        "body_checksum": hashlib.sha256(body_text.encode()).hexdigest(),
        "body_text": body_text,
        "acquisition_transport": "browser_fetch_same_official_doc_endpoint_after_scripted_http_429",
    }
    target = ROOT / "data/raw/gdelt/timeline_direct" / f"{interval_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return str(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("interval_id")
    parser.add_argument("source_url")
    args = parser.parse_args()
    print(main(args.interval_id, args.source_url))
