"""Generate 32 five-slide, print-ready executive research memos."""
from __future__ import annotations

from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path

from common import ROOT, write_json


FEEDBACK = "Which public-attention signal would be useful in your team’s workflow, and which internal data would you need before acting on it?"


def fmt_number(value):
    return f"{value:,}" if isinstance(value, int) else str(value)


def evidence_lines(profile: dict) -> list[str]:
    finding = profile.get("finding_evidence")
    if not finding:
        return [
            "Cross-channel status: no reliable pattern",
            f"Wikimedia days: {fmt_number(profile['attention_days_by_channel']['wikimedia_pageviews'])}",
            f"GDELT days: {fmt_number(profile['attention_days_by_channel']['gdelt_earned_media'])}",
            f"Registered moments: {fmt_number(profile['moment_records'])}",
        ]
    return [
        f"Moment: {finding['moment_type'].replace('_', ' ')}",
        f"Window: {finding['post_window'].replace('_', ' ')}",
        f"Minimum modeled sample: {finding['minimum_sample_size']}",
        f"Cross-channel status: {finding['cross_channel_status']}",
    ]


def build_slides(profile: dict, playbooks: list[dict], league_benchmark: list[dict]) -> list[dict]:
    coverage = profile["attention_days_by_channel"]
    slides = [
        {
            "slide": 1,
            "kicker": "DECISION AND EVIDENCE COVERAGE",
            "title": profile["finding"],
            "body": profile["reason"],
            "evidence": evidence_lines(profile),
            "limitation": profile["limitation"],
        },
        {
            "slide": 2,
            "kicker": "CLUB MOMENT-RESPONSE PROFILE",
            "title": f"{profile['moment_records']:,} registered moments across the eligible 2015–16 through 2025–26 archive.",
            "body": "The profile keeps immediate, short-persistence, and sustained windows separate and suppresses club–moment cells with fewer than ten observations.",
            "evidence": [
                f"Wikimedia observations: {coverage['wikimedia_pageviews']:,}",
                f"GDELT observations: {coverage['gdelt_earned_media']:,}",
                f"Official YouTube videos: {profile['youtube_current_snapshot_videos']:,}",
                f"GDELT audit precision: {profile['gdelt_precision'].get('precision', 0):.1%}",
            ],
            "limitation": profile["youtube_limitation"],
        },
        {
            "slide": 3,
            "kicker": "LEAGUE BENCHMARK",
            "title": "Cross-channel agreement is uncommon by design.",
            "body": "The benchmark counts only club–moment–window cells that meet both sample and precision rules. A high single-channel estimate is not promoted to a stable finding.",
            "benchmark": league_benchmark,
            "limitation": "League comparisons describe public-signal associations and do not rank club business performance.",
        },
        {
            "slide": 4,
            "kicker": "THREE ACTIVATION TEST NOTES",
            "title": "A 0–24 hour, 24–72 hour, and Day 4–7 sequence—with the evidence gate attached.",
            "playbooks": playbooks,
            "limitation": "Every action is a test protocol. Any internal KPI or commercial use requires club validation.",
        },
        {
            "slide": 5,
            "kicker": "MEASUREMENT PLAN AND INTERNAL-DATA REQUEST",
            "title": "Connect public attention to an approved internal outcome before acting.",
            "body": "Retain exact publication and distribution timestamps, predeclare one internal outcome, preserve no-signal cases, and compare the same moment definition over time.",
            "evidence": [
                "Internal request: owned-channel publication and distribution timestamps",
                "Internal request: approved outcome definition and attribution window",
                "Guardrail: no revenue, attendance, sponsor, CRM, or conversion inference from public signals",
                f"Feedback question: {FEEDBACK}",
            ],
            "limitation": "Public attention can identify a timing hypothesis; it cannot establish downstream business value.",
        },
    ]
    for slide in slides:
        slide["club_name"] = profile["club_name"]
        slide["as_of"] = profile["as_of"]
    return slides


def slide_html(slide: dict) -> str:
    evidence = "".join(f"<li>{escape(str(item))}</li>" for item in slide.get("evidence", []))
    benchmark = "".join(
        f"<tr><td>{escape(row['moment_type'].replace('_', ' '))}</td><td>{row['stable_club_window_cells']}</td><td>{escape(row['leading_window'].replace('_', ' '))}</td></tr>"
        for row in slide.get("benchmark", [])
    )
    playbooks = "".join(
        "<article class='playbook'>"
        f"<p class='mono'>{escape(item['moment_type'].replace('_', ' '))} · {escape(item['confidence_label'])}</p>"
        f"<h3>{escape(item['owner_function'].capitalize())}</h3>"
        f"<dl><dt>0–24H</dt><dd>{escape(item['action_0_24h'])}</dd><dt>24–72H</dt><dd>{escape(item['action_24_72h'])}</dd><dt>DAY 4–7</dt><dd>{escape(item['action_day_4_7'])}</dd></dl>"
        "</article>"
        for item in slide.get("playbooks", [])
    )
    return (
        f"<section class='slide' aria-label='Slide {slide['slide']}'>"
        f"<header><span>{escape(slide['club_name'])} · {slide['slide']} / 5 · AS OF {escape(slide['as_of'])}</span><b>{escape(slide['kicker'])}</b></header>"
        f"<h2>{escape(slide['title'])}</h2>"
        f"<p class='body'>{escape(slide.get('body', ''))}</p>"
        + (f"<ul>{evidence}</ul>" if evidence else "")
        + (f"<table><thead><tr><th>MOMENT</th><th>STABLE CELLS</th><th>LEADING WINDOW</th></tr></thead><tbody>{benchmark}</tbody></table>" if benchmark else "")
        + (f"<div class='playbooks'>{playbooks}</div>" if playbooks else "")
        + f"<footer>{escape(slide['limitation'])}</footer></section>"
    )


def memo_html(memo: dict, accent: str) -> str:
    slides = "".join(slide_html(slide) for slide in memo["slides"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(memo['title'])}</title><style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:wght@400;600&display=swap');
:root{{--bone:#f4f1ea;--ink:#13201d;--slate:#607078;--rule:#c8d0cd;--ice:#dde7e6;--accent:{accent}}}*{{box-sizing:border-box}}body{{margin:0;background:#d8d8d4;color:var(--ink);font:16px/1.5 'IBM Plex Sans',sans-serif}}.deck{{display:grid;gap:28px;justify-content:center;padding:28px}}.slide{{position:relative;width:1280px;min-height:720px;padding:48px 58px 46px;background:var(--bone);border-top:5px solid var(--accent);display:flex;flex-direction:column}}header{{display:flex;justify-content:space-between;border-bottom:1px solid var(--ink);padding-bottom:12px;font:500 11px 'IBM Plex Mono';letter-spacing:.08em}}h1,h2{{font:400 48px/1.03 'Source Serif 4';max-width:980px;margin:52px 0 18px}}.body{{font-size:19px;max-width:850px}}ul{{columns:2;gap:50px;margin-top:36px;padding:20px 0 0;list-style:none;border-top:1px solid var(--rule)}}li{{break-inside:avoid;padding:8px 0;font:14px 'IBM Plex Mono'}}table{{border-collapse:collapse;width:100%;margin-top:32px}}th,td{{padding:12px;border-bottom:1px solid var(--rule);text-align:left}}th,.mono,dt{{font:500 10px 'IBM Plex Mono';letter-spacing:.07em}}.playbooks{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:24px}}.playbook{{border-top:2px solid var(--ink);padding-top:10px}}.playbook h3{{margin:8px 0 14px}}dl{{margin:0}}dt{{margin-top:12px}}dd{{margin:3px 0;font-size:13px}}footer{{margin-top:auto;border-top:1px solid var(--rule);padding-top:12px;color:var(--slate);font:11px 'IBM Plex Mono'}}@media(max-width:900px){{.deck{{display:block;padding:0}}.slide{{width:100%;min-height:100vh;padding:28px 22px;margin-bottom:10px}}h2{{font-size:36px}}.playbooks{{grid-template-columns:1fr}}}}@media print{{@page{{size:13.333in 7.5in;margin:0}}body{{background:white}}.deck{{display:block;padding:0}}.slide{{break-after:page;width:13.333in;height:7.5in;min-height:0}}}}
</style></head><body><main class="deck">{slides}</main></body></html>"""


def build():
    profiles = json.loads((ROOT / "data/curated/club_profiles.json").read_text())
    playbooks = json.loads((ROOT / "data/curated/activation_playbook.json").read_text())
    model = json.loads((ROOT / "data/curated/club_moment_estimate.json").read_text())
    current_clubs = {profile["club_id"] for profile in profiles}
    stable = [row for row in model["cross_channel_assessments"] if row["stable"] and row["club_id"] in current_clubs]
    counts = Counter(row["moment_type"] for row in stable)
    windows = {}
    for kind in counts:
        window_counts = Counter(row["post_window"] for row in stable if row["moment_type"] == kind)
        windows[kind] = window_counts.most_common(1)[0][0]
    benchmark = [
        {"moment_type": kind, "stable_club_window_cells": count, "leading_window": windows[kind]}
        for kind, count in counts.most_common(6)
    ]
    if not benchmark:
        benchmark = [{"moment_type": "no_registered_stable_pattern", "stable_club_window_cells": 0, "leading_window": "not_available"}]

    manifest = []
    for profile in profiles:
        club_playbooks = sorted(
            [row for row in playbooks if row["club_id"] == profile["club_id"]],
            key=lambda row: row["priority_within_club"],
        )
        memo = {
            "club_id": profile["club_id"],
            "club_slug": profile["club_slug"],
            "title": f"{profile['club_name']} Moment-to-Market Intelligence Brief",
            "as_of": profile["as_of"],
            "taxonomy_version": profile["taxonomy_version"],
            "model_version": profile["model_version"],
            "feedback_question": FEEDBACK,
            "slides": build_slides(profile, club_playbooks, benchmark),
        }
        output_dir = ROOT / "outputs/memos" / profile["club_slug"]
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "executive-memo.json"
        html_path = output_dir / "index.html"
        json_path.write_text(json.dumps(memo, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        html_path.write_text(memo_html(memo, profile["club_accent"]))
        manifest.append({
            "club_id": profile["club_id"],
            "club_slug": profile["club_slug"],
            "json_path": str(json_path.relative_to(ROOT)),
            "html_path": str(html_path.relative_to(ROOT)),
            "json_checksum": hashlib.sha256(json_path.read_bytes()).hexdigest(),
            "html_checksum": hashlib.sha256(html_path.read_bytes()).hexdigest(),
            "slide_count": len(memo["slides"]),
            "analytical_signature": hashlib.sha256(json.dumps({
                "finding": profile.get("finding_evidence"),
                "moment_type_counts": profile.get("moment_type_counts"),
                "playbooks": [
                    {
                        "moment_type": row["moment_type"],
                        "post_window": row["evidence"]["post_window"],
                        "confidence_label": row["confidence_label"],
                        "content_context": row["official_content_context"],
                    }
                    for row in club_playbooks
                ],
            }, sort_keys=True).encode()).hexdigest(),
        })
    return write_json("outputs/release_manifests/executive_memos.json", {
        "evidence_status": "confirmed",
        "club_count": len(manifest),
        "memo_count": len(manifest),
        "slides_per_memo": 5,
        "records": manifest,
    })


if __name__ == "__main__":
    print(build())
