---
name: shell-scripting
description: Shell-scripting skill — discipline for bash/POSIX automation: strict mode, quoting, idempotency, and knowing when to stop using shell
metadata:
  type: user
---

# Shell Scripting — Unix Automation Skill

## Why

Shell is the language where the default behavior is wrong: unset variables expand to nothing, failed commands are ignored, unquoted expansions split on spaces, and a script that "worked" has silently done half its job. Smaller models know the commands but skip the discipline — and shell punishes skipped discipline more than any other language, because the failure mode of a bad script is `rm`-ing the wrong thing on a production box. This skill is the set of habits that make shell scripts safe to run twice, on a machine you care about.

## The Rule

**Every script starts with strict mode, quotes every expansion, and is safe to re-run.** A script that can't be run twice is a script that can't be recovered when it fails halfway.

## How to Apply

### 1. The non-negotiable header

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- Exceptions to `-e` are per-command (`cmd || true`), explicit, with a reason
- `trap 'cleanup' EXIT` for anything that makes temp files, takes locks, or starts background jobs

### 2. Quoting is correctness

- **Every** expansion quoted: `"$var"`, `"$(cmd)"`, `"$@"` — no exceptions until you can articulate why word-splitting is wanted
- Filenames are hostile: `find -print0 | xargs -0`, `--` before positional args, never parse `ls`
- shellcheck in CI — it catches the quoting bug class mechanically and non-negotiably

### 3. Idempotency and safe re-runs

- `mkdir -p`, `ln -sfn`, guarded appends (`grep -q line file || echo line >> file`) — every step either converges or skips
- Destructive steps check before acting; anything that deletes takes a `--dry-run` flag and prints what it *would* do
- Long scripts checkpoint: failed at step 7 means resumable at step 7, not restart-and-hope

### 4. Fail loudly, log usefully

- Errors to stderr with context: `echo "error: expected $f to exist (did step 3 run?)" >&2`
- Print what the script is doing at each major step — silent scripts are undebuggable at 3am
- Validate inputs and preconditions *first* (args present, commands available, paths exist), die immediately with usage text — not at minute 20

### 5. Know when shell is the wrong tool

Shell excels at plumbing: sequencing commands, moving files, gluing tools. Escalate to Python (or similar) the moment you have: nested data structures, arithmetic beyond counters, error handling with more than two branches, or anything parsing JSON more complex than one `jq` expression. A 300-line bash script is a Python script that hasn't admitted it yet.

### 6. Portability is a decision, not an accident

Decide the target (bash-on-Linux vs POSIX sh, stated in the shebang) — for scripts targeting more than one OS, defer to the **cross-platform** skill.

### 7. Scripts that touch production

A script destined for a prod box is an infrastructure change: it lives in the repo and follows the **infra-ops** discipline (reviewed, reversible, not pasted into an SSH session).

## Anti-Patterns

- Adding `|| true` wholesale to silence `-e` — strict mode kept in the header, defeated in every line
- shellcheck disable comments sprinkled without justification — the checker is "clean" because it was told not to look
- Parsing `ls` output; using `which` (use `command -v`); useless `cat | grep`
- `cd` without checking success (everything after runs in the wrong directory — `cd foo || exit`)
- Backgrounding jobs and exiting without `wait` (the script "finished"; the work didn't)
- sudo inside the script instead of requiring the script be run with privilege (audit trail and password prompts mid-run)
- 40 lines of sed/awk where the honest answer was `jq` or a Python script

## Verification

Pre-ship checklist — every box answered with evidence, not "yes":
- [ ] Strict mode header present?
- [ ] shellcheck clean — output pasted?
- [ ] Script run twice — second run's output shown (proves idempotency)?
- [ ] Every destructive step has `--dry-run`?
- [ ] Inputs and preconditions validated first, with usage text on failure?

Verdict is PASS/FAIL; an unchecked box is a FAIL.
