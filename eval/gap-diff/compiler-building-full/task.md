# Compiler / interpreter task

A junior engineer built a small expression interpreter for a calculator DSL (numbers, `+ - * /`,
parentheses, variables, and comparisons like `a < b`). Here's their parser/evaluator core and their
test suite. Review it: what's wrong, what's missing, and what would you require before it ships?
Enumerate every real problem — correctness, language-design, and testing.

```python
# grammar (informal): expr := term (('+'|'-') term)*
#                      term := factor (('*'|'/') factor)*
#                      factor := NUMBER | NAME | '(' expr ')' | expr '<' expr
def parse(tokens):
    def expr(i):
        val, i = term(i)
        while i < len(tokens) and tokens[i] in ('+', '-'):
            op = tokens[i]; rhs, i = term(i+1)
            val = ('bin', op, val, rhs)
        return val, i
    def term(i):
        val, i = factor(i)
        while i < len(tokens) and tokens[i] in ('*', '/'):
            op = tokens[i]; rhs, i = factor(i+1)
            val = ('bin', op, val, rhs)
        return val, i
    def factor(i):
        t = tokens[i]
        if t == '(':
            val, i = expr(i+1)
            return val, i+1          # consume ')'
        return ('lit', t), i+1
    return expr(0)[0]

def evaluate(node, env):
    if node[0] == 'lit':
        return float(node[1])
    op, l, r = node[1], evaluate(node[2], env), evaluate(node[3], env)
    if op == '+': return l + r
    if op == '-': return l - r
    if op == '*': return l * r
    if op == '/': return l / r

# tests
assert evaluate(parse(['1','+','2']), {}) == 3.0
assert evaluate(parse(['2','*','3','+','4']), {}) == 10.0
assert evaluate(parse(['(', '1', '+', '2', ')', '*', '3']), {}) == 9.0
```
