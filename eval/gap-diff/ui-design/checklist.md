# GRADER checklist — ui-design (12 issues in the component)

1 no loading state (fetch in flight shows nothing): r"loading (state|indicator|spinner)|no loading|while.*(fetch|load)|pending state"
2 no empty state (rows==[] shows just headers): r"empty state|no (rows|data|results)|zero (rows|results)|nothing to show|empty.*(list|table)"
3 no error state (fetch failure unhandled): r"error state|fetch (fail|error)|\.catch|error handling|network (error|fail)|request fail"
4 missing key prop on mapped rows: r"key prop|missing key|key=|key warning|react key"
5 not semantic (divs not a real <table>/th/td): r"semantic|<table>|table element|th|td|role=|div.*(table|instead)|not a (real )?table"
6 color-only status (green/red, colorblind + contrast): r"color.?only|colou?rblind|color alone|not (just|only) colou?r|icon.*(status|text)|red.*green.*(access|colorblind)"
7 low-contrast header (#999 on white fails WCAG): r"#999|contrast|low.?contrast|wcag|gray.*(header|text).*(contrast|fail)|4\.5|readab"
8 div onClick not keyboard accessible (rows + load more not buttons): r"keyboard|not.*(button|focusable)|<button>|tabindex|onClick.*div|div.*(clickable|not accessible)|role=.?button|focus"
9 stale-closure bug: setRows([...rows]) with rows not in deps: r"stale (closure|rows|state)|closure|\[\.\.\.rows|dependency array|deps.*(missing|rows)|functional update|prev =>"
10 hardcoded styles / no design tokens / inline styles: r"inline style|hardcod|design token|magic (number|value)|px.*hardcod|no (theme|token)|repeated.*(200|width)"
11 no focus/hover/active states on interactive rows/button: r"hover|focus (state|ring|visible)|active state|interactive.*(state|feedback)|no.*(hover|focus)"
12 no alt/aria for status meaning / screen reader: r"aria|screen reader|alt|sr-only|accessible name|announce|label.*(status|active)"

## Scoring: each present = 1, /12. Enumeration of coverage — the ui-design skill's whole claim is
## systematically checking every state + contrast pair + semantic + a11y item vs. eyeballing.
