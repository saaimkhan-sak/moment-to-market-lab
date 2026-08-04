# Design decisions — The Rinkside Research Desk, narrative edition

## Design brief

**Central job.** Explain why the NHL Moment-to-Market Intelligence Lab exists, show exactly how the evidence is assembled, and let a general hockey audience explore what the record says for every club without requiring statistical fluency.

**Audience.** Curious hockey supporters, media readers, and club-side content, communications, marketing, partnerships, strategy, and business-intelligence staff.

**Emotional register.** A composed rinkside analyst explaining a careful piece of work on television after the noise of the game has settled: direct, hockey-literate, skeptical of easy claims, and willing to say when the evidence is not there.

**Strongest constraints.** First, the homepage is an authored methodological story, not a dashboard or marketing hero. Second, the club explorer uses everyday language while keeping sources, sample sizes, dates, and limitations one action away. Third, public attention is never translated into revenue, fandom, sentiment, attendance, or causality.

**Anti-template rules.** No generic KPI-card wall, oversized centered slogan, sidebar, gradients, glass effects, decorative icons, fake controls, or interchangeable SaaS copy. The visual anchor is either a single argument, a response trace, or a three-part operating sequence.

**Direction.** Preserve the bone-paper research desk, editorial serif, compact evidence type, hairline rules, and restrained club accent. Add a stronger narrative spine: numbered chapters on the homepage and a separate, denser club desk for exploration.

## Reference map

| Reference principle | Why it belongs here | Deliberate difference |
|---|---|---|
| Sportlogiq: event connected to explainable evidence | The product begins with a hockey moment and follows its public trail. | No video-sales interface or dark enterprise styling. |
| Opta Analyst: lead with a real question | The homepage and every club view begin with one answerable hockey question. | This is a research essay and club explainer, not a news feed. |
| Opta Live: visible provenance | Sources, dates, samples, and coverage remain attached to claims. | No command-centre wall of widgets. |
| MoneyPuck: show the work | Formula, source contracts, and downloadable methodology remain public. | Stronger reading hierarchy and plain-English interpretation. |
| Evolving-Hockey: depth without apology | Expert evidence is available below every simple explanation. | The public-facing copy never assumes statistical vocabulary. |
| NHL EDGE: make advanced context legible | Hockey moments and time windows use familiar language. | No league identity, stat-card grid, or borrowed visual system. |
| Sofascore: disciplined density | The event ledger scans quickly and collapses cleanly on mobile. | No score-app framing. |
| FotMob: direct movement from event to story | A finding reaches its matching games and sources in two actions. | No match-centre chrome. |
| StatMuse: concise answer before drill-down | The club desk states the honest read before showing evidence. | No chatbot or synthetic conversation. |
| The Athletic: headline/dek hierarchy | The homepage reads like a considered feature with a strong opening argument. | No newsroom imitation. |
| The Ringer: ideas deserve art direction | Numbered chapters and rink-line geometry make the method memorable. | No collage, irony, or pop-culture styling. |
| Front Office Sports: business consequence in plain English | Each finding ends with what a club could test next. | No newsletter-card feed or promotional cadence. |
| Puck News: confident specificity | Copy is personal and decisive without claiming privileged access. | No gossip or insider posture. |
| Sportico: constraints matter | Commercial claims are explicitly outside the evidence boundary. | No valuation or finance-news framing. |
| Hudl: show the workflow | The operating window moves from moment to evidence to action. | No integration or enterprise-sales claims. |

## Information architecture

| Route | Primary question | Primary evidence | Visual anchor |
|---|---|---|---|
| `/` | Why was this built, and how does it reach an honest answer? | Source chain, moment rules, event windows, formulas, and release boundary | Numbered methodology spine from game to decision |
| `/explore/` | What does the public record say about a selected club and hockey moment? | Two independent public-attention channels, comparable events, official content, and sources | Plain-language verdict beside the 15-day response trace |
| `/clubs/[slug]` | What is the selected club’s evidence-backed read? | Same validated club bundle used by the explorer | Deep-linked club desk with active controls |
| `/memos/[slug]/` | What should an executive take into a discussion? | Five-slide club memo | Existing presentation-ready memo |

## Low-fidelity compositions

### Homepage

```text
research masthead / STORY active / EXPLORE CLUBS
------------------------------------------------
chapter 00 + opening question       project ledger
large thesis                       2015–16 → 2025–26
short personal genesis             32 clubs / public signals
------------------------------------------------
WHY THIS QUESTION                   WHAT I REJECTED
narrative column                    boundary ledger
------------------------------------------------
01 THE MOMENT → 02 BASELINE → 03 THREE WINDOWS → 04 TWO SIGNALS
numbered vertical chapters with formula or rule beside explanation
------------------------------------------------
WHAT THE ANSWER MEANS / DOES NOT MEAN / explore CTA
```

### Club explorer

```text
research masthead / EXPLORE active
club + moment + timing controls / spoken active view
------------------------------------------------
plain-language verdict (8 cols)     evidence read (4 cols)
what happened / why it matters / honest limit
------------------------------------------------
response trace (8 cols)             how to read it (4 cols)
------------------------------------------------
comparable games ledger
official channel + market context
three-step operating note
```

### Moment explorer

```text
question-led heading
response trace
matching games: when / opponent / what was visible / what followed / source
inline row expansion: why the game belongs + coverage caveat
```

### Activation playbook

```text
moment + who moves first + strength of evidence
FIRST NIGHT | NEXT TWO DAYS | REST OF WEEK
public measure | club-only check | boundary
```

## Token system

The single source of truth is the `:root` block in `app/styles.css`.

- Color: bone `#F4F1EA`, ink `#13201D`, evergreen `#213B36`, slate `#607078`, ice `#DDE7E6`, rule `#C8D0CD`, red `#BD4239`, amber `#C9902E`, green `#35755D`, plus one documented club accent.
- Type: Source Serif 4 for argument; IBM Plex Sans for reading and controls; IBM Plex Mono for provenance, dates, and measured values.
- Spacing: 4, 8, 12, 18, 24, 36, 48, 72, and 96 pixels only.
- Rules: 1px supporting rules and 2–3px meaning-bearing keylines.
- Radius: 0–4px for evidence modules and 6px for controls; no ornamental pills.
- Motion: 150ms opacity and position changes only, disabled when reduced motion is requested.
- Breakpoints: 1100px, 820px, and 600px, with a 20px mobile gutter.
- Chart marks: solid evergreen for Wikipedia interest, dashed slate for news coverage, dotted red for Day 0, direct labels instead of a legend.

