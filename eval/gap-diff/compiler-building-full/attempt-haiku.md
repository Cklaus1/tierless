# Interpreter Review: Calculator DSL

## 1. CRITICAL: `evaluate` crashes on comparison operators

The grammar declares `factor := expr '<' expr`, but `evaluate` has no case for `<`. Any expression containing a comparison will raise a `KeyError`/`IndexError` on `node[1]` (the operator) because the `if op == '+'` chain falls through to the end of the function, returning `None`. Worse, the `bin` node for `<` is built as `('bin', '<', left_val, right_val)`, so `op` would be `'<',` and none of the `if` branches match -- the function silently returns `None` instead of raising. This is a correctness bug: `parse(['1', '<', '2'])` produces a valid AST, but `evaluate` returns `None` instead of `True`.

## 2. CRITICAL: `factor` does not handle NAME (variables)

The grammar says `factor := NUMBER | NAME | '(' expr ')' | expr '<' expr`, but `factor` only handles `'('` and falls through to `('lit', t), i+1` for everything else. This means:

- **Variable names are silently treated as literals.** `parse(['a'])` produces `('lit', 'a')`, and `evaluate` then calls `float('a')`, which raises `ValueError`. The parser never builds a `('var', 'a')` node. The task description says the DSL supports variables, but the parser does not implement this.

## 3. CRITICAL: `factor` does not handle `<` (comparison in factor)

The grammar says `factor` can be `expr '<' expr`, but `factor` never checks for `<`. It only checks for `'('` and treats everything else as a literal. So `parse(['1', '<', '2'])` would call `factor(0)`, see `'1'`, return `('lit', '1')`, and then `term` and `expr` would try to consume `<` as an operator -- but `<` is not in `('+','-')` or `('*','/')`, so the loops exit. The result is `('lit', '1')` with the tokens `['<', '2']` silently ignored. This is a parser bug: trailing tokens are dropped without error.

## 4. CRITICAL: No error handling for unexpected tokens / unterminated expressions

- **Unterminated parentheses:** `parse(['(', '1', '+', '2'])` (missing `)`) will call `expr(i+1)` recursively, eventually index-out-of-bounds when `i >= len(tokens)` and `tokens[i]` is accessed.
- **Trailing tokens:** `parse(['1', '+', '2', 'x'])` silently ignores `'x'` because the `expr` loop only consumes `+`/`-` and the remaining tokens are never checked.
- **Empty input:** `parse([])` crashes with `IndexError` on `tokens[0]`.
- **Consecutive operators:** `parse(['1', '+', '+', '2'])` would call `factor` on `'+'`, which returns `('lit', '+')`, then the outer `while` loop consumes the second `+` as an operator, producing a nonsensical AST.

## 5. BUG: Division by zero is unhandled

`evaluate` performs `l / r` with no check for `r == 0`. This raises `ZeroDivisionError`, which is a runtime crash with no user-friendly message. For a calculator DSL, this should either raise a descriptive error or return `inf`/`nan` explicitly.

## 6. BUG: `evaluate` does not handle `('var', name)` nodes

Even if the parser were fixed to produce `('var', 'a')` nodes, `evaluate` has no case for variable lookup. It only handles `'lit'` nodes. This is a language-design gap: the DSL claims to support variables but the evaluator cannot resolve them.

## 7. BUG: `evaluate` returns `None` for unrecognized node types

If any node type other than `'lit'` or a recognized binary operator is encountered, the function falls through and returns `None` silently. There is no error path. This makes debugging extremely difficult -- errors manifest as silent `None` values propagating through subsequent operations.

## 8. BUG: Left-associativity of `<` is undefined

The grammar puts `<` inside `factor`, which means `1 < 2 < 3` would be parsed as `factor -> expr '<' expr`, where the RHS `expr` recursively calls `factor` again. But since `factor` doesn't actually handle `<`, this is moot -- the expression is silently truncated. If `<` were properly implemented in `factor`, the associativity would be right-to-left (because `factor` is recursive on the right), which is non-standard for comparisons. Comparisons are typically left-associative or chained.

## 9. TEST SUITE: Insufficient test coverage

The three tests cover only happy-path arithmetic:

- Test 1: `1 + 2` -- basic addition
- Test 2: `2 * 3 + 4` -- operator precedence
- Test 3: `(1 + 2) * 3` -- parentheses

Missing entirely:
- **Variable evaluation:** No test with any variable names
- **Comparison operators:** No test with `<`
- **Subtraction and division:** Only `+` and `*` are tested
- **Error cases:** No tests for division by zero, invalid input, missing variables
- **Edge cases:** Single number, nested parentheses, chained operations
- **Operator precedence edge cases:** Only one precedence test, and it is the simplest case

## 10. DESIGN: No tokenizer/lexer

The parser operates directly on a flat list of tokens. There is no lexer to convert raw strings like `"1+2*(3-4)"` into tokens. This is not a bug per se (the parser takes a token list), but it means the "calculator DSL" is not usable with raw input. A real calculator needs a tokenizer.

## 11. DESIGN: No support for unary operators

Negative numbers like `-5` cannot be expressed. The parser would see `-` as a binary operator and then call `factor` on `5`, but the preceding `-` would be consumed by the `expr` loop as a binary operator with no left operand (actually, `val` would be `('lit', '5')` from the first `term`, and then `-` would try to consume the next term). Wait -- `parse(['-5'])` would call `expr(0)`, which calls `term(0)`, which calls `factor(0)`, which sees `'-'` and returns `('lit', '-')`. Then `term` returns `('lit', '-')` and `expr` tries to consume the next token as `+`/`-`, but there is none. So the result is `('lit', '-')` and `evaluate` calls `float('-')` which raises `ValueError`. Negative numbers are not supported.

## 12. DESIGN: No support for `>` or other comparison operators

The grammar only declares `<`. A calculator DSL would typically support `<=`, `>=`, `==`, `!=`, `>`. This is a language-design limitation.

## 13. DESIGN: AST node format is fragile

The AST uses tuples with magic string indices: `node[0]` is the tag, `node[1]` is the operator/value, `node[2]` and `node[3]` are children. This is error-prone and hard to maintain. Named tuples, dataclasses, or a visitor pattern would be more robust.

## 14. DESIGN: `evaluate` evaluates both sides eagerly

For comparison operators (if they were implemented), both sides are always evaluated even if short-circuiting would be appropriate. This is not a bug for arithmetic expressions but is a design consideration for a language that might grow conditional logic.

## 15. DESIGN: No type safety or input validation

`evaluate` assumes all `'lit'` nodes contain numeric values. If a variable name somehow reaches `evaluate` as a `'lit'` node (as currently happens), `float()` raises an unhelpful `ValueError`. There is no distinction between a literal number and an identifier at the AST level.

## Summary: What Would Be Required Before Shipping

1. **Fix the parser** to properly handle `NAME` tokens (produce `('var', name)` nodes) and `<` comparisons (either in `factor` or as a new precedence level).
2. **Add a tokenizer/lexer** to convert raw input strings into tokens.
3. **Fix `evaluate`** to handle `('var', name)` nodes by looking up the variable in `env`, and to handle `<` comparisons.
4. **Add error handling** for: unterminated parentheses, trailing tokens, empty input, division by zero, unknown variable names, and invalid literal values.
5. **Support negative numbers** via a unary minus operator.
6. **Expand the test suite** to cover: all operators, variable lookups, comparisons, error cases, edge cases, and operator precedence.
7. **Add a tokenizer test suite** to verify correct tokenization of raw input strings.

The code as written is not functional for the stated DSL. It cannot evaluate variables, cannot evaluate comparisons, silently drops trailing tokens, and crashes on unterminated parentheses. The test suite covers only 3 of the 6+ operators and 0 error cases. This would not ship in any form.