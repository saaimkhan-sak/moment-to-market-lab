# Methodology v2.0.0

The NHL Moment-to-Market Intelligence Lab measures descriptive public-attention responses around objectively registered hockey and official-publication moments. It does not measure attendance, revenue, sponsor value, conversion, CRM behavior, renewal probability, sentiment, or fan identity.

## Event and attention windows

The historical release covers 2015–16 through 2025–26. The panel is intentionally unbalanced: Vegas begins in 2017–18, Seattle in 2021–22, and Utah in 2024–25; Arizona remains a separate historical identity through 2023–24. Preseason games are excluded. For each qualifying club moment, the 14 days preceding Day 0 form the baseline. Registered post-event windows are immediate (Days 0–1), short persistence (Days 2–3), and sustained attention (Days 4–7).

`attention_lift = (post_window_value - mean(pre_event_window_value)) / max(mean(pre_event_window_value), 1)`

The isolated raw-median event study excludes a moment when another major moment for the same club falls within ±7 days, and retains the exclusion reason. The hierarchical daily model enters overlapping moment-window indicators jointly rather than pretending each event is isolated.

## Public-attention channels

Wikimedia daily pageviews are the primary independent information-demand outcome. Missing days remain missing and are never converted to zero. Pageviews are not unique people, sentiment, or purchase intent.

GDELT’s DOC API is retained for recent article-context checks, but its documented precise-date search window cannot supply an eleven-season history. The historical quantified outcome therefore uses the partitioned GDELT GKG 2.1 public dataset. It counts distinct web-source article URLs whose extracted `AllNames` field contains the registered full club name, divides that count by the daily web-source GKG denominator, and reports observations per 100,000 monitored articles.

The base GKG extraction was manually reviewed across 257 articles and qualified 28 current clubs. It failed for Boston, Chicago, Nashville, and Winnipeg because an extracted club name could appear outside the article’s substantive subject. Those four clubs use the separately versioned and audited precision-recovery rule requiring both the exact `AllNames` entity and a club-bearing article URL. The active release extraction has 185 manually reviewed articles and qualifies all 32 current clubs at the 90% threshold; its 40 recovery articles were all true club-subject matches. The failed base rows remain preserved as an excluded diagnostic and are not relabelled. Eighteen source-partition dates across the expanded history have no denominator, remain unavailable for every club, and never become zero. GDELT volume is earned-media coverage, not readership or fan sentiment.

Official YouTube data support two distinct layers. Publication timestamps measure the club's observable content response in Days 0–1, 2–3, and 4–7 after a moment. For an objective interaction check, the system selects the first official upload in Days 0–1 without using engagement and reconstructs the timestamps of top-level comments still public at retrieval. Deleted, moderated, reply, and disabled-comment observations are unavailable, so this is descriptive surviving public interaction rather than total historical engagement or sentiment. Current views, likes, comments, and channel subscribers remain retrieval-time snapshots and are never assigned to a past event. Prospective daily trajectory collection is intentionally deferred.

## Hierarchical model and stability

Wikimedia and GDELT are modeled separately using:

`log(attention + 1) ~ moment-window indicators + home_away + standings_context + day_of_week + month + season_effect + club_random_intercept + opponent_random_intercept`

Each output retains raw medians, modeled estimates, modeled and raw bootstrap 95% intervals, sample size, isolated sample size, model version, and sensitivity checks using 7-day and 21-day alternative baselines. Club–moment cells with fewer than ten modeled or ten isolated observations are not ranking-eligible.

A club–moment–window finding is labelled stable only when:

1. Wikimedia and GDELT each have at least ten modeled and ten isolated observations;
2. their modeled estimates and club-local raw medians point in the same direction in both channels; and
3. every modeled and raw 95% interval excludes zero.

Anything else is labelled mixed, insufficient, unavailable, or a measurement-only hypothesis. Stability remains descriptive association, not causal evidence.

## Official publication moments

Playoff clinches, roster events, and community or heritage events require a dated official NHL or club source. The current source table uses archived videos from verified official club channels. Day 0 is the official public video publication timestamp, not an inferred transaction or event time.

## Market context

U.S. industry location quotients use 2024 annual BLS QCEW private employment when the metro-sector cell is publishable. A BLS confidentiality suppression remains unavailable and is never interpreted as zero or low concentration. The system calculates a separate ACS 2020–2024 five-year C24030 resident-worker industry LQ with its 90% margin-of-error inputs. The preferred display uses QCEW first and an explicitly labelled ACS estimate only when QCEW is suppressed. These sources are not interchangeable raw employment counts.

Canadian market measures retain Statistics Canada definitions and currencies. U.S. and Canadian context is not forced into a common rank and does not enter the same-day attention outcome.
