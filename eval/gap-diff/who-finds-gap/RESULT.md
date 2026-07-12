# Who can find the gap? (2026-07-12)

The question: does the gap-diff method need a FRONTIER model to do the diff-analysis (see what the
strong model caught and distill the discipline), or can a CHEAP model do it given the two attempts?

## Setup
Took a cycle with KNOWN ground truth: constant-coupling. Opus originally analyzed (bare-Haiku
attempt, Fable attempt) and produced 5 validated hunts — the ones that, distilled into a skill,
moved Haiku 9/12 → 12/12. Now gave the SAME two attempts to Haiku and Sonnet as the diff-analyst,
and scored how many of the 5 ground-truth hunts each recovered.

## Result (keyword score, then eye-corrected)
Keyword score said Haiku 2/5, Sonnet 2/5 — but eye-verification found the hunt-#1 hits were FALSE
POSITIVES (regex matched the word "aliased" in an unrelated exception-handling discipline). True
recovery of the crux discipline:

| discipline | Opus (original) | Haiku analyst | Sonnet analyst |
|---|---|---|---|
| #1 the disguised constant (`attempt==2` = a copy of N) | ✓ derived | ✗ never mentioned | ~ *noticed Fable found it, did NOT distill it as a discipline* |
| the other 4 hunts | ✓ | partial/different | partial/different |

Both cheap models produced 5 plausible-but-DIFFERENT disciplines (exception-clause enumeration,
caller mapping, deployment story…) — reasonable review advice, but **NOT the load-bearing insight.**
The one catch that made constant-coupling a validated skill — recognizing that `if attempt == 2` is
a disguised second copy of the retry count, the actual bug the change introduces — was distilled by
NEITHER cheap model. Sonnet *recognized it in Fable's text* but couldn't abstract it into a
repeatable process; Haiku didn't see it at all.

## The finding — you need the frontier model to SEE the gap
Extracting the right discipline from (weak attempt, strong attempt) is itself a
**derive-the-non-obvious** act — the exact class cheap models are weakest at (LESSONS #20). So:

- The frontier model is required not just to PRODUCE the strong example, but to ANALYZE it — to see
  which of its many catches is the load-bearing, generalizable one and phrase it as a discipline.
- A cheap model given both attempts produces plausible-but-wrong distillations. It can RECOGNIZE a
  named insight (Sonnet did) but not DERIVE it. Recognition ≠ derivation.

## Consequence for the method and the product (important)
This bounds the self-improvement loop. The gap-diff method is NOT cheaply self-serve:
- You CANNOT hand a cheap model a pile of (weak, strong) attempt pairs and have it distill its own
  skills correctly — it will miss the non-obvious disciplines, which are exactly the valuable ones.
- The frontier model is a REQUIRED, expensive ingredient in the DISTILLATION step (not just the
  example-generation step). "Fable-in-the-loop" is not optional for building blind-spot skills.
- BUT: once distilled by the frontier model, the skill is cheap to APPLY (Haiku+skill ran the 5 hunts
  fine — 9→12). So the economics are: expensive to MINT a skill (needs frontier analysis), cheap to
  USE it. That's a reasonable product shape — distill centrally with a strong model, ship cheap skills
  to users — but it kills the "cheap models bootstrap themselves from examples" story.

## Caveat
N=1 per analyst, one task. Directional. And keyword scoring misfired here (false positive on the crux
hunt) — only eye-verification caught that the cheap models missed it. Reinforces: never trust the
keyword total without reading the output (LESSONS #18).
