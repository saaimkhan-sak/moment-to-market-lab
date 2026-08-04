# Data-quality plan

Each raw response receives a URL, retrieval time, source identifier, checksum, and schema hash. NHL response values are reconciled to a defined MoneyPuck sample. Entity mappings retain Wikidata IDs, redirects/aliases, and review status. Pageview missingness is rendered and never converted to zero.

GDELT is article-level audited in a stratified sample of at least 160 articles, with at least five active-extraction observations per current club. Precision below 90% makes that club unavailable as a quantified outcome. The DOC API remains a recent article-context source, but its documented rolling search window does not support the full 2015–2026 panel and it is not the historical quantified source.

The release uses the archived, partition-pruned GKG exact-name daily panel. Its base 257-row audit qualifies 28 current clubs. Boston, Chicago, Nashville, and Winnipeg use the separately registered exact-name-plus-URL-subject extraction; its deterministic 40-row audit contains ten true matches per club. The active extraction has 185 reviewed articles and qualifies all 32 clubs. The failed base extraction remains preserved as an excluded diagnostic, and the recovery rule’s reduced recall is explicit. Eighteen source-partition dates remain unavailable league-wide.

Every release checks registry, entity validity, full YouTube upload coverage, preseason exclusion, NHL/MoneyPuck reconciliation, announcement and rivalry provenance, GDELT audit and daily coverage, two-channel convergence, cross-channel stability, small-sample suppression, differentiated playbooks, 32 five-slide memos, web-release assembly, no commercial overclaim, and deterministic output.
