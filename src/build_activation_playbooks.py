"""Create club-specific, evidence-gated activation test notes."""
from __future__ import annotations

from collections import Counter
import csv
import json

from common import ROOT, write_json
from build_club_profiles import assessment_candidates
from content_formats import format_counts


TEMPLATES = {
    "rivalry_win": ("content", "Package the decisive rivalry sequence with opponent context and an exact source trail.", "Publish one follow-up explaining the rivalry moment through comparable games rather than rivalry mythology.", "Close the sequence with a sourced recap and retain the publishing timestamps for internal evaluation."),
    "rivalry_loss": ("communications", "Issue a factual result-and-next-game note; avoid treating elevated attention after a loss as positive sentiment.", "Track whether earned-media coverage centers on performance, availability, or opponent narrative.", "Document the narrative decay and compare it with other rivalry losses before changing cadence."),
    "two_goal_third_period_comeback_win": ("content", "Publish the verified comeback sequence with the third-period starting deficit clearly stated.", "Release one player or coach explanation tied to the turning point, with the game evidence linked.", "Compare the full seven-day response with other qualifying comebacks and preserve overlap exclusions."),
    "overtime_win": ("content", "Publish the decisive overtime sequence and a concise game-context explainer while the immediate window is open.", "Add one format that explains how the winning sequence developed; retain exact publish time.", "Review persistence against other overtime wins before repeating the format as a standard."),
    "shootout_win": ("content", "Publish the winning attempt and goalie sequence with the shootout state labelled explicitly.", "Use one compact explainer or player reaction rather than treating the result as regulation performance.", "Compare the seven-day signal with overtime and regulation wins before standardizing the package."),
    "hat_trick": ("content", "Publish a three-goal evidence package with timestamps and the scorer's official game line.", "Add one player-led or tactical explanation while retaining source links to all three goals.", "Test whether the player-information response persists after Day 3 using internal content timestamps."),
    "four_point_game": ("content", "Publish the player's complete scoring contribution and distinguish goals from assists.", "Use a sourced sequence breakdown instead of a generic performance superlative.", "Compare persistence with other four-point games before committing recurring production resources."),
    "goalie_high_volume_shutout": ("content", "Publish the official shutout and 40-plus-save line with a save-sequence evidence path.", "Add a workload or shot-location explainer using public game data; do not infer proprietary tracking data.", "Review whether attention persists beyond the recap cycle and whether internal video completion supports reuse."),
    "playoff_clinch": ("communications", "Publish the official berth confirmation and clearly distinguish qualification from seeding or home ice.", "Sequence one practical postseason-context explainer and one team voice, preserving publication times.", "Measure whether the public response persists after the initial clinch announcement before extending the campaign."),
    "official_roster_event": ("communications", "Publish the official transaction or appointment source with the observable announcement timestamp.", "Answer the highest-frequency factual questions through official material; do not infer contract economics beyond disclosed terms.", "Compare seven-day information demand with prior roster events and request internal referral-path data."),
    "community_or_heritage_event": ("community", "Lead with the official program, artist, participant, or community purpose and its dated source.", "Publish participant-centered context and the event's intended public outcome without turning attention volume into social impact.", "Review public-information persistence alongside the club's own approved program measures."),
}

INTERNAL_KPI = {
    "content": "Club-owned completion rate and publish-to-consumption curve for the registered package",
    "communications": "Referral and pickup quality for the official announcement or briefing",
    "community": "Club-approved program participation or partner-defined community outcome",
}


def same_direction(candidate: dict) -> bool:
    values = [row.get("estimate") for row in candidate["channel_estimates"]]
    return all(value is not None and value > 0 for value in values) or all(value is not None and value < 0 for value in values)


def choose_three(club: str, candidates: list[dict], moment_counts: Counter) -> list[dict]:
    best_by_type = {}
    for row in candidates:
        current = best_by_type.get(row["moment_type"])
        score = (
            row["stable"],
            same_direction(row),
            row["minimum_sample_size"],
            row.get("local_raw_mean") if row.get("local_raw_mean") is not None else -10**9,
        )
        if current is None or score > current[0]:
            best_by_type[row["moment_type"]] = (score, row)
    ranked = [item[1] for item in sorted(best_by_type.values(), key=lambda item: item[0], reverse=True)]
    selected = ranked[:3]
    if len(selected) < 3:
        selected_types = {row["moment_type"] for row in selected}
        for (candidate_club, moment_type), count in moment_counts.most_common():
            if candidate_club == club and moment_type not in selected_types:
                selected.append({
                    "club_id": club,
                    "moment_type": moment_type,
                    "post_window": "immediate",
                    "cross_channel_status": "insufficient_channel_coverage",
                    "stable": False,
                    "minimum_sample_size": count,
                    "minimum_isolated_sample_size": 0,
                    "channel_estimates": [],
                    "rule": "measurement-only fallback; not a modeled finding",
                })
                selected_types.add(moment_type)
                if len(selected) == 3:
                    break
    return selected


def build():
    model = json.loads((ROOT / "data/curated/club_moment_estimate.json").read_text())
    moments = json.loads((ROOT / "data/curated/moment.json").read_text())
    videos = json.loads((ROOT / "data/curated/content_video.json").read_text())
    if model.get("status") != "confirmed" or set(model.get("channels", [])) != {"wikimedia_pageviews", "gdelt_earned_media"}:
        raise RuntimeError("Playbooks require a confirmed Wikimedia + GDELT model")
    moment_counts = Counter((row["club_id"], row["moment_type"]) for row in moments)
    videos_by_club = {}
    for video in videos:
        videos_by_club.setdefault(video["club_id"], []).append(video)
    with (ROOT / "config/clubs.csv").open(newline="") as handle:
        clubs = list(csv.DictReader(handle))

    rows = []
    for config in clubs:
        club = config["club_id"]
        club_videos = videos_by_club.get(club, [])
        club_format_counts = format_counts(club_videos)
        leading_format, leading_format_count = max(club_format_counts.items(), key=lambda item: (item[1], item[0])) if club_format_counts else ("unclassified", 0)
        for rank, candidate in enumerate(choose_three(club, assessment_candidates(model, club), moment_counts), start=1):
            moment_type = candidate["moment_type"]
            owner, first, second, third = TEMPLATES[moment_type]
            if candidate["stable"]:
                confidence = "stable_cross_channel_public_signal"
                operating_mode = "timed_activation_test"
            elif same_direction(candidate) if candidate.get("channel_estimates") else False:
                confidence = "directional_hypothesis_not_stable"
                operating_mode = "measurement_rehearsal"
            else:
                confidence = "no_reliable_pattern_measurement_only"
                operating_mode = "measurement_rehearsal"
            local_channel_evidence = [
                {
                    "attention_channel": row["attention_channel"],
                    "raw_median_lift": row.get("raw_median_lift"),
                    "raw_confidence_interval_low": row.get("raw_confidence_interval_low"),
                    "raw_confidence_interval_high": row.get("raw_confidence_interval_high"),
                    "modeled_estimate": row.get("estimate"),
                    "modeled_confidence_interval_low": row.get("confidence_interval_low"),
                    "modeled_confidence_interval_high": row.get("confidence_interval_high"),
                    "modeled_sample_size": row.get("sample_size"),
                    "isolated_sample_size": row.get("isolated_sample_size"),
                }
                for row in candidate.get("channel_estimates", [])
            ]
            rows.append({
                "playbook_id": f"{config['club_slug']}--{rank}--{moment_type}",
                "club_id": club,
                "club_name": config["club_name"],
                "priority_within_club": rank,
                "moment_type": moment_type,
                "owner_function": owner,
                "trigger": f"Confirmed {moment_type.replace('_', ' ')} under taxonomy v1.1.0 with source coverage for the registered {candidate['post_window'].replace('_', ' ')} window",
                "action_0_24h": first + f" The official-channel archive contains {leading_format_count:,} titles coded as {leading_format.replace('_', ' ')}.",
                "action_24_72h": second,
                "action_day_4_7": third,
                "public_kpi": "Wikimedia daily pageviews, corroborated by audited GDELT normalized article volume",
                "internal_kpi": INTERNAL_KPI[owner],
                "driver_metrics": "official publish time; source coverage; comparable-event count; overlap status; format and distribution timestamps",
                "guardrails": "Public attention is not sentiment, attendance, revenue, sponsor value, conversion, or fan identity. Pause if either public channel is unavailable or matching precision falls below threshold.",
                "internal_data_required": f"Owned-channel publication and distribution timestamps plus the club-approved {owner} outcome definition",
                "confidence_label": confidence,
                "operating_mode": operating_mode,
                "requires_internal_validation": True,
                "evidence": {
                    "cross_channel_status": candidate["cross_channel_status"],
                    "post_window": candidate["post_window"],
                    "minimum_sample_size": candidate["minimum_sample_size"],
                    "minimum_isolated_sample_size": candidate["minimum_isolated_sample_size"],
                    "channel_estimates": candidate.get("channel_estimates", []),
                    "club_local_channel_evidence": local_channel_evidence,
                    "stability_rule": candidate["rule"],
                },
                "official_content_context": {
                    "accessible_video_count": len(club_videos),
                    "leading_observed_title_format": leading_format,
                    "leading_observed_title_format_count": leading_format_count,
                    "all_observed_title_format_counts": club_format_counts,
                    "classification_rule": "case-insensitive title keyword rules in src/content_formats.py; categories may overlap and counts are descriptive",
                    "limitation": "Current public statistics and title formats do not establish historical 24-hour performance or format effectiveness.",
                },
                "model_version": model["model_version"],
                "taxonomy_version": "1.1.0",
            })
    if len(rows) != 96:
        raise ValueError(f"Expected exactly three playbooks for each of 32 clubs; got {len(rows)}")
    return write_json("data/curated/activation_playbook.json", rows)


if __name__ == "__main__":
    print(build())
