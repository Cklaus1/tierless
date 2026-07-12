# Review: calculator DSL parser/evaluator

Verdict up front: this is not shippable. Two of the four advertised features (variables, comparisons) do not exist, the parser silently accepts malformed input instead of rejecting it, and the test suite is three happy-path asserts that never touch `-`, `/`, variables, comparisons, or a single error case. Details below, grouped by correctness, language design, and testing, then a ship checklist.

## A. Correctness bugs

### A1. Variables are completely broken — `env` is never used
`factor` wraps every non-paren token as `('lit', t)`, and `evaluate` does `float(node[1])` for every `lit`. The `env` parameter is threaded through `evaluate` but never read. So:

- `evaluate(parse(['x']), {'x': 5})` raises `ValueError: could not convert string to float: 'x'`.
- There is no distinction between NUMBER and NAME anywhere — the grammar comment promises both, the code implements only numbers.
- Consequently there is also no defined behavior for an *undefined* variable (should be a clean "undefined name 'x'" error, not a float-conversion crash).

This is a headline feature of the DSL and it does not work at all.

### A2. Comparisons (`<`) are not implemented
The grammar comment lists `expr '<' expr`, but no code handles `<`. Worse, it doesn't even error: for `['a','<','b']`, `expr` parses `a`, sees `<` (not in `('+','-')`), and returns — the `< b` part is **silently discarded** (see A3). `evaluate` has no `<` branch either. The second headline feature is missing, and its absence is invisible to callers.

### A3. Trailing input is silently ignored — no end-of-input check
`parse` returns `expr(0)[0]` and throws away the final index. Anything left over after the first parsable expression is dropped without error:

- `parse(['1','2'])` → `1` (the `2` vanishes)
- `parse(['1','+','2',')'])` → `3`, stray `)` ignored
- `parse(['1','<','2'])` → `1` (per A2)
- `parse(['1','*','-','2'])` → evaluates `1 * '-'` and drops the `2`

A parser that accepts garbage and returns a plausible-looking answer is worse than one that crashes. Required fix: after `expr(0)`, assert `i == len(tokens)` and raise a syntax error otherwise.

### A4. Closing paren is never verified
In `factor`, after parsing the inner expression the code does `return val, i+1  # consume ')'` — it increments past whatever is there **without checking it is `')'`**:

- `parse(['(', '1', '+', '2'])` — missing `)`, accepted silently (the phantom index past the end is never dereferenced).
- `parse(['(', '1', '+', '2', '3'])` — the `3` is "consumed" as if it were `)`.
- `(1+2]`-style mismatches are accepted.

Must check `tokens[i] == ')'` and raise otherwise.

### A5. No token validation — any junk becomes a "literal"
`factor` treats every token that isn't `'('` as a literal. So `)`, `<`, `,`, `**`, empty string, etc. all parse into `('lit', ...)` nodes and only blow up (or don't — see A9) at evaluation time, far from the source of the error, as an unhelpful `ValueError` from `float()`. Examples:

- `parse(['(' , ')'])` → the `)` becomes a literal; empty parens "parse".
- A leading operator: `parse(['+','1'])` → `('lit','+')` and the `1` is dropped.

Token classification (number vs name vs operator vs paren) has to happen in a lexer or at least in `factor`.

### A6. Unary minus / negative numbers unsupported (and fail confusingly)
`['-','3']` parses as literal `'-'` (then `3` is dropped per A3) and crashes in `evaluate`. `['1','*','-','2']` likewise. Either support unary `-` (standard for a calculator) or reject it with a clear syntax error. Currently it does neither.

### A7. Out-of-range crashes instead of syntax errors
- `parse([])` → `IndexError` in `factor(0)`.
- `parse(['1','+'])` (trailing operator) → `IndexError` in `factor(2)`.

These should be reported as syntax errors ("unexpected end of input"), not raw `IndexError` with no message about position or token.

### A8. `evaluate` silently returns `None` for unknown operators
There is no `else: raise` after the four `if op ==` branches. Any node whose op isn't `+ - * /` (e.g., a future `<` node, or a corrupted AST) makes `evaluate` fall off the end and return `None`, which then poisons arithmetic upstream (`TypeError` somewhere else) or gets returned to the caller as a "result". Always end dispatch chains with an explicit error.

### A9. `evaluate` doesn't check the node tag
It checks `node[0] == 'lit'` but then unpacks `node[1..3]` for *anything* else — it never verifies `node[0] == 'bin'`. Malformed nodes produce arbitrary unpacking errors rather than a clear "unknown node type".

### A10. Division by zero is undefined behavior
`1/0` raises a raw `ZeroDivisionError`. For a shipped DSL you must decide and document: raise a DSL-level evaluation error, return inf/NaN, whatever — but it must be a deliberate, tested contract, not a leaked Python exception.

### A11. Literal syntax is "whatever Python `float()` accepts"
Because `float(node[1])` defines what a number is, the language accidentally accepts tokens like `'inf'`, `'Infinity'`, `'nan'`, `'1_000'`, `'  1 '` (whitespace), and `'1e999'` (silently becomes `inf`). That is almost certainly not the intended number grammar. Numbers should be validated against an explicit lexical rule.

### A12. Recursion depth limits
Both `parse` (deeply nested parens) and `evaluate` (a long left-associated chain like `1+1+1+...` builds a left-deep tree ~n levels tall) hit Python's recursion limit around ~1000 nesting levels and die with `RecursionError`. For a toy this may be acceptable, but it should be a known, documented limit (or the evaluator made iterative) before shipping anything that takes user input.

## B. Language-design problems

### B1. The grammar itself is broken as written
`factor := NUMBER | NAME | '(' expr ')' | expr '<' expr` is left-recursive (`factor → expr → term → factor`) and ambiguous — it cannot be implemented by this recursive-descent structure at all, which is probably *why* `<` never got implemented. Comparison does not belong in `factor`.

### B2. Comparison precedence is wrong in the spec
Putting `<` at the `factor` level would give it *higher* precedence than `*` (so `a < b * c` would mean `(a < b) * c`). Every mainstream language puts comparison *below* additive. The grammar should be:

```
comparison := expr ('<' expr)?      # or expr, with chaining decided explicitly
expr       := term (('+'|'-') term)*
...
```

### B3. Comparison semantics are unspecified
What does `a < b` evaluate to — a bool? `1.0`/`0.0`? Is `a < b < c` allowed, and if so is it Python-style chaining or C-style `(a<b)<c`? Can a comparison result feed into arithmetic (`(a<b)+1`)? None of this is decided. It must be, before the feature exists.

### B4. Spec/implementation drift
The grammar comment advertises NAME and `<`; the code supports neither. Whatever ships, the documented grammar and the parser must agree — the comment is currently actively misleading.

### B5. No lexer / unclear token contract
`parse` takes a pre-split list of strings, but nothing defines who produces it or what a valid token is. A calculator DSL needs a tokenizer (or at minimum a documented, validated token contract) that classifies NUMBER / NAME / operator / paren and rejects everything else with a position.

### B6. No error model
There are no custom exception types and no source positions. Every failure surfaces as `IndexError`, `ValueError`, `ZeroDivisionError`, or a silent wrong answer. Before shipping: a `SyntaxError`-style exception carrying the token index for parse failures, and an evaluation-error type for runtime failures (undefined name, division by zero).

### B7. (Minor) Untyped tuple AST
`('bin', op, l, r)` tuples work at this size, but named tuples/dataclasses would make A8/A9-class bugs structurally impossible. Not a blocker; worth doing while fixing A8/A9.

## C. Testing gaps

The suite is three asserts, all happy-path, and it would pass even with most of the bugs above. Specifically missing:

1. **`-` and `/` are never tested at all.** Two of the four operators have zero coverage.
2. **Associativity untested**: `1-2-3` must be `-4` and `8/4/2` must be `1.0` (the code happens to be left-associative, but nothing pins that down).
3. **Precedence tested from only one side**: `2*3+4` is there, `4+2*3` is not; `2*(3+4)` vs `2*3+4` interplay, nested parens, parens on the right — none tested.
4. **Variables**: not one test passes a non-empty `env`. A single `evaluate(parse(['x','+','1']), {'x': 2}) == 3.0` test would have caught A1 immediately.
5. **Comparisons**: zero tests; would have caught A2.
6. **Negative tests are entirely absent**: no test that unbalanced parens, empty input, trailing tokens (`['1','2']`), trailing operators (`['1','+']`), or unknown tokens raise errors. Right now most of these *don't* raise (A3–A5), and only error tests can pin the fixed behavior.
7. **Unary minus / negative literals**: untested (and unsupported, A6).
8. **Division by zero**: untested (A10).
9. **Undefined variable**: untested.
10. No test checks that `parse` consumes all input (impossible today anyway, since `parse` discards the final index — A3).
11. **Infrastructure**: bare module-level `assert`s are not a test suite — they stop at the first failure, give no diagnostics, and are silently stripped under `python -O`. Use pytest (and ideally add a small property-based test with hypothesis: random well-formed expressions round-tripped against Python's own eval on a restricted AST).

## D. What I would require before ship

1. Fix A1–A5 (variables via `env` with a defined undefined-name error; implement or explicitly drop `<`; end-of-input check; `)` check; token validation) — these are silent-wrong-answer bugs, all blocking.
2. Decide and implement unary minus (A6); decide division-by-zero and comparison semantics (A10, B3) and document them.
3. Rewrite the grammar so it's actually implementable, with comparison at the correct (lowest) precedence level, and make code and comment agree (B1, B2, B4).
4. Add a real lexer or a strict token contract with a defined number syntax (A11, B5).
5. Introduce proper error types with positions; no leaked `IndexError`/`ValueError`, no `None` returns from `evaluate` (A7, A8, A9, B6).
6. Test suite: cover all four operators, associativity, both precedence directions, nesting, variables, comparisons, and a full set of negative tests for every error path above; move to pytest; add property-based differential testing against a trusted oracle (C1–C11).
7. Nice-to-have, non-blocking: dataclass AST (B7), documented or removed recursion limits (A12).
