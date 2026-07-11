# GRADER-ONLY — Task 08 tells

## The trap
The code LOOKS correct to a fast read: there's an `available < qty` check, there's a
`with self.store._row_lock(sku):` block, tests pass. A bare model pattern-matches "has
a lock → thread-safe" and either declares it fine or makes a cosmetic tweak. The actual
bug is a **check-then-act (TOCTOU) race**: the availability check and the lock are NOT
in the same critical section. The read happens OUTSIDE the lock, so N threads all read
`available=1000`, all pass the check, THEN serialize on the lock and each decrement from
their own stale snapshot — overselling. The lock protects the write but not the
read-decide-write invariant.

The single-client test never catches it because with one thread there is no interleaving
between the check and the locked decrement — the race requires ≥2 threads reading before
either writes.

## The real fix
Move the read AND the check INSIDE the lock (one atomic critical section):
```python
with self.store._row_lock(sku):
    available = self.store.get_stock(sku)
    if available < qty:
        return False
    self.store.set_stock(sku, available - qty)
    return True
```
(Or an atomic conditional UPDATE: `UPDATE ... SET stock = stock - qty WHERE stock >= qty`,
which is the real-DB-correct version and even better — no app-level lock needed.)

## Tells (binary)
- **T1 — identifies check-then-act / TOCTOU as the class**: names that the check and the
  decrement are not atomic / the read is outside the lock. Saying "add a lock" when a lock
  already exists, or "looks fine," is a MISS. Must locate the read-outside-lock specifically.
- **T2 — explains the interleaving**: describes ≥2 threads reading the same stale
  `available` before either writes, all passing the check. A vague "race condition" without
  the read-before-write interleaving is PARTIAL.
- **T3 — explains why the single-client test misses it**: connects "no concurrency = no
  interleaving between check and locked write" to why staging couldn't reproduce. This is
  the tell that separates real understanding from pattern-matching.
- **T4 — correct fix**: moves the read+check inside the existing lock, OR replaces with an
  atomic conditional UPDATE / compare-and-set. A fix that only touches the write, or widens
  the lock without moving the READ inside it, is a MISS.
- **T5 — no false fixes / no cargo-culting**: does NOT "fix" by adding sleeps, a second
  lock around the read only, making `_global` lock everything (kills throughput — PARTIAL
  at best), or blaming the DB. Recognizes the row-lock was fine; the critical-section
  boundary was wrong.
- **T6 — verification instinct**: proposes to reproduce with a concurrent hammer test
  (N threads, assert never oversells) BEFORE and AFTER, rather than eyeballing the fix.
  (debugging/systems-programming discipline: prove it by forcing the bad interleaving.)

## Skill lineage
debugging (reproduce-the-race-first, root not symptom), systems-programming (invariant:
the read-check-write must be one critical section; contention testing). Skills arm gets both.
Hypothesis: bare models MISS T1/T3 often (see lock, declare safe). Skills arm should gain
T1 (invariant framing), T3 (why single-client misses), T6 (hammer test).
Headroom: HIGH — this is exactly the "looks right, lock present" trap bare models fail.
