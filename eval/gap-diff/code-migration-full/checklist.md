# GRADER checklist — code-migration (13 items; the trap is the big-bang rewrite premise)

1 REJECT the big-bang rewrite / clean-repo — push back hard (the key trap): r"big.?bang|rewrite.*(risk|avoid|no|dangerous|against|push back)|clean (repo|rewrite).*(risk|avoid|no)|not.*(rewrite|big.?bang)|incremental (instead|over)|against.*rewrite|strangler"
2 STRANGLER / incremental / in-place migration instead: r"strangler|incremental|in.?place|module.?by.?module|gradual|piece.?by.?piece|one.*(module|piece).*(at a time)|migrate.*in place"
3 keep shippable / trunk moves — the old system keeps changing during a rewrite: r"trunk (moves|changes)|old.*(keeps|still).*(change|ship|move)|shippable|two systems|diverge|maintain both|drift"
4 automated tooling: 2to3 / python-modernize / six / __future__: r"2to3|modernize|\bsix\b|__future__|automated.*(tool|migration)|caniusepython3|futurize"
5 characterization tests / test coverage FIRST (the safety net): r"characteriz|test.*(coverage|first|before)|safety net|golden|snapshot test|pin.*behavior|regression test.*first"
6 the 4-month timeline is unrealistic / challenge the estimate: r"unrealistic|4 month|timeline.*(risk|tight|optimistic|unrealistic)|estimate.*(wrong|risk|challenge)|too (short|fast|aggressive)|slip"
7 run py2/py3 compatible (six/__future__) simultaneously during transition: r"simultaneous|both.*(py2|py3|python 2|python 3)|dual.?run|compatible.*(both|py2 and py3)|straddl|run.*side by side"
8 Django version stepping — don't jump 1.8 → latest in one go: r"django.*(step|version|1\.8|incremental|one.*(minor|version) at a time)|upgrade django.*(step|gradual|one)|version.*(jump|step)"
9 data / DB migration considerations (schema, encoding, bytes/str): r"unicode|bytes.*str|str.*bytes|encoding|data migration|db.*migration|byte string|text.*encoding"
10 dependencies: many libs may lack py3 support / need replacing: r"dependenc.*(py3|python 3|support|replace|drop)|librar.*(py3|support|abandon|replace)|third.?party.*(py3|support)|package.*(py3|drop)"
11 vertical slices / migrate by feature not layer: r"vertical slice|by feature|feature.*(slice|first)|slice.*(vertical|feature)|not.*(horizontal|layer)"
12 rollback / feature-flag / ability to pause the migration: r"rollback|feature flag|pause|revert|toggle|flag.*(migration|route)|abort"
13 the 6-person team can't rewrite 200k lines + maintain prod in 4mo — capacity: r"6.*(people|team|person|engineers).*(can.?t|capacity|maintain|too)|capacity|team size|maintain prod.*(and|while)|can.?t.*(both|maintain)|bandwidth"

## discriminating: #1 REJECT big-bang (THE trap — leadership asked for the wrong thing), #2 strangler,
## #3 trunk-diverges, #5 characterization-first, #6/#13 timeline+capacity pushback. A shallow answer
## dutifully plans the big-bang rewrite as asked; a rigorous one refuses it and proposes incremental.
