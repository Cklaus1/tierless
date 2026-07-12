# Arm B skills for Task 12b
- deconstruct
- verify

Underspecified variant: the invariants (atomicity, conservation, integer cents) are NOT
stated in the task — the arm must DISCOVER them. deconstruct forces enumerating failure
paths per step; verify forces adversarial self-review ("what input breaks this?"). Those
are exactly the disciplines that surface the debit-before-check bug a rushed arm ships.
build-loop omitted here — this is a single-file build; the test is invariant discovery,
not multi-phase structure (that's task 07).
