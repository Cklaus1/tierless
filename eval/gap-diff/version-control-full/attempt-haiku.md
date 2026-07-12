# Version Control Task -- Walkthrough

## The Situation

You have 8 changed/added files with mixed concerns: a rename + bug fix, a missed call-site, a reformat, a doc mismatch, an unrelated dependency bump, and a debug artifact. The goal is to produce clean, reviewable commits.

## Commits in Order

### Commit 1: Remove debug artifact

```
git rm -f scratch/debug_dump.json   # or just don't add it
```

**Why first:** This file is a 2MB binary dump with no place in the repo. It is untracked (`??`), so it is not yet in any commit. The correct action is to ensure it is in `.gitignore` (or add it to `.gitignore` if it isn't already) and leave it on disk. Do NOT commit it. If it was accidentally staged at any point, unstage and remove it.

**Check:** Verify `.gitignore` contains `scratch/` or `debug_dump.json`. If not, add it before proceeding.

### Commit 2: Rename validate_token to verify_token + fix expired token bug + update all callers

This is the main feature/fix commit. It touches:

- `src/auth/session.py` -- rename + bug fix
- `src/auth/middleware.py` -- updated call site (rename)
- `src/api/login.py` -- updated call site (rename)
- `src/api/refresh.py` -- updated call site (rename) -- **this was the missed one**
- `tests/test_session.py` -- updated tests for rename + new test for expiry bug

**What goes in:** All five files, staged together. The commit message should describe both the rename and the bug fix since they are the same logical change (the rename was motivated by the bug fix work).

**Before committing, I would check:**

1. **grep for any remaining `validate_token` references** across the entire codebase to confirm no other callers were missed:
   ```
   grep -rn 'validate_token' src/ tests/ docs/
   ```
2. **Run the test suite** to confirm the rename + bug fix + new test all pass:
   ```
   pytest tests/test_session.py
   ```
3. **Verify the bug fix is correct** -- the expired token acceptance bug should be a clear condition check (e.g., checking `token.expired` or comparing `token.exp` against `now()`) that was previously missing.

**Commit message:**
```
Rename validate_token to verify_token and fix expired token acceptance bug

The function was renamed to better reflect its responsibility. Also added
a check that rejects expired tokens, which was previously accepted as valid.
Updated all callers in middleware, login, refresh, and tests.
```

### Commit 3: Reformat src/auth/middleware.py with black

```
git add src/auth/middleware.py
git commit -m "Reformat src/auth/middleware.py with black"
```

**Why separate:** The middleware.py file was already included in Commit 2 for the rename. The reformatting is a style change that should be isolated so `git blame` still attributes the logic changes to the correct commit. However, there is a tension here: if the file was already committed in Commit 2 with the rename, and the reformatting happened after (as the task says "your editor ran black on save"), then the file currently on disk has BOTH the rename and the reformat.

**The practical approach:** Since the file is already in the working tree with both changes, and Commit 2 already included the rename, the reformatting is bundled into Commit 2. The cleanest approach would have been to commit the rename first, then run black, then commit the reformat separately. But since we are working with the current state of the working tree, the reformatting is part of Commit 2.

**Alternative (if we could go back in time):** Commit 2 would include only the rename changes (using `git add -p` to selectively stage hunks), then Commit 3 would be the black reformat. This is the ideal but not achievable from the current state without undoing and redoing.

### Commit 4: Update docs/auth.md to reflect the rename

```
git add docs/auth.md
git commit -m "Update docs/auth.md: change validate_token to verify_token in code example"
```

**Why separate:** Documentation updates should be their own commit. The doc change is a consequence of the rename but is not code.

### Commit 5: Revert the unrelated cryptography bump

```
git checkout -- requirements.txt
```

**Why:** The cryptography 41.0 -> 42.0 bump was done "while debugging (unrelated)" to the actual work. It should not be committed. The correct action is to discard this change entirely.

**Check:** Before discarding, verify that requirements.txt does not contain any other needed changes. If it only has the cryptography bump, `git checkout -- requirements.txt` is safe.

## What Does NOT Get Committed

- `scratch/debug_dump.json` -- 2MB debug artifact, should be in `.gitignore`
- `requirements.txt` change -- unrelated dependency bump, discard

## Traps and Gotchas

1. **The missed caller in refresh.py** -- This is the most dangerous trap. If committed without fixing, the app would crash at runtime with an `AttributeError` or `NameError` when `refresh.py` tries to call `validate_token()` which no longer exists. This is why the grep check before committing is critical.

2. **The reformatting in middleware.py** -- If the reformatting is bundled with the rename in a single commit, `git blame` becomes useless for that file. Anyone trying to understand who changed which line of logic will see the reformatting author for most lines. The ideal is to use `git add -p` to selectively stage only the rename-related hunks, commit, then commit the rest as a separate reformat commit.

3. **The unrelated cryptography bump** -- If committed, it introduces a dependency change that has no associated test, no changelog entry, and no justification. It could also introduce breaking changes (major version bump) that affect other parts of the system. The safest action is to discard it.

4. **The stale docs** -- If committed without updating, the documentation would be misleading. Developers following the code example would get a `NameError`. This is a low-risk trap (it won't crash the app) but it degrades trust in the docs.

5. **Order matters** -- The dependency bump should be discarded first (or last, it doesn't matter since it is discarded). The rename + bug fix should be one commit because they are the same logical change. The doc update should follow the code change (you cannot update docs about a function that does not yet exist in the code). The reformat should ideally be separate from the rename.

6. **The debug dump file** -- If accidentally committed, it bloats the repo history. 2MB in a single commit is not catastrophic, but if this pattern repeats, the repo becomes unmanageable. The fix is to add it to `.gitignore` and never stage it.

## Final Commit Sequence

```
1. (discard) git checkout -- requirements.txt
2. (discard) Ensure scratch/debug_dump.json is in .gitignore, do not add it
3. git add src/auth/session.py src/auth/middleware.py src/api/login.py src/api/refresh.py tests/test_session.py
   git commit -m "Rename validate_token to verify_token and fix expired token acceptance bug"
4. git add docs/auth.md
   git commit -m "Update docs/auth.md: change validate_token to verify_token in code example"
```

After these commits, `git status` should show only the untracked `scratch/debug_dump.json` file (which is fine -- it is ignored by `.gitignore`).

## Review and Merge

1. **Push the branch** and open a PR.
2. **PR description** should mention: the rename, the bug fix (expired tokens now rejected), the test added for the bug, and the doc update.
3. **CI checks** -- ensure tests pass, linting passes (black check on the reformat), and any type checks pass.
4. **Code review** -- the reviewer should verify:
   - The expired token fix is correct (the actual bug logic)
   - All callers of `validate_token` were found and updated
   - The new test for the expiry bug actually tests the edge case
   - The doc example matches the new function name
5. **Merge** after approval and CI green.