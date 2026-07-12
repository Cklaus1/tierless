# GRADER checklist — code-archaeology (12 things to investigate before the change)

1 the '2**attempt' backoff & '10*(attempt+1)' timeout are COUPLED to 3 (change breaks timing): r"backoff|2 ?\*\* ?attempt|timeout.*attempt|10 ?\* ?\(attempt|coupled|sleep.*attempt|exponential|timing.*(change|scale)"
2 'if attempt == 2' hardcodes the last-attempt (must become count-1): r"attempt == 2|== 2|last attempt|hardcoded (2|last)|count ?- ?1|final attempt|failure event.*(last|2)"
3 the redis lock TTL 300s vs total retry time (more retries can exceed lock): r"300|ttl|lock.*(expire|duration|exceed)|retry.*(time|exceed).*(lock|300)|total.*(time|duration)|lock.*(time|window)"
4 lock released even if another holder / setnx race / force path double-run: r"setnx|lock.*(race|steal|release other|not (mine|owned))|force.*(concurrent|double|race)|delete.*lock.*(other|another)|lock ownership"
5 idempotency of db.write + emit_event on retry (double event/write): r"idempoten|double (write|event|emit)|emit.*(twice|duplicate|retry)|replay|exactly.once|re.emit"
6 upstream.fetch timeout growth unbounded with more retries: r"timeout.*(grow|unbounded|large|10\*|balloon)|fetch.*(long|slow).*retry|timeout.*(scale|increase)"
7 who consumes 'account.synced' / 'sync_failed' events (downstream impact): r"consum|downstream|who (listens|handles|subscribes)|event.*(consumer|handler|contract)|emit.*(depend|downstream)"
8 version comparison semantics ('<=' skip) / stale/equal handling: r"version|<=|get_local_version|stale|equal.*version|version.*(compare|semantic|skip)"
9 what calls sync_account / callers' expectation of retry behavior: r"caller|who calls|call site|callers.*(expect|rely|depend)|call.*sync_account"
10 config source / where the new param comes from / default preserves 3: r"config|default.*3|preserve.*(3|current|behavior)|backward.?compat|where.*(value|param|setting) come|env|parameter default"
11 tests exist? characterization tests before changing: r"test|characteriz|coverage|existing test|test.*(before|first)|no tests|write.*test"
12 git history / why 3 / why these specific values (Chesterton's fence): r"git (log|blame|history)|why (3|hardcoded|these)|chesterton|reason.*(3|hardcoded|chosen)|intentional|original (author|intent|decision)"

## Scoring: each present = 1, /12. code-archaeology's whole claim is enumerating hidden
## dependencies/invariants before touching legacy code. Pure enumeration test.
