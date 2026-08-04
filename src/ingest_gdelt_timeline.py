"""Acquire and ingest validity-aware GDELT DOC API daily volume exports.

The free DOC API is queried in paced 90-day windows. Existing checksum-valid
archives are reused, historical boundary windows are added when the analysis
period expands, and every request is resumable and checkpointed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from common import ROOT, now_utc, write_json
from analysis_window import ANALYSIS_START as ANALYSIS_START_TEXT, ANALYSIS_END as ANALYSIS_END_TEXT

ANALYSIS_START = date.fromisoformat(ANALYSIS_START_TEXT)
ANALYSIS_END = date.fromisoformat(ANALYSIS_END_TEXT)
MAX_WINDOW_DAYS = 90
DOWNLOAD_GLOB = "gdelt-timeline-*.json"
DIRECT_ARCHIVE_DIR = ROOT / "data/raw/gdelt/timeline_full"
LEGACY_ARCHIVE_DIR = ROOT / "data/raw/gdelt/timeline"
USER_AGENT = "nhl-moment-to-market-lab/1.0 (public-research; paced acquisition)"


def parse_day(value: str | None, fallback: date) -> date:
    return date.fromisoformat(value) if value else fallback


def gdelt_stamp(day: date, end_of_day: bool = False) -> str:
    return day.strftime("%Y%m%d") + ("235959" if end_of_day else "000000")


def source_url(query: str, start: date, end: date) -> str:
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "startdatetime": gdelt_stamp(start),
        "enddatetime": gdelt_stamp(end, end_of_day=True),
    }
    return "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode(params, quote_via=quote)


def windows(start: date, end: date) -> list[tuple[date, date]]:
    result = []
    cursor = start
    while cursor <= end:
        interval_end = min(end, cursor + timedelta(days=MAX_WINDOW_DAYS - 1))
        result.append((cursor, interval_end))
        cursor = interval_end + timedelta(days=1)
    return result


def build_plan() -> Path:
    plan_path = ROOT / "data/manifests/gdelt_timeline_plan.json"
    if plan_path.exists():
        prior = json.loads(plan_path.read_text())
        if prior.get("analysis_start") != ANALYSIS_START.isoformat() or prior.get("analysis_end") != ANALYSIS_END.isoformat():
            write_json("data/manifests/gdelt_timeline_plan_prior_window.json", {
                **prior,
                "superseded_reason": "Analysis window expanded; checksum-valid intervals are retained and new historical boundary windows are added.",
                "superseded_by": "data/manifests/gdelt_timeline_plan.json",
            })
    legacy_plan_path = ROOT / "data/manifests/gdelt_timeline_plan_90day_superseded.json"
    legacy_plan = json.loads(legacy_plan_path.read_text()) if legacy_plan_path.exists() else {"mappings": []}
    legacy_by_mapping = {item["mapping_id"]: item for item in legacy_plan.get("mappings", [])}
    mappings = []
    reused_intervals = 0
    acquisition_intervals = 0
    with (ROOT / "config/entity_dictionary.csv").open() as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "confirmed":
                continue
            valid_start = max(parse_day(row.get("valid_from"), ANALYSIS_START), ANALYSIS_START)
            valid_end = min(parse_day(row.get("valid_to"), ANALYSIS_END), ANALYSIS_END)
            if valid_start > valid_end:
                continue
            exact_name = row["entity_label"]
            query = f'"{exact_name}" sourcelang:english'
            intervals = []
            legacy_intervals = legacy_by_mapping.get(row["mapping_id"], {}).get("intervals", [])
            if legacy_intervals:
                legacy_intervals = sorted(legacy_intervals, key=lambda item: item["start_date"])
                first_legacy_start = date.fromisoformat(legacy_intervals[0]["start_date"])
                if valid_start < first_legacy_start:
                    history_end = min(valid_end, first_legacy_start - timedelta(days=1))
                    for history_index, (start, end) in enumerate(windows(valid_start, history_end)):
                        intervals.append({
                            "interval_id": f"{row['mapping_id']}-history-{history_index:03d}",
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                            "expected_days": (end - start).days + 1,
                            "source_url": source_url(query, start, end),
                            "acquisition_mode": "new_historical_boundary_window",
                        })
                        acquisition_intervals += 1
                index = 0
                gap_index = 0
                while index < len(legacy_intervals):
                    legacy = legacy_intervals[index]
                    legacy_path = LEGACY_ARCHIVE_DIR / f"{legacy['interval_id']}.json"
                    if valid_direct_response(legacy_path, legacy["source_url"]):
                        intervals.append({**legacy, "acquisition_mode": "reused_checksum_valid_90day_archive"})
                        reused_intervals += 1
                        index += 1
                        continue
                    gap_start = index
                    while index < len(legacy_intervals):
                        candidate = legacy_intervals[index]
                        candidate_path = LEGACY_ARCHIVE_DIR / f"{candidate['interval_id']}.json"
                        if valid_direct_response(candidate_path, candidate["source_url"]):
                            break
                        index += 1
                    first = legacy_intervals[gap_start]
                    last = legacy_intervals[index - 1]
                    gap_start_date = date.fromisoformat(first["start_date"])
                    gap_end_date = date.fromisoformat(last["end_date"])
                    for start, end in windows(gap_start_date, gap_end_date):
                        intervals.append({
                            "interval_id": f"{row['mapping_id']}-gap-{gap_index:03d}",
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                            "expected_days": (end - start).days + 1,
                            "source_url": source_url(query, start, end),
                            "acquisition_mode": "missing_90day_window",
                        })
                        acquisition_intervals += 1
                        gap_index += 1
                last_legacy_end = date.fromisoformat(legacy_intervals[-1]["end_date"])
                if last_legacy_end < valid_end:
                    extension_start = max(valid_start, last_legacy_end + timedelta(days=1))
                    for extension_index, (start, end) in enumerate(windows(extension_start, valid_end)):
                        intervals.append({
                            "interval_id": f"{row['mapping_id']}-extension-{extension_index:03d}",
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                            "expected_days": (end - start).days + 1,
                            "source_url": source_url(query, start, end),
                            "acquisition_mode": "new_forward_boundary_window",
                        })
                        acquisition_intervals += 1
            else:
                for gap_index, (start, end) in enumerate(windows(valid_start, valid_end)):
                    intervals.append({
                        "interval_id": f"{row['mapping_id']}-gap-{gap_index:03d}",
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "expected_days": (end - start).days + 1,
                        "source_url": source_url(query, start, end),
                        "acquisition_mode": "missing_90day_window",
                    })
                    acquisition_intervals += 1
            mappings.append({
                "mapping_id": row["mapping_id"],
                "club_id": row["club_id"],
                "entity_id": row["entity_id"],
                "entity_label": exact_name,
                "query": query,
                "valid_from": valid_start.isoformat(),
                "valid_to": valid_end.isoformat(),
                "intervals": intervals,
            })
    plan = {
        "source_id": "gdelt-doc-api-timelinevolraw",
        "source_contract": "Exact full club name; English; raw daily article count and monitored-news denominator.",
        "analysis_start": ANALYSIS_START.isoformat(),
        "analysis_end": ANALYSIS_END.isoformat(),
        "max_window_days": MAX_WINDOW_DAYS,
        "window_strategy": "reuse_checksum_valid_90day_archives_and_add_paced_90day_boundary_windows",
        "resolution_contract": "GDELT DOC timeline spans greater than one week use daily resolution; requests remain capped at 90 days for source stability",
        "resolution_source_url": "https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
        "minimum_request_spacing_seconds": 6,
        "mapping_count": len(mappings),
        "interval_count": sum(len(item["intervals"]) for item in mappings),
        "reused_interval_count": reused_intervals,
        "acquisition_interval_count": acquisition_intervals,
        "mappings": mappings,
    }
    return write_json("data/manifests/gdelt_timeline_plan.json", plan)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def valid_direct_response(path: Path, expected_url: str) -> bool:
    """Return True only for a complete, checksum-valid archived response."""
    if not path.exists():
        return False
    try:
        response = json.loads(path.read_text())
        body_text = response["body_text"]
        payload = json.loads(body_text)
        return (
            response.get("http_status") == 200
            and response.get("source_url") == expected_url
            and response.get("body_checksum") == sha256_bytes(body_text.encode())
            and bool(payload.get("timeline"))
        )
    except (KeyError, json.JSONDecodeError, OSError):
        return False


def acquire_direct(
    spacing_seconds: float = 20.0,
    attempts: int = 3,
    workers: int = 1,
    only_interval: str | None = None,
    initial_cooldown_seconds: float = 0.0,
) -> Path:
    """Fetch missing intervals with globally paced starts and durable resume."""
    plan_path = ROOT / "data/manifests/gdelt_timeline_plan.json"
    if not plan_path.exists():
        build_plan()
    plan = json.loads(plan_path.read_text())
    intervals = [
        (mapping, interval)
        for mapping in plan["mappings"]
        for interval in mapping["intervals"]
        if only_interval is None or interval["interval_id"] == only_interval
    ]
    if only_interval is not None and not intervals:
        raise ValueError(f"Unknown GDELT interval: {only_interval}")
    DIRECT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    request_lock = threading.Lock()
    last_request_started = [0.0]
    rate_state = {"blocked_until": 0.0, "consecutive_429": 0, "rate_limit_events": 0}
    if initial_cooldown_seconds > 0:
        rate_state["blocked_until"] = time.monotonic() + initial_cooldown_seconds

    def checkpoint() -> Path:
        ordered = sorted(results, key=lambda item: item["interval_id"])
        return write_json("data/manifests/gdelt_timeline_direct_acquisition.json", {
            "source_id": plan["source_id"],
            "created_at": now_utc(),
            "spacing_seconds": spacing_seconds,
            "workers": workers,
            "only_interval": only_interval,
            "initial_cooldown_seconds": initial_cooldown_seconds,
            "adaptive_429_cooldown": "120 seconds, doubling to a 600-second cap after consecutive 429 responses; reset after success",
            "rate_limit_events": rate_state["rate_limit_events"],
            "planned_intervals": len(intervals),
            "processed_intervals": len(ordered),
            "confirmed_or_cached_intervals": sum(item["status"] in {"confirmed", "cached"} for item in ordered),
            "failed_intervals": [item for item in ordered if item["status"] == "unavailable"],
            "results": ordered,
        })

    def acquire_one(index: int, mapping: dict, interval: dict) -> dict:
        target = DIRECT_ARCHIVE_DIR / f"{interval['interval_id']}.json"
        legacy_target = LEGACY_ARCHIVE_DIR / f"{interval['interval_id']}.json"
        if valid_direct_response(target, interval["source_url"]) or valid_direct_response(legacy_target, interval["source_url"]):
            print(f"[{index}/{len(intervals)}] cached {interval['interval_id']}", flush=True)
            return {"interval_id": interval["interval_id"], "status": "cached"}
        error = None
        for attempt in range(1, attempts + 1):
            with request_lock:
                now = time.monotonic()
                wait_for = max(
                    spacing_seconds - (now - last_request_started[0]),
                    rate_state["blocked_until"] - now,
                )
                if wait_for > 0:
                    time.sleep(wait_for)
                last_request_started[0] = time.monotonic()
            try:
                request = Request(interval["source_url"], headers={"User-Agent": USER_AGENT})
                with urlopen(request, timeout=120) as response:
                    body = response.read()
                    status = response.status
                body_text = body.decode("utf-8")
                payload = json.loads(body_text)
                if status != 200 or not payload.get("timeline"):
                    raise ValueError("GDELT response lacks a timeline")
                record = {
                    "interval_id": interval["interval_id"],
                    "mapping_id": mapping["mapping_id"],
                    "club_id": mapping["club_id"],
                    "source_url": interval["source_url"],
                    "http_status": status,
                    "retrieved_at": now_utc(),
                    "body_checksum": sha256_bytes(body),
                    "body_text": body_text,
                }
                target.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
                with request_lock:
                    rate_state["consecutive_429"] = 0
                print(f"[{index}/{len(intervals)}] confirmed {interval['interval_id']}", flush=True)
                return {"interval_id": interval["interval_id"], "status": "confirmed", "attempt": attempt}
            except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                if isinstance(exc, HTTPError) and exc.code == 429:
                    with request_lock:
                        rate_state["consecutive_429"] += 1
                        rate_state["rate_limit_events"] += 1
                        retry_after = exc.headers.get("Retry-After") if exc.headers else None
                        try:
                            retry_after_seconds = float(retry_after) if retry_after else 0.0
                        except ValueError:
                            retry_after_seconds = 0.0
                        cooldown = max(
                            retry_after_seconds,
                            min(1800.0, 120.0 * (2 ** (rate_state["consecutive_429"] - 1))),
                        )
                        rate_state["blocked_until"] = max(rate_state["blocked_until"], time.monotonic() + cooldown)
                if attempt < attempts:
                    time.sleep(min(90, 10 * (2 ** (attempt - 1))))
        if error:
            print(f"[{index}/{len(intervals)}] unavailable {interval['interval_id']}: {error}", flush=True)
            return {"interval_id": interval["interval_id"], "status": "unavailable", "reason": error}
        raise RuntimeError(f"Unexpected empty acquisition result: {interval['interval_id']}")

    if workers == 1:
        for index, (mapping, interval) in enumerate(intervals, start=1):
            results.append(acquire_one(index, mapping, interval))
            checkpoint()
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(acquire_one, index, mapping, interval): interval["interval_id"]
                for index, (mapping, interval) in enumerate(intervals, start=1)
            }
            for future in as_completed(futures):
                results.append(future.result())
                checkpoint()
    return checkpoint()


def archive_downloads(download_dir: Path) -> list[dict]:
    archive_dir = ROOT / "data/raw/gdelt/timeline_downloads"
    archive_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sorted(download_dir.glob(DOWNLOAD_GLOB)):
        body = source.read_bytes()
        payload = json.loads(body)
        target = archive_dir / source.name
        if target.exists() and target.read_bytes() != body:
            raise ValueError(f"Conflicting raw export already archived: {target}")
        if not target.exists():
            shutil.copyfile(source, target)
        records.append({
            "file_name": source.name,
            "archive_path": str(target.relative_to(ROOT)),
            "checksum": sha256_bytes(body),
            "bytes": len(body),
            "mapping_id": payload.get("mapping_id"),
            "batch_id": payload.get("batch_id"),
            "response_count": len(payload.get("responses", [])),
        })
    return records


def materialize(download_dir: Path) -> Path:
    plan = json.loads((ROOT / "data/manifests/gdelt_timeline_plan.json").read_text())
    plan_intervals = {
        interval["interval_id"]: (mapping, interval)
        for mapping in plan["mappings"]
        for interval in mapping["intervals"]
    }
    raw_files = archive_downloads(download_dir)
    responses = {}
    for record in raw_files:
        archive = json.loads((ROOT / record["archive_path"]).read_text())
        for response in archive.get("responses", []):
            interval_id = response.get("interval_id")
            if interval_id not in plan_intervals:
                raise ValueError(f"Unplanned GDELT interval: {interval_id}")
            if response.get("http_status") != 200:
                continue
            body_text = response.get("body_text", "")
            if response.get("body_checksum") != sha256_bytes(body_text.encode()):
                raise ValueError(f"Body checksum mismatch: {interval_id}")
            payload = json.loads(body_text)
            if not payload.get("timeline"):
                raise ValueError(f"Missing timeline payload: {interval_id}")
            prior = responses.get(interval_id)
            if prior and prior.get("retrieved_at", "") >= response.get("retrieved_at", ""):
                continue
            responses[interval_id] = response

    # Direct interval archives use the same response contract as browser bundles.
    for interval_id, (_, interval) in plan_intervals.items():
        paths = [
            DIRECT_ARCHIVE_DIR / f"{interval_id}.json",
            LEGACY_ARCHIVE_DIR / f"{interval_id}.json",
        ]
        path = next((candidate for candidate in paths if valid_direct_response(candidate, interval["source_url"])), None)
        if path is None:
            continue
        response = json.loads(path.read_text())
        prior = responses.get(interval_id)
        if not prior or prior.get("retrieved_at", "") < response.get("retrieved_at", ""):
            responses[interval_id] = response

    # Normalize both daily and hourly TimelineVolRaw responses to UTC days.
    # GDELT omits query dates with zero matching articles. Those dates may be
    # emitted as confirmed zeros only when another checksum-valid response
    # supplies the exact query-independent monitored-news denominator for that
    # same UTC day. A date with no denominator anywhere remains unavailable.
    response_daily = {}
    corpus_denominator = {}
    for interval_id, response in responses.items():
        payload = json.loads(response["body_text"])
        normalized = {}
        for point in payload["timeline"][0].get("data", []):
            day = datetime.strptime(point["date"], "%Y%m%dT%H%M%SZ").date().isoformat()
            value = point.get("value")
            denominator = point.get("norm")
            if value is None or denominator is None or denominator <= 0:
                raise ValueError(f"Invalid GDELT timeline value: {interval_id} {day}")
            aggregate = normalized.setdefault(day, {"value": 0, "norm": 0, "points": 0})
            aggregate["value"] += int(value)
            aggregate["norm"] += int(denominator)
            aggregate["points"] += 1
        response_daily[interval_id] = normalized
        for day, point in normalized.items():
            prior = corpus_denominator.get(day)
            if prior is not None and prior != point["norm"]:
                raise ValueError(f"Inconsistent GDELT corpus denominator: {day} {prior} != {point['norm']}")
            corpus_denominator[day] = point["norm"]

    daily = {}
    interval_results = []
    zero_filled_days = 0
    hourly_aggregated_days = 0
    for interval_id, (mapping, interval) in sorted(plan_intervals.items()):
        response = responses.get(interval_id)
        if not response:
            interval_results.append({**interval, "mapping_id": mapping["mapping_id"], "club_id": mapping["club_id"], "evidence_status": "unavailable", "reason": "missing_or_failed_archived_response"})
            continue
        expected_dates = {
            (date.fromisoformat(interval["start_date"]) + timedelta(days=n)).isoformat()
            for n in range(interval["expected_days"])
        }
        observed_dates = set()
        inferred_zero_dates = []
        hourly_dates = []
        for day in sorted(expected_dates):
            point = response_daily[interval_id].get(day)
            if point:
                value = point["value"]
                denominator = point["norm"]
                quality = "confirmed_exact_name_query"
                if point["points"] > 1:
                    quality = "confirmed_exact_name_query_hourly_aggregated_to_utc_day"
                    hourly_dates.append(day)
                    hourly_aggregated_days += 1
            elif day in corpus_denominator:
                value = 0
                denominator = corpus_denominator[day]
                quality = "confirmed_zero_omitted_by_query_with_exact_corpus_denominator"
                inferred_zero_dates.append(day)
                zero_filled_days += 1
            else:
                continue
            observed_dates.add(day)
            row = {
                "club_id": mapping["club_id"],
                "entity_id": mapping["entity_id"],
                "mapping_id": mapping["mapping_id"],
                "date_utc": day.replace("-", ""),
                "channel": "gdelt_earned_media",
                "metric_name": "article_count",
                "metric_value": int(value),
                "project_or_platform": "GDELT DOC 2.0 TimelineVolRaw",
                "source_url": response["source_url"],
                "retrieved_at": response["retrieved_at"],
                "evidence_quality": quality,
                "daily_monitored_article_count": int(denominator),
                "normalized_articles_per_100k": float(value) / float(denominator) * 100000,
                "query": mapping["query"],
            }
            key = (row["club_id"], row["mapping_id"], row["date_utc"])
            if key in daily and daily[key] != row:
                raise ValueError(f"Conflicting daily GDELT observation: {key}")
            daily[key] = row
        missing_dates = sorted(expected_dates - observed_dates)
        interval_results.append({
            **interval,
            "mapping_id": mapping["mapping_id"],
            "club_id": mapping["club_id"],
            "evidence_status": "confirmed" if not missing_dates else "unavailable",
            "observed_days": len(observed_dates),
            "missing_days": missing_dates,
            "confirmed_zero_days": inferred_zero_dates,
            "hourly_aggregated_days": hourly_dates,
            "retrieved_at": response["retrieved_at"],
            "body_checksum": response["body_checksum"],
        })

    rows = [daily[key] for key in sorted(daily)]
    write_json("data/curated/gdelt_attention_daily.json", rows)
    all_responses_archived = len(responses) == len(plan_intervals)
    source_unavailable_days = sorted({
        day
        for item in interval_results
        for day in item.get("missing_days", [])
    }) if all_responses_archived else []
    if all_responses_archived:
        status = "confirmed_with_visible_source_gaps" if source_unavailable_days else "confirmed"
    else:
        status = "unavailable_partial"
    return write_json("data/manifests/gdelt_timeline_acquisition.json", {
        "source_id": plan["source_id"],
        "created_at": now_utc(),
        "evidence_status": status,
        "planned_intervals": len(plan_intervals),
        "confirmed_intervals": sum(item["evidence_status"] == "confirmed" for item in interval_results),
        "archived_response_count": len(responses),
        "source_unavailable_days": source_unavailable_days,
        "source_unavailable_day_count": len(source_unavailable_days),
        "daily_rows": len(rows),
        "corpus_denominator_days": len(corpus_denominator),
        "confirmed_zero_days": zero_filled_days,
        "hourly_aggregated_days": hourly_aggregated_days,
        "zero_policy": "A missing query point becomes zero only when another archived response supplies the exact query-independent monitored-news denominator for that UTC day; otherwise the date remains unavailable.",
        "source_gap_policy": "When every planned response is archived but no response supplies a monitored-news denominator for a UTC date, that date remains explicitly unavailable across the source and is excluded from modeling rather than imputed as zero.",
        "club_identities": sorted({row["club_id"] for row in rows}),
        "raw_files": raw_files,
        "interval_results": interval_results,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--acquire-direct", action="store_true")
    parser.add_argument("--spacing-seconds", type=float, default=20.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--only-interval")
    parser.add_argument("--initial-cooldown-seconds", type=float, default=0.0)
    parser.add_argument("--ingest-downloads", type=Path)
    args = parser.parse_args()
    if args.plan:
        print(build_plan())
    elif args.acquire_direct:
        print(acquire_direct(
            spacing_seconds=args.spacing_seconds,
            attempts=args.attempts,
            workers=args.workers,
            only_interval=args.only_interval,
            initial_cooldown_seconds=args.initial_cooldown_seconds,
        ))
    elif args.ingest_downloads:
        print(materialize(args.ingest_downloads.expanduser()))
    else:
        parser.error("Use --plan or --ingest-downloads PATH")


if __name__ == "__main__":
    main()
