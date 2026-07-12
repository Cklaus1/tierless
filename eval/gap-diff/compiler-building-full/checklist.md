# GRADER checklist — compiler-building (15 items). The code has real planted defects.

The grammar/parser/evaluator has specific bugs and gaps. A shallow review says "add error handling
and more tests." A rigorous one enumerates the actual defects below.

## Planted defects & required disciplines
1 NAME/variable eval unhandled — evaluate() has no 'lit' path for non-numeric; float('x') crashes on a NAME: r"variable|name.*(eval|unhandled|crash|not handled)|float\('|env\[|lookup.*(variable|name)|NAME.*(eval|handled)|undefined variable"
2 the '<' comparison in the grammar is NEVER parsed (factor never handles it) — dead grammar rule: r"comparison|'<'|less.than|< .*(not (parsed|handled|implemented)|never|missing|dead)|factor.*(doesn.t|never).*<|grammar.*(unimplemented|dead|not.*match)"
3 division by zero unhandled (1/0 → crash): r"division by zero|divide by zero|/ ?0|zero.?division|1/0|denominator"
4 index-out-of-range / unexpected end of input (tokens[i] past end): r"index (out of|error)|out of range|end of (input|tokens)|tokens\[i\].*(past|end|bounds)|unexpected (end|eof)|missing.*(token|operand)|IndexError"
5 missing close-paren not detected (returns i+1 blindly, no check it's ')'): r"missing.*(close|closing|\))|unbalanced paren|no check.*\)|assume.*\)|paren.*(mismatch|not checked|unbalanced)|consume.*\).*(without|no) check"
6 no tokenizer/lexer — assumes pre-tokenized input; multi-char numbers/whitespace/negative unhandled: r"tokeniz|lexer|pre.?tokenized|multi.?(char|digit)|whitespace|negative number|scan|lexing|input.*(already|assumed) token"
7 trailing/leftover tokens not rejected ('1 2' or '1 + 2 )' silently accepted): r"trailing|leftover|extra token|didn.t consume|remaining token|1 2|not.*(all|fully) consumed|expr\(0\)\[0\].*ignore|garbage after"
8 float everywhere — no int/precision consideration (0.1+0.2, or the DSL wanting exact): r"float.*(everything|precision|0\.1|exact|round)|floating.point|precision|integer.*(vs|not)|decimal"
9 undefined-behavior / spec gaps stated (what does < return? bool vs number? assoc?): r"undefined|unspecified|spec.*(gap|unclear|ambiguous)|what (does|should).*(<|comparison) (return|mean)|semantics.*(unclear|undefined|missing)|associativ|precedence.*(of|for) <"
10 error MESSAGES / diagnostics with position, not just crashes: r"error message|diagnostic|position|location|line.*col|caret|report.*(where|position)|user.friendly error|which token|helpful.*error"
11 TEST GAPS — only 3 happy-path tests; no error/edge tests (the review must call this out): r"test.*(gap|only|happy|3 tests|insufficient|missing)|no (error|edge|negative) test|test.*(coverage|edge case|failure)|more tests|only.*happy path"
12 tests should cover the ERROR paths (invalid input, div0, unbalanced) once fixed: r"test.*(error|invalid|div|zero|unbalanced|missing paren|bad input)|error.?case test|negative test|test.*(reject|failure)|fuzz"
13 precedence: '<' has no defined precedence vs +/*; grammar puts it inside factor wrongly: r"precedence.*(<|comparison|wrong|undefined)|< .*(precedence|bind|inside factor|wrong level)|factor.*<.*(wrong|odd|misplaced)|grammar.*(precedence|level).*<"
14 associativity is correct (left) for +/- BUT worth confirming / stating: r"associativ|left.?assoc|1-2-3|a - b - c|left to right|((.*)-.*)"
15 no AST/eval separation issues or recursion depth / deep-nesting stack overflow: r"recursion depth|stack overflow|deep.*(nest|recursion)|recursion limit|deeply nested|blow the stack"

## Scoring: each present = 1, /15. Discriminating (subtle, code-specific): #1 (NAME crashes eval),
## #2 (the '<' rule is dead — never parsed), #5 (missing-paren not checked), #7 (trailing tokens
## accepted), #13 (comparison precedence wrong). These require actually TRACING the code, not reciting
## "compilers need error handling." Hypothesis: bare model recites generic compiler advice + catches
## div0/tests, MISSES the code-specific dead-grammar-rule (#2) and the NAME-eval crash (#1). If Fable
## catches the traced defects Haiku misses → real gap.
