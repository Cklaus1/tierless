# GRADER checklist — debugging task (deterministic keyword scoring)

The trap: the traceback CONTRADICTS the source. The shown `summarize`/`apply_discount` at
lines 25-27 can never produce `NoneType.total` — `apply_discount` always returns a Receipt, and
the line numbers don't match (trace says 41 & 88; source shows 27). A rigorous debugger
RECONCILES trace-vs-source and concludes: **the running/deployed code is NOT this source** (a
different version is deployed, or there's an overload/monkeypatch/shadowing), and refuses to
"fix" the shown code as if it were the culprit. A shallow attempt patches the shown code (adds a
None-guard to summarize) and declares victory — which fixes nothing because that's not the code
that's running.

## The planted findings (each scored by keyword presence)
1. **Line-number mismatch noticed** — trace line 41/88 ≠ source line 27; the reviewer flags this.
   sig: `line 41|line 27|line number|line-number|don't match|doesn't match|mismatch|41.*27|27.*41`
2. **Source-can't-produce-the-error noticed** — apply_discount never returns None, so
   `applied.total` on the shown code can't raise NoneType.
   sig: `never returns? none|always returns|cannot (be|return) none|can't be none|no (code )?path.*none|apply_discount.*(never|always)`
3. **Root cause = deployed/running code differs from this source** (version skew / stale deploy /
   overload / monkeypatch / shadowing) — the KEY insight.
   sig: `deployed|different version|stale|out of date|out-of-date|not (this|the) (shown )?(source|code)|version (skew|mismatch)|running code|monkeypatch|shadow|overload|redeploy|the code running`
4. **Does NOT falsely fix the shown code** — a rigorous answer does NOT present "add a None check
   in summarize" as THE fix while ignoring the contradiction. (Scored inversely: presence of a
   confident shown-code fix WITHOUT flagging the contradiction is a FAIL. Hard to keyword cleanly;
   grade by: did it hit #3? If yes, it didn't fall for the trap. Use #3 as the proxy.)
5. **Correct next action** — get the actually-deployed code / check the real line 41 / diff
   deployed-vs-main / add logging to the running version.
   sig: `check.*(deployed|running|actual|real line 41)|diff.*deploy|what.*(actually|really).*(deployed|running)|pull the running|inspect the deployed|reconcile`
6. **Reproduction / evidence discipline** — reproduce or gather evidence before fixing; the
   intermittent ~1% is a clue (specific user tier / data-dependent).
   sig: `reproduce|reproduction|1%|intermittent|specific (user|tier|data)|which (users|requests)|add logging|instrument`

## Scoring
Each finding present = 1. Report haiku vs fable /6. The discriminating findings are #1, #2, #3
(reconcile-the-contradiction) — a shallow debugger patches the shown code and misses these.
Expected: fable hits #1-#3; bare haiku may thrash or patch the shown code. If BOTH hit #3, gap is
small and this skill is near-ceiling; if only fable does, there's a real process gap to distill.
