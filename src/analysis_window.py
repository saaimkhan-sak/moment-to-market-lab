"""Versioned historical-window and club-season eligibility helpers."""
from __future__ import annotations

import json

from common import ROOT


WINDOW = json.loads((ROOT / "config/analysis_window.json").read_text())
SEASONS = tuple(WINDOW["seasons"])
ANALYSIS_START = WINDOW["analysis_start"]
ANALYSIS_END = WINDOW["analysis_end"]


def club_active_in_season(club_id: str, season: str) -> bool:
    rule = WINDOW.get("club_season_validity", {}).get(club_id, {})
    first = rule.get("first", WINDOW["default_club_first_season"])
    last = rule.get("last", WINDOW["last_season"])
    return first <= season <= last


def season_label(season: str) -> str:
    return f"{season[:4]}-{season[6:]}"
