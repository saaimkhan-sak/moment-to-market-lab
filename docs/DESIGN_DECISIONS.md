# Design decisions — The Rinkside Research Desk

The interface is a research pre-read, not SaaS or a fan site. It uses bone `#F4F1EA`, ink `#13201D`, evergreen `#213B36`, cold slate `#607078`, ice `#DDE7E6`, rule `#C8D0CD`, red `#BD4239`, amber `#C9902E`, and green `#35755D`. Club accent is a documented, restrained line/keyline only.

Signal red remains `#BD4239` for non-text chart marks and rules. Warning text uses the darker companion `#96352F` so it clears WCAG AA contrast on the ice surface while retaining the same semantic role.

Typography roles are Source Serif 4 for narrative claims, IBM Plex Sans for reading/interface, and IBM Plex Mono for measured evidence. The layout favors an editorial masthead, rule-based evidence stamps, asymmetric report columns, a hand-built SVG response trace, and a dense event docket. Cards are not a default layout primitive.

The app uses visible source links, active filters in prose, real no-signal states, semantic sections, keyboard focus, and reduced-motion support. The build avoids decorative color gradients, generic icons, fake controls, stock/AI hockey images, and assertions which public data cannot establish. Its only gradient function is the permitted 1% repeating line texture used as quiet paper grain. This records the attached design references' emphasis on a deliberate design system, bespoke visual anchors, real browser QA, and authored hierarchy.

One shared page system serves the League Desk and all `/clubs/[club-slug]` routes. Club, moment, response-window, and source selections are encoded in the URL and update the finding, evidence stamp, trace, docket, and accessible table together. The canonical chart is a hand-authored SVG with direct labels and a tabular text equivalent; no chart-library defaults are exposed. Official YouTube content is summarized before browser delivery so the site does not ship the 126,000-plus-video archive to each visitor.
