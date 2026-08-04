# Data dictionary

| Table | Grain | Primary key | Purpose |
| --- | --- | --- | --- |
| `game` | game | `game_id` | Final game context from NHL public endpoints, with a separately sourced nested MoneyPuck context where reconciled. |
| `moneypuck_game_context` | game | `game_id` | All-situation and manpower-specific xG plus shot/xG score-state splits; MoneyPuck remains an enrichment source rather than the official result source. |
| `game_event` | play event | `game_id,event_id` | Objective moment detection inputs. |
| `moment` | qualifying club-moment | `moment_id` | Taxonomy-detected event, rules, source and evidence state. |
| `official_announcement` | manually reviewed official publication | `announcement_id` | Dated roster, playoff-clinch, or community/heritage source. Trigger time is the official publication timestamp, not an inferred transaction time. |
| `entity_mapping` | source entity mapping | `entity_id,platform` | Auditable Wikidata/Wikipedia/channel mappings and aliases. |
| `attention_daily` | entity-day-channel | `club_id,entity_id,date_utc,channel,metric_name` | Independent public attention observations; missing remains missing. |
| `gdelt_attention_daily` | club-entity-day | `club_id,mapping_id,date_utc` | Exact-name English article count, monitored-news denominator, and normalized articles per 100,000. Hourly API points are aggregated to UTC day. An omitted query date is zero only when the exact corpus denominator exists for that date; otherwise it remains unavailable. |
| `gdelt_article_observation` | returned article | `article_url,retrieved_at` | Query/audit record; tone is never sentiment. |
| `content_video` | video snapshot | `video_id,retrieved_at` | Official-channel current public video statistics. |
| `youtube_event_publication` | moment-video assignment | `moment_id,video_id` | Official upload publication timing in Days 0–7 after a moment. Overlapping moments use the closest-preceding assignment. Current engagement totals are excluded. |
| `youtube_historical_comment_event` | moment-video-surviving-comment | `moment_id,video_id,comment_id` | Original timestamps for top-level comments still public at retrieval on the first official upload in Days 0–1. Deleted, moderated, reply, and disabled-comment observations are not reconstructed. |
| `market_context` | market/source/period/measure | `club_id,source_id,period,measure_id` | Descriptive U.S./Canadian market context only. U.S. industry concentration retains QCEW and ACS C24030 separately; `preferred_industry_lq_*` uses QCEW when publishable and a labeled ACS survey fallback otherwise. |
| `club_moment_estimate` | club-moment-channel-window-model | compound | League-level modeled association plus club-local raw median, modeled and raw bootstrap intervals, modeled and isolated sample sizes, and coverage. |
| `activation_playbook` | club-priority-moment | `playbook_id` | Three time-bounded, evidence-gated test notes per club, including club-local channel evidence and descriptive official-content format context; every internal KPI requires club validation. |
| `evidence_coverage` | club-source-period | compound | Availability, limitation and quality. |
| `release_manifest` | release | `release_id` | Immutable source, code, taxonomy and model version record. |

All timestamps are UTC. Local time is a separately derived display field. `unknown`, `unavailable`, `blocked`, and `missing` are non-numeric evidence states.
