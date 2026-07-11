---
name: compiler-building
description: Compiler-building skill — discipline for compilers, interpreters, parsers, and DSLs: spec before code, testing as the main event, errors as UX
metadata:
  type: user
---

# Compiler Building — Language Tooling Skill

## Why

Compilers are the one domain where the input space is *another program* — effectively infinite and adversarial by accident. Smaller models build language tooling bottom-up: write a parser, bolt on evaluation, discover the language's semantics by whatever the code happens to do. The result: grammar ambiguities surface as parser bugs, semantics change silently between versions, and error messages describe the compiler's confusion instead of the user's mistake. This skill inverts it: the language is specified, the pipeline is staged, and testing is the majority of the work — because in compilers, it is.

## The Rule

**The spec precedes the implementation, each pipeline stage has its own contract and tests, and every bug becomes a permanent regression case.** A compiler without a conformance suite is a rumor about a language.

## How to Apply

### 1. Specify before implementing

The spec lives at `.claude/plans/{lang}-spec.md` with four sections: grammar (EBNF or equivalent), semantics table (per construct: evaluation order, scoping, type rules), undefined-behavior list, and open questions.

- Grammar written down *before* the parser — ambiguities found on paper cost minutes; found in the parser, days
- The undefined list is as load-bearing as the defined one — it's your future compatibility space
- Every "we'll decide later" recorded as an open question, not left as whatever-the-code-does

### 2. Stage the pipeline, contract each seam

Each stage: typed input, typed output, its own tests. Never let parsing "help" with semantics or codegen reach back into syntax — stage bleed is where compilers rot. A separate IR that seems unnecessary usually pays for itself the first time you add an optimization or a second target.

### 3. Testing is the main event (~half the total work, plan for it)

Design the suite with the **qa-testing** skill; compiler-specific test kinds:

- **Golden tests**: source in → expected AST/IR/output, one file pair per case, trivially addable
- **Error tests**: invalid programs with the *expected diagnostic* — error quality is tested, not hoped for
- **Round-trips where they exist**: parse(print(ast)) == ast; these catch entire bug classes free
- **Differential testing** when a reference exists (old implementation, another engine): same input, compare outputs
- **Fuzzing**: generated/mutated inputs; the parser must never crash, hang, or blow the stack on *any* byte sequence — a parse error is fine, a segfault is not
- **Every fixed bug adds its input to the suite permanently** — compiler regressions are legendary because inputs recombine forever

### 4. Errors are the user interface

A compiler's diagnostics *are* its UX (see ux-design). Every error: precise source location, what was wrong, what was expected, and where relevant a suggestion. Test the messages. "Syntax error" with a line number is the compiler describing its own confusion; "expected ')' to close the call opened at 3:12" is it describing the user's.

### 5. Optimize only what stays correct

Optimizations come after correctness, each one: justified by a benchmark per the **performance-optimization** skill (benchmark in the repo), verified against the full suite, and toggleable (`-O0` path stays alive) — because when codegen is wrong, bisecting optimizations is how you find it.

## Anti-Patterns

- Discovering the grammar by writing the parser (ambiguity found at the worst possible time)
- Semantics defined as "whatever the current evaluator does" — now every refactor is a language change
- Skipping the IR because "we only have one target" (you have two the moment you add an optimizer)
- Error messages added after the fact, untested, describing internal state
- A test suite of 12 hand-picked programs for a language with infinite programs — generate, fuzz, differential
- Performance work before the conformance suite exists (fast and wrong is just wrong, sooner)

## Verification

Done means evidence, not vibes — report three numbers in the verify artifact:
- Conformance-suite count (golden + error + round-trip cases), all passing
- Fuzz run duration with zero crashes/hangs/stack overflows (state the duration; "we fuzz" without a number is a FAIL)
- Error-message test count — diagnostics are tested output, not hoped-for output
- `.claude/plans/{lang}-spec.md` exists and matches the implementation; verdict is PASS/FAIL
