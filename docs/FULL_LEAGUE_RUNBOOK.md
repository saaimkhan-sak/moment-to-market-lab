# Full-league acquisition runbook

## Full-league source state

- MoneyPuck all-teams game file plus 2015–16 through 2025–26 shot archives are preserved with checksums.
- YouTube Data API and BEA credentials have passed minimal, non-secret preflight checks.
- NHL GameCenter schedules, boxscores, and play-by-play are archived for the registered 2015–16 through 2025–26 window, with expansion clubs entering only in eligible seasons.
- Wikidata validity mappings and all 32 official YouTube channels are verified; all accessible uploads have been archived.
- MoneyPuck reconciles 14,508 eligible regular-season and playoff games against the NHL archive. It contributes expected-goal and score-state context; six score disagreements remain explicitly documented, with the NHL final score retained as the canonical result.
- U.S. and Canadian market data cover all 32 clubs; BLS suppressions remain visible and use separately labelled ACS fallbacks only in the preferred display.

## Ordered full run

1. Archive NHL GameCenter responses, MoneyPuck files, Wikimedia observations, the GDELT GKG historical extract, official YouTube uploads, and market-source extracts with checksums and retrieval timestamps.
2. Materialize the daily Wikimedia and GDELT panels. The GDELT release query uses exact audited full-name matching, plus separately audited club-bearing URL recovery rules for Boston, Chicago, Nashville, and Winnipeg. Preserve the 18 dates where GKG has no monitored web records as unavailable, never zero.
3. Rebuild the full versioned moment panel and response windows for 2015–16 through 2025–26. Expansion identities enter only in valid seasons; Arizona and Utah remain separate identities.
4. Fit separate Wikimedia and GDELT hierarchical models and apply the registered cross-channel agreement rule. Suppress club–moment–window rankings below ten observations.
5. Build 32 club profiles, three evidence-gated test notes per club, and 32 five-slide memos.
6. Assemble the shared website, perform responsive browser and performance QA, then run every release gate.

The GDELT DOC API is retained only for recent article-context checks. Its rolling precise-date window cannot support the registered historical panel and is not a model input.

No club-level headline, ranking, playbook recommendation, or memo finding is released until this sequence and the release gates complete.
