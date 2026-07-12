# Sonnet arm test — cross-family headroom & skill generalization (2026-07-12)

Motivation: our "cheap models are near-ceiling" finding rests on Haiku-4.5 being unusually strong.
The ICP runs whatever cheap model they have (possibly a different family — "sonnet" may route to a
substitute backend; can't confirm from inside, and it doesn't matter: it's a distinct arm, its
behavior is the data). Two questions: (A) does sonnet show headroom where Haiku was at ceiling?
(B) do our two validated skills close SONNET's gap (cross-family generalization)?

All deterministic keyword scoring + eye-verification. No LLM judge.

## Results

### Headroom (bare) on tasks Haiku aced
| task | haiku | sonnet | fable |
|---|---|---|---|
| threat-modeling /13 | 13 | 13 | 13 |
| adversarial-review /12 | 12 | 10 | 12 |

Sonnet is slightly WEAKER than Haiku (10 vs 12 on adversarial-review; tie on threat-modeling) but
still near-ceiling. Not a dramatically different/weaker arm — comparable cheap-model tier.

### Generalization: validated skills on the sonnet arm
| task (/checklist) | haiku bare→skill | sonnet bare→skill | fable bare |
|---|---|---|---|
| spec-review /15 | 8 → 13 | **12 → 13** | 15 (opus 12) |
| code-archaeology /12 | 9 → 12 | **12 → 11*** | 12 |

(* the 11 is a keyword artifact — sonnet+skill dropped only the unrelated "idempotency" item; on the
three constant-coupling items it targets, sonnet was already 12/12 bare. Effectively ceiling.)

## Interpretation — this is the important finding

**Sonnet was already at/near ceiling on BOTH validated-skill tasks bare (spec-review 12/15,
code-archaeology 12/12).** So the skills had almost no gap to close for sonnet — spec-review nudged
12→13, constant-coupling had nothing to add. The Haiku gaps (8→13, 9→12) did NOT reproduce on sonnet.

Two readings, both real:
1. **The gap is model-specific, not universal.** Haiku-4.5 happens to miss disguised constants and
   unstated design assumptions; sonnet happens to catch them bare. A skill's value depends on WHICH
   cheap model you run — it helps the model that has that specific blind spot, and is inert for one
   that doesn't. This complicates the product claim: "skills close the gap" is true per-(model,skill)
   pair, not universally.
2. **Testing a second family did NOT reveal more headroom — it revealed LESS.** The hypothesis that a
   different family would be "further diff from Fable" was not supported here: sonnet was comparable
   to Haiku, and on the two derive-the-non-obvious tasks it was actually STRONGER than Haiku (no gap).

## Consequence for the method and the product
- **Skills must be validated per target model, not once.** A skill derived from a Haiku-vs-Fable gap
  is validated FOR HAIKU. It may be inert on Sonnet/Qwen/Llama. The gap-diff cycle should be run with
  the ACTUAL deployment model as the cheap arm, or the "it works" claim doesn't transfer.
- **The honest product framing tightens further:** not "these skills make cheap models match frontier"
  but "these skills close the SPECIFIC blind spots of the SPECIFIC model you run — measure yours."
  The method (gap-diff + deterministic scoring) is the durable asset; any given distilled skill is
  only validated for the model it was distilled against.
- N=1 per cell — directional. A real cross-family study needs N=3 and genuinely weaker models
  (small local 3-7B, the actual cost-driven ICP target) where the gap is likely largest.

## Biggest open question this surfaces
We've been measuring against strong cheap models (Haiku, Sonnet) that are near-ceiling. The models
where skills would plausibly show the LARGEST, most-generalizable gap are the small local models an
ICP actually reaches for to cut cost (Qwen-7B-class, Llama-8B). Those aren't in this gateway. Until
tested there, "skills close the cheap→frontier gap" is demonstrated only for the narrow band of
already-strong cheap models — where the gap is smallest. That's the most important caveat in the
whole eval.
