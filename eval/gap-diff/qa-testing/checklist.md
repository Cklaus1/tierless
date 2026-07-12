# GRADER checklist — qa-testing (12 distinct test cases that thorough coverage needs)

1 even split (no remainder): r"even|divides evenly|no remainder|exact.*split|100.*2|divisible"
2 remainder distribution (uneven, first N get +1): r"remainder|uneven|does.?n.?t divide|first (few|n|people).*(extra|\+1|more)|10.*3|100.*3|leftover cent"
3 sum-equals-total invariant (the core property): r"sum.*(equal|=|add).*total|adds? up|invariant|conservation|total.*preserved|reconstruct"
4 num_people <= 0 -> ValueError (zero AND negative): r"num_people.*(0|zero|negative)|zero people|negative people|people.*(<= ?0|invalid)"
5 total negative -> ValueError: r"negative total|total.*(< ?0|negative)|total.*invalid"
6 tip negative -> ValueError: r"negative tip|tip.*(< ?0|negative)|tip.*invalid"
7 tip zero / default (no tip): r"tip.*(0|zero|default|no tip|without tip)|zero tip|default tip"
8 tip rounding (round-half behavior on tip calc): r"tip.*(round|rounding|\.5|half|fraction)|round.*tip"
9 total zero (valid, everyone gets 0): r"total.*(0|zero)|zero (total|bill)|free|0 cents"
10 one person (num_people=1 gets everything): r"one person|num_people.*1|single person|1 person"
11 large numbers / overflow-ish / big bill: r"large|big (bill|number|total)|overflow|million|huge"
12 remainder < num_people always (each gets at most +1 / no one gets +2): r"at most.*(1|one) (extra|more|cent)|remainder.*< num_people|no one gets.*2|fairness|difference.*(1|one) cent"

## Scoring: each present = 1, /12. Enumeration test: does the reviewer systematically cover the
## input space (boundaries, invariants, error paths, rounding) or list a few happy cases and stop.
