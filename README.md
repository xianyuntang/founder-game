# 12 個月

A single-file, offline-capable text adventure about running a startup. Twelve rounds,
one choice per month. Every option's verdict is backed by a real failure or success
pattern distilled from 4,999 Reddit posts, and every cited case links back to its
original thread.

**Play it: https://founder-game-coral.vercel.app**

## What's in here

| Path | What it is |
|---|---|
| `index.html` | The whole game. No build step, no dependencies, no CDN. Double-click to play offline. |
| `og.png` | Social preview image (1200×630). |
| `verify_game.py` | Checks every citation in the game against the source playbooks. |
| `data/playbook.md` | 93 failure patterns across 11 chapters. |
| `data/success-playbook.md` | 35 success patterns across 4 chapters. |
| `data/upgrade-rate.json` | Per-pattern "how many went past paid_validation" rates. |

## How the data works

The playbooks were distilled from 4,999 Reddit posts (2025-01 to 2026-09) in
startup and SaaS communities, yielding 3,614 usable failure events from 2,909
distinct people. Only self-reported, software-business, review-passing events were
kept. Each pattern needs at least three non-low-trust people behind it and carries
case IDs so any claim can be traced to its source thread.

**Read the counts as relative weight, not probability.** "85 people did this" does
not mean 85% of founders fail this way. The sample is not random, the reports are
unverified and told in hindsight, and a person's stated cause is not necessarily the
real one. The success playbook needs even more care: its denominators are 5–17
people, upgrade rates cannot be compared across chapters, and survivorship bias sits
in both the numerator and the denominator. The game surfaces these caveats in the
ending screen rather than burying them here.

Low-trust sources — posts whose own text reads as AI-generated or promotional, where
the storyteller is the post author — are excluded from every count and never used as
a representative case.

## Verifying the citations

The question bank is hand-authored, so a wrong headcount, a case ID pasted from a
neighbouring pattern, or an invented founder quote would be invisible to a reader.
`verify_game.py` catches all of it:

```bash
python3 verify_game.py
```

It extracts the embedded JSON bank from `index.html` and asserts that every pattern
name, chapter, headcount and case ID matches the playbooks verbatim, that each cited
case actually lives inside the pattern it is attributed to, and that anything printed
inside 「」 is a real quote from that pattern's block. It exits non-zero on any
mismatch and ships with an assert-based `demo()` self-check (`--demo`).

The economy is checked separately, inside the page itself, so the simulation reuses
the real `settle()` instead of a drifting reimplementation:

```
open index.html#selftest
```

That run asserts the question bank's structure, that every (track, phase) pair has
enough drawable questions, that flag-gated consequence questions are reachable, and
that an all-bad run dies between month 5 and 10 while an all-good run survives.

`data/` is a snapshot of the playbooks at the time the question bank was written. If
the playbooks are regenerated, refresh the snapshot and re-run the verifier.

## Deploying

Static hosting, nothing to build:

```bash
npx vercel@latest deploy --prod --yes
```

If the deployment URL changes, update the absolute `og:image` and `twitter:image`
URLs in `index.html` — social crawlers do not resolve relative paths.

## License

Code is MIT. The playbook text summarises publicly posted Reddit content and links
back to each source thread; treat it as research notes, not as a dataset to
redistribute.
