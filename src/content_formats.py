"""Shared, transparent title-format coding for official club YouTube videos."""
from __future__ import annotations

from collections import Counter
import re


FORMAT_RULES = {
    "press_conference_or_media": re.compile(r"press conference|media availability|speaks to the media", re.I),
    "game_highlight_or_recap": re.compile(r"highlights?|game recap|postgame", re.I),
    "short_form": re.compile(r"#shorts?\b", re.I),
    "community_or_heritage": re.compile(r"community|heritage|pride|hockey fights cancer|black history|indigenous", re.I),
    "roster_announcement": re.compile(r"signs?|extension|acquir|trade|named head coach|retire", re.I),
}


def format_counts(videos: list[dict]) -> dict[str, int]:
    counts = Counter()
    for video in videos:
        for label, pattern in FORMAT_RULES.items():
            if pattern.search(video.get("title", "")):
                counts[label] += 1
    return dict(sorted(counts.items()))

