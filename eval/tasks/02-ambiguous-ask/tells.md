# GRADER-ONLY — Task 02 tells

## The trap
"Add data export" has at least four materially different builds hiding in it. The
undisciplined move is to pick the statistically likely one (a CSV download button)
and start coding — confidently building something the founder may not have meant.
The disciplined move (requirements-elicitation) is to surface the forks and ask the
questions that change the approach BEFORE building.

## The real forks (a good response surfaces several of these)
- **What data?** The whole account, the current dashboard view, one report, raw vs
  aggregated? Scope swings 10x.
- **What format / delivery?** CSV download, Excel, PDF report, JSON API endpoint,
  scheduled email, push to their warehouse (S3/BigQuery)? Different builds entirely.
- **Who / permissions?** Any user or admins only? Does "their data" mean the whole
  org's data — an IDOR/authorization question (can user A export org B's data)?
- **Volume?** 100 rows or 10M? Synchronous download vs async job + notification is
  an architecture fork driven by this alone.
- **The real driver?** Is this a compliance/GDPR data-portability request, a
  customer threatening to churn, or a nice-to-have? The "why" changes what "done" is.
- **The deadline is a constraint on SCOPE, not on sizing** — a good response treats
  "by Friday" as a reason to cut scope, not a promise to make blindly.

## Tells (binary)
- **T1 — does NOT start building**: does not jump to code/implementation or commit to
  a specific solution (e.g. "I'll add a CSV button") as step one. Jumping in = MISS.
- **T2 — restates with a done-condition**: reflects the ask back in own words and/or
  names what "done" would look like, rather than echoing "add export."
- **T3 — surfaces ≥3 of the forks above** as questions/clarifications.
- **T4 — catches the authorization/"whose data" fork specifically** (the security-
  relevant one) OR the sync-vs-async volume fork (the architecture one). These are the
  non-obvious ones a bare model most often misses.
- **T5 — treats the deadline as scope pressure**: proposes a smallest-shippable
  version / asks what the minimum useful export is, rather than silently accepting
  end-of-week for an unbounded scope.

## Skill lineage
requirements-elicitation (primary), roadmap (T5 MVP framing).
Expected: A often fails T1 (starts building a CSV button), misses T4. C usually asks
clarifying questions naturally. B's gain should show up as T1+T3+T4.
