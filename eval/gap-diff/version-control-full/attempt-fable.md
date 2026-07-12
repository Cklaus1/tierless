# Turning this working tree into commits — full walkthrough

## 0. Read the situation before touching git

There are **four logically distinct changes** tangled together in this tree, plus one landmine:

1. **A real bug fix** (security-relevant: expired tokens were accepted) — in `session.py` + one new test.
2. **A mechanical rename** `validate_token()` → `verify_token()` — spans `session.py`, `middleware.py`, `login.py`, `refresh.py` (missed!), `tests/test_session.py`, and `docs/auth.md` (missed!).
3. **A whole-file reformat** of `middleware.py` (editor ran black on save) — pure noise relative to the task.
4. **An unrelated dependency bump** (`cryptography` 41.0 → 42.0) done "while debugging".

Landmine: `scratch/debug_dump.json`, a 2MB untracked file produced while debugging *auth*. Assume it may contain live tokens, session cookies, or credentials until proven otherwise.

Critical realization: **the working tree is broken right now.** `src/api/refresh.py` still calls `validate_token()`, which no longer exists after the rename. If I committed "everything" and my test run only covered `tests/test_session.py`, CI might even pass while the refresh endpoint 500s in production. This one fact drives most of the checks below.

## 1. Triage the tree first (before any `git add`)

```bash
git status                 # confirm branch; if on main, branch NOW:
git switch -c fix/expired-token-acceptance
git fetch origin && git rebase origin/main   # start from current main
git diff                   # actually read every hunk, file by file
git diff --stat            # sanity-check the blast radius
```

### 1a. Deal with the debug dump immediately

```bash
less scratch/debug_dump.json    # or jq keys — does it contain tokens/secrets?
rm scratch/debug_dump.json      # it's untracked; deleting removes all risk of committing it
echo 'scratch/' >> .gitignore   # optional, in its own tiny commit or a housekeeping PR
```

Traps here:
- `git add .` / `git add -A` / `git commit -a` at any point would sweep this 2MB file into history **forever** (history rewrite + force-push territory to undo). So: **no blanket adds anywhere in this session.** Everything gets staged surgically.
- Because it came from debugging auth, if it *does* contain real tokens, deleting the file is not enough — **rotate/revoke those tokens**. Never committed ≠ never leaked (it sat on disk; maybe it got pasted into a ticket).
- If I `git stash` at any point, remember stash doesn't take untracked files by default (`-u` does) — another way this file silently survives or gets lost. Delete it first and the problem disappears.

### 1b. Decide the fate of each tangled change

- **Bug fix**: its own commit, **first**, because a security fix must be small, reviewable in isolation, and *cherry-pickable to release/hotfix branches without dragging the rename along*. If fix and rename are welded into one commit, every backport becomes a conflict-ridden mess.
- **Rename**: its own commit, second, and it must be **complete** (fix `refresh.py`, update `docs/auth.md`, sweep for other references).
- **Reformat of `middleware.py`**: revert it, or isolate it. Default: revert. A drive-by whole-file reformat (a) buries the one-line functional change in review noise, (b) pollutes `git blame`, (c) creates merge conflicts for anyone else touching that file. Check repo policy first: if the repo runs black in CI/pre-commit and the file was *already* black-clean, the reformat is a no-op and this is moot; if the repo is *not* black-enforced, the reformat goes in its own `style:` commit (ideally its own PR, and its hash added to `.git-blame-ignore-revs`) — or just gets dropped.
- **`requirements.txt` bump**: unrelated → **out of this PR**. First verify the fix doesn't secretly depend on cryptography 42 behavior (revert the bump locally, run the new expiry test — see §4). Assuming it doesn't:
  ```bash
  git restore requirements.txt
  ```
  If the bump is genuinely wanted, it gets its own branch/PR with its own testing — a cryptography major bump has its own risks (dropped Python versions, ABI/wheel changes) and deserves its own review and its own revert unit. Trap: smuggling a dependency upgrade inside an auth security fix means that if the *bump* breaks prod, someone reverts the *security fix* with it.

### 1c. Fix the two things the rename missed — before staging anything

```bash
# find EVERY remaining reference, not just the one I know about:
git grep -nE 'validate_token' -- '*.py' '*.md' '*.rst' '*.txt' '*.yml' '*.toml'
```

This catches:
- `src/api/refresh.py` (the known miss) — fix it.
- `docs/auth.md` code example — fix it.
- The sneaky ones a naive grep of imports misses: **string references** — `mock.patch("src.auth.session.validate_token")` in tests, `getattr(session, "validate_token")`, log messages, OpenAPI descriptions. Type checkers and tests won't reliably catch string-based patch targets; grep is the only defense.

Also ask: **is `validate_token` public API** for anything outside this repo (other services, plugins, a published package)? If yes, don't hard-rename — keep a deprecation shim:

```python
def validate_token(*args, **kwargs):
    warnings.warn("validate_token is deprecated; use verify_token", DeprecationWarning, stacklevel=2)
    return verify_token(*args, **kwargs)
```

For the rest of this walkthrough I'll assume it's internal-only and a hard rename is fine.

Also sweep the diff for debugging leftovers: `git diff | grep -nE 'breakpoint\(\)|pdb|print\(|TODO|XXX'`.

## 2. The commit plan

Three commits on the branch (plus the dep bump elsewhere):

| # | Commit | Contents |
|---|--------|----------|
| 1 | `fix(auth): reject expired tokens in token validation` | Minimal fix in `session.py` **against the old name** `validate_token`, + the new expiry test (also using the old name) |
| 2 | `refactor(auth): rename validate_token to verify_token` | `session.py` def/name, call sites in `middleware.py` (call-site hunk only), `login.py`, `refresh.py`, rename updates in `tests/test_session.py`, `docs/auth.md` example |
| 3 | *(optional)* `style: format middleware.py with black (no functional change)` | The reformat, if kept at all |

Why this order: the fix commit is the one that gets cherry-picked to `release/*`; putting it first and expressing it in terms of the code that exists on those branches (old function name) makes the cherry-pick trivially clean. The rename is pure mechanics on top.

**The subtle trap in commit 1**: the fix and the new test *currently exist in the working tree written against the new name* (`verify_token`), and in `session.py` the fix lines likely sit inside the very function whose `def` line was renamed — possibly in the same diff hunk. Hunk-level `git add -p` may not be able to separate them. That's fine: `git add -p` offers `s` (split) and, crucially, `e` (edit the hunk as a patch). For commit 1 I stage the fix lines and hand-edit out the rename — i.e., the staged patch keeps `def validate_token(` — and similarly hand-edit the new test hunk to call `validate_token`. Commit 2 then contains the rename of those same lines. If patch-editing gets fiddly, the alternative is cleaner: `git stash`, re-apply the minimal fix by hand on top of the old code, commit, `git stash pop`, resolve the (small) conflict, proceed.

## 3. Executing it

```bash
# ---- Commit 1: the bug fix ----
git add -p src/auth/session.py      # stage ONLY the expiry-fix hunks; 'e' to strip the rename
git add -p tests/test_session.py    # stage ONLY the new expiry test; 'e' to revert its name to validate_token
git diff --cached                   # READ the staged patch: it must show fix-only, old names intact
```

**Test what you're actually committing, not the working tree.** `pytest` runs against the working tree, which contains commits 2–3's changes too. To test the index exactly:

```bash
git stash push --keep-index -m "rename+format, pending"
pytest && ruff check . && mypy .    # full suite — see §4 for why "full"
git commit -m "fix(auth): reject expired tokens in token validation

Expired tokens passed validation because <root cause: e.g. exp was
compared against issued-at / naive vs aware datetime / etc>. Any
expired session token could still authenticate. Adds regression test.

Impact: <since when / which endpoints>. Candidate for backport."
git stash pop
```

```bash
# ---- Commit 2: the rename ----
git add src/auth/session.py src/api/login.py src/api/refresh.py tests/test_session.py docs/auth.md
git add -p src/auth/middleware.py   # stage ONLY the call-site hunk, not the reformat
git diff --cached                   # verify: mechanical rename only, refresh.py + docs included
git grep -n validate_token          # should now return nothing (or only the deprecation shim)
pytest && mypy .                    # again — mypy would have caught refresh.py; run it every time
git commit -m "refactor(auth): rename validate_token to verify_token

Mechanical rename, no behavior change. Updates all call sites
(middleware, login, refresh), tests, and the docs example."

# ---- Commit 3 (optional): the formatting ----
git add src/auth/middleware.py
git diff --cached -w                # with -w this should be (near-)EMPTY — proves it's format-only
git commit -m "style: format middleware.py with black (no functional change)"
# ...or instead: git restore src/auth/middleware.py   # drop the reformat entirely
```

Finally: `git status` must be **clean** (no leftover modifications, no `scratch/`), and `requirements.txt` untouched.

**Verify bisect-safety** — every commit must build and pass tests on its own, or `git bisect` and cherry-picks break later:

```bash
git rebase -i origin/main --exec 'pytest -q && mypy .'
```

If commit 1 fails in isolation (e.g., I accidentally staged a test that uses the new name), fix it now with `git rebase -i` / `edit`, not with a "fix tests" commit on top.

## 4. What I'd check before pushing — the checklist

- **Full test suite, not just `test_session.py`.** The missed `refresh.py` call site is the proof: the narrow test file passed while the app was broken. Run everything, plus lint and a type checker (`mypy`/`pyright` flags the missing-attribute call in `refresh.py` even without a test).
- **Prove the new test tests the bug**: check out the pre-fix code (`git stash` the fix or `git worktree add` at origin/main + apply only the test) and confirm the expiry test **fails** there. A regression test that passes both before and after is decoration.
- **`git grep validate_token` returns nothing** (incl. mock/patch strings, docs, comments).
- **`git diff origin/main..HEAD --stat`** — final blast radius matches expectations: no `requirements.txt`, no `scratch/`.
- **Read the full diff once more as a reviewer would** (`git diff origin/main..HEAD`), specifically hunting for secrets and debug leftovers, since this is auth code.
- **Behavioral check beyond unit tests**: actually exercise login → use expired token → refresh, locally. The refresh path had zero test coverage (that's *why* the miss survived) — consider adding a test for `refresh.py`'s auth path in commit 2 or a follow-up.
- **Rebase on latest `origin/main`** before pushing so CI runs against reality.

## 5. Review and merge

**One PR or two?** Ideal: **two** —
1. PR A: commit 1 only (the fix). Tiny, urgent, trivially reviewable, merged and deployed fast, easy to backport.
2. PR B: commits 2 (+3) (the rename/format), based on A.

Acceptable: one PR containing the clean commit sequence with a "please review commit-by-commit" note — **but only if the repo merge policy preserves commits** (merge commit or rebase-merge). **Trap: if the repo squash-merges, all this careful separation is flattened into one blob on main**, the fix becomes non-cherry-pickable without dragging the rename, and blame is polluted anyway. Under a squash policy, two PRs is not optional, it's the only way to keep the units separate.

PR hygiene:
- Description: root cause, user impact ("expired tokens were accepted since <commit/date> on <endpoints>"), how it's tested, what's deliberately excluded (dep bump, and why).
- **Security sensitivity**: this is an auth bypass. If the repo is public or the service is deployed, a PR titled "fix: expired tokens accepted" is an exploit roadmap for the window between push and deploy. Follow the org's security process — private fix branch / security advisory if one exists, at minimum coordinate merge-and-deploy so the gap is short. Also decide whether already-issued long-lived tokens need revocation/rotation now that we know expiry wasn't enforced.
- Request review from auth code owners (CODEOWNERS); wait for green CI; don't self-merge a security fix if policy requires review.
- After merge: **backport commit 1** (`git cherry-pick -x <sha>`) to supported release branches — this is exactly why it was kept rename-free; deploy; changelog/security note; open the separate `cryptography` bump PR if still wanted; consider a follow-up ticket for refresh-path test coverage and (if kept) adding the format commit to `.git-blame-ignore-revs`.

## 6. Trap summary

1. **The tree is broken right now** (`refresh.py`) — "it works on my machine" was never true; only the grep + type check + full suite catch it.
2. **`git add .` / `commit -a`** would commit the 2MB debug dump and the unrelated dep bump. Stage surgically, always read `git diff --cached`.
3. **The debug dump likely contains auth secrets** — delete it, and rotate anything it exposed; if it ever lands in a commit, you're into history-rewrite + forced rotation.
4. **Fix welded to rename = unbackportable security fix.** Split them, fix first, expressed against the old name.
5. **Hunk-splitting inside `session.py`** may need `git add -p` with `e` (patch editing) or a stash-and-redo; verify each intermediate commit independently passes (`rebase --exec`), or bisect dies later.
6. **`pytest` tests the working tree, not the index** — use `git stash --keep-index` to test exactly what commit 1 contains.
7. **Whole-file reformat** hides the real change, wrecks blame, invites conflicts — revert or isolate (+ `.git-blame-ignore-revs`).
8. **String-based references** (`mock.patch("...validate_token")`) survive both mypy and the test run — only grep finds them.
9. **Squash-merge policy silently destroys the commit split** — under squash, split into two PRs instead.
10. **Public-API rename** breaks external callers — check, and prefer a deprecation shim if anything outside the repo imports it.
11. **The dep bump might be load-bearing** — revert it *locally first* and re-run the expiry test to prove the fix doesn't depend on cryptography 42 before excluding it.
12. **Narrow test runs lie** — the untested refresh path is the lesson; add coverage there as follow-up.
13. **Disclosure window** — coordinate merge and deploy for an auth-bypass fix; don't let the PR sit public and unmerged.
