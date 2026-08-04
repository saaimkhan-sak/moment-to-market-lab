"""Credential and source preflight. Never prints secret values."""
from __future__ import annotations
import json, os
from urllib.parse import urlencode
from common import ROOT, fetch_json, load_env, now_utc, write_json

def run() -> str:
    load_env()
    results={"checked_at":now_utc(),"youtube":{"key_present":bool(os.getenv("YOUTUBE_API_KEY")),"status":"confirmed_from_pilot" if (ROOT/"data/evidence/youtube-nyrangers.json").exists() else "not_checked"},"bea":{"key_present":bool(os.getenv("BEA_API_KEY")),"status":"unavailable"}}
    key=os.getenv("BEA_API_KEY")
    if key:
        try:
            payload, provenance=fetch_json("https://apps.bea.gov/api/data/?"+urlencode({"UserID":key,"method":"GETDATASETLIST","ResultFormat":"JSON"}))
            results["bea"]={"key_present":True,"status":"confirmed" if payload.get("BEAAPI",{}).get("Results") else "unavailable","source_url":"https://apps.bea.gov/api/data/","retrieved_at":provenance["retrieved_at"]}
        except Exception as exc:
            results["bea"]={"key_present":True,"status":"unavailable","reason":type(exc).__name__}
    return str(write_json("data/evidence/preflight.json",results))
if __name__ == "__main__": print(run())
