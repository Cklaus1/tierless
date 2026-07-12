# Enumeration-skill deterministic cycles (2026-07-12)

Test of the hypothesis from the triage: "skills help on enumeration-under-horizon tasks."
Ran the FULL deterministic cycle (many-item task + objective keyword checklist, Haiku-bare vs
Fable, grep-scored, eye-verified) on 5 enumeration-shaped skills, plus 2 from the prior batch.

## Results (deterministic, all eye-verified where a gap appeared)

| skill | Haiku | Fable | gap | at ceiling? |
|---|---|---|---|---|
| debugging | 5/5* | 5/5 | 0 | yes |
| api-design | 8/8 | 8/8 | 0 | yes |
| security-review | 6/7 | 7/7 | ~0 | yes (red-herring only) |
| adversarial-review | 12/12 | 12/12 | 0 | yes |
| qa-testing | 11/12 | 12/12 | ~0 | yes |
| threat-modeling | 13/13 | 13/13 | 0 | yes |
| ui-design | 12/12 | 12/12 | 0 | yes |
| **code-archaeology** | **9/12** | **12/12** | **+3** | **NO — real gap** |
| **spec-review** (prior) | **8/15** | **~14/15** | **+6** | **NO — real gap** |
| build-loop (prior, process) | 0.23 | 0.87 | +0.64 | NO — real gap |

(* debugging Haiku scored 4/5 by keyword but reached the discriminating insight; true ~5/5.)

## The refined criterion (this is the finding)

"Enumeration-shaped" was TOO COARSE. threat-modeling, adversarial-review, qa-testing, ui-design
are all enumeration tasks — and all at CEILING. code-archaeology and spec-review are also
enumeration — and both show a REAL gap. The difference:

**Skills help where the items to enumerate are NON-OBVIOUS and must be DERIVED; they do NOT help
where the items are a STANDARD CHECKLIST the model already has memorized.**

- STANDARD CHECKLIST (ceiling): STRIDE threats (threat-modeling), common code bugs
  (adversarial-review), boundary/error test cases (qa-testing), a11y/state checklist (ui-design),
  payments-API disciplines (api-design). A strong small model has these memorized — it enumerates
  them fine unprompted.
- NON-OBVIOUS / DERIVED (real gap): hidden couplings in unfamiliar legacy code (code-archaeology —
  the `if attempt==2` disguised-constant, the timeout that scales with retry count), and unstated
  assumptions in a design doc that must be traced, not recalled (spec-review — dual-write ordering,
  correlated-reconnect, dependency-own-failure). These require a DISCIPLINE to derive, which is
  exactly what a process skill installs.

The code-archaeology proof: bare Haiku found the 9 obvious things (the lock, idempotency, version
semantics) but MISSED the 3 that require tracing THIS code's specific hidden structure — Fable
caught all 3. Verified by eye: the `attempt==2` disguised-copy is the actual bug the requested
change would introduce, and Haiku never saw it.

## Implication for the library

Validated real gaps (skills worth their place): **build-loop, spec-review, code-archaeology** —
all "derive the non-obvious under a horizon" skills. Presumptive ceiling (skill ≈ documentation the
model doesn't need): the standard-checklist domains — debugging, api-design, security-review,
adversarial-review, qa-testing, threat-modeling, ui-design.

This does NOT mean the checklist skills are worthless — they may still help a WEAKER model than
Haiku-4.5, enforce consistency, or matter on harder instances. But on the current cheap-model bar,
their measured gap is ~0, so they are not where the leverage is. The leverage is the derive-the-
non-obvious skills.

## Method note
All scoring deterministic (keyword grep) + eye-verification of every non-zero gap. No LLM judge
was trusted (LESSONS #18). The one gap found (code-archaeology) was confirmed by reading the actual
missed items, not by a score alone.
