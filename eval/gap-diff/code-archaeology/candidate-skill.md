---
name: constant-coupling
description: Constant-coupling skill — before changing a hardcoded constant, find every DISGUISED copy of it (algebraic aliases, scaling coefficients, coupled constants, external contracts) by its consequence, not its spelling
metadata:
  type: user
---

# Constant Coupling — A Hardcoded Constant Is Rarely Defined Once

## Why

Asked to make a hardcoded value configurable (a retry count, a batch size, a timeout, a limit),
a model audits the code's *named* concerns — the lock, the error handling, the data flow — and
changes the literal. It misses the places where the constant exists **without its digits appearing**:
an `attempt == 2` that is really `count - 1`, a `timeout = 10 * (attempt + 1)` whose ceiling is an
accident of the count, a neighboring TTL sized to stay consistent with it. These disguised copies
don't change when you change the literal, so they break silently — and they are usually the *actual*
bug the change introduces. This skill installs the discipline that finds them: derived empirically
as the exact gap between a cheap and a frontier review of this task (see eval/gap-diff/code-archaeology/).

## The Rule

**A hardcoded constant is rarely defined once. Before changing it, assume it has been copied —
as an off-by-one comparison, a scaling coefficient, a coupled constant, and an external contract —
and find each copy by its CONSEQUENCE, not its spelling.**

## The Five Hunts

Run all five before touching the constant. Call the constant N.

### 1. Algebraic aliases — the off-by-one shadows
Grep the literal, then grep its neighbors (N−1, N+1) and every comparison against the loop/index
variable. Any expression that is currently correct *only because the loop runs exactly N times* —
`i == N-1`, `count == max`, `attempt == 2` — is a second declaration of N in disguise. Test each
boundary comparison: **"Is this correct only because N is what it is? Then it's a copy of N."** It
must change in lockstep.

### 2. Trace the induction variable into every expression it feeds
List every place the loop/index variable is *read*, not just where it's *bounded*. For each use,
write its value at the final iteration as a function of N, and its cumulative total across the loop.
A counter that leaks into a timeout, sleep, buffer size, or allocation is a **scaling coupling** the
loop bound hides — its ceiling is an accident of N. (This is how `timeout = 10*(attempt+1)`, fine at
N=3, becomes 100s at N=10.)

### 3. Closed-form the latent invariants; solve for the break point
Where two constants silently depend on each other (a timeout that must exceed a runtime, a TTL that
must outlast the work it guards, a budget sized for K× traffic), write the worst case as a formula
in N and solve for the exact N where the relationship inverts. Don't reason "that's plenty of
headroom" — compute `worst_case(N)` and find where it breaks. The invisible coupling becomes a hard
number ("breaks at N=7").

### 4. Provenance — which coupled constants are external contracts?
For each constant entangled with the one you're changing, ask: was this value picked arbitrarily, or
negotiated with a party *outside this function*? A 30s max may be an upstream load balancer's cutoff;
a 300s TTL may be a downstream SLA. Chesterton's fence applied to the *value*, not the mechanism:
treat each coupled constant as a possible contract boundary until confirmed arbitrary. Scaling a
self-chosen number is safe; scaling a negotiated one needs the other party's sign-off.

### 5. Substitute degenerate and extreme values through the WHOLE function
Run N=0, N=1, and N=large through *every* expression found in hunts 1–2 and read the behavior. This
catches disguised couplings behaviorally when static reading misses them: N=10 through `attempt == 2`
fires a false failure event then succeeds; N=0 is a silent no-op with no event. Boundary substitution
turns "looks fine" into an observable wrong outcome — it's the backstop that catches what hunts 1–2
miss.

## How to Apply

1. Identify the constant N you're about to make configurable.
2. Run the five hunts; for each hit, record: the disguised location, why it's a copy of N, and what
   it must become (e.g. `attempt == 2` → `attempt == retries - 1`).
3. List which coupled constants are external contracts (hunt 4) — those block the change until confirmed.
4. Only then make the change, updating every copy in lockstep.

## Anti-Patterns (gaming behaviors)

- Grepping only the literal digits and declaring the constant "used in one place"
- Reading a boundary comparison (`attempt == 2`) as an unrelated magic number instead of a copy of N
- "That timeout/TTL has plenty of headroom" with no closed-form worst-case in N
- Treating every constant as internal and freely tunable (missing the external-contract ones)
- Auditing the code's named concerns (the lock, the retries) but never the *number's footprint*

## Verification

Done means: every algebraic alias of N found and slated to change in lockstep; every use of the
induction variable bounded as f(N); every latent invariant solved for its break-point N; every
coupled constant classified arbitrary-vs-contract; and N=0/1/large substituted through the whole
function. A change that updated only the literal is incomplete.

## Provenance
Derived by gap-diff (eval/gap-diff/code-archaeology/): these five hunts are the distilled PROCESS
deltas between a Haiku review (found the 9 obvious concerns, missed the 3 disguised couplings) and a
Fable review (found all 12) of the same "make the retry count configurable" task. Through-line:
**find the constant by its consequence, not its spelling.** A focused companion to code-archaeology.
