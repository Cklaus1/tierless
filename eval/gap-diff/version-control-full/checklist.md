# GRADER checklist — version-control (14 items; the traps are the discriminators)

The scenario has intentional traps. A shallow answer says "commit it and open a PR." A disciplined
answer separates concerns into atomic commits AND catches the specific traps planted below.

1 SEPARATE the tangled changes into atomic commits (not one blob): r"atomic|separate commit|one (change|concern|thing) per commit|split.*commit|distinct commits|multiple commits|break.*into commits"
2 the BUGFIX (expired-token accept) is its own commit, ideally FIRST: r"bug.?fix.*(commit|separate|first|own)|expir.*token.*(commit|first|separate)|fix.*(before|separate from).*(rename|refactor)|behavior change.*separate"
3 the RENAME is a separate commit from the bugfix (behavior vs refactor): r"rename.*(separate|own commit|different commit)|refactor.*(separate|not.*(bug|behavior))|keep.*rename.*apart|rename.*vs.*(bug|fix)"
4 THE MISSED CALL SITE — refresh.py still calls validate_token() → rename is incomplete/broken: r"refresh\.py|missed.*call|still calls validate_token|incomplete rename|stale (call|reference)|grep.*(callers|call site|old name)|find all (callers|usages|references)|one.*you missed"
5 the DOCS example (docs/auth.md) also references the old name → update or it's stale: r"docs?/auth|documentation.*(update|stale|old name)|code example.*(doc|update)|doc.*(validate_token|old name)|update the docs"
6 the black REFORMAT in middleware.py should be a SEPARATE commit (clean blame/diff): r"reformat|black|formatting.*(separate|own commit|noise)|format.*(commit|apart)|whitespace.*separate|style.*separate commit|blame"
7 the cryptography BUMP (requirements.txt) is UNRELATED → separate commit (or revert): r"crypto.*(separate|unrelated|own commit|revert)|dependency (bump|upgrade).*(separate|unrelated)|requirements.*(separate|unrelated)|41.*42.*(separate|unrelated)|unrelated.*(bump|upgrade|dep)"
8 the scratch/debug_dump.json must NOT be committed (2MB junk / gitignore): r"debug_dump|scratch.*(not commit|gitignore|remove|exclude|delete)|don.t commit.*(scratch|dump|json)|2 ?mb|junk|artifact.*(not commit|ignore)|\.gitignore"
9 verify each commit is GREEN / tests pass before committing (bisectability): r"tests? pass|green.*commit|each commit.*(compil|work|test|green)|run.*test.*before commit|bisect|working state.*commit"
10 commit MESSAGE quality — explain the why, esp. the bugfix: r"commit message|message.*(why|explain|describe)|why.*(not|beyond).*(what|diff)|good message|meaningful message|reference.*(issue|why)"
11 stage DELIBERATELY (git add -p / per-file), since files mix concerns: r"add -p|add --patch|stage.*(deliberate|selective|hunk|per.file|carefully)|partial.*(stage|commit)|split.*(file|hunk)|interactive.*(add|stage)|middleware.*two commits"
12 the rename should update ALL sites atomically (grep old name → zero left): r"grep.*validate_token|all (call sites|usages|references).*(update|atomic)|zero.*(stale|remaining|left)|search.*old name|rg |ripgrep|find.*validate_token"
13 review/PR sizing — keep the PR reviewable / order commits for review: r"PR|pull request|review.*(size|small|order)|reviewable|stack.*commit|small.*PR|reviewer"
14 the file mixing bugfix+rename (session.py) needs care — two concerns in one file: r"session\.py.*(two|both|mix|split|separate)|same file.*two (concern|change)|split.*session|one file.*(bug|rename).*(and|both)"

## Scoring: each present = 1, /14. Discriminating traps: #4 (missed refresh.py call), #5 (stale docs),
## #6 (reformat noise), #7 (unrelated dep bump), #8 (junk file), #11/#12 (selective staging + grep the
## rename). Hypothesis: bare model says "split into a few commits, open PR" and MISSES the specific
## planted traps (esp. #4 the missed call site — the incomplete-rename bug); a rigorous answer catches
## them by actually reading the status and grepping. If Haiku ~= Fable, ceiling; if Fable catches the
## traps Haiku misses, real distillable gap.
