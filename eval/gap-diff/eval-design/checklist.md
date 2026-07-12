# GRADER checklist — eval-design (12 methodological disciplines)

These are the disciplines this project learned THE HARD WAY (each maps to a LESSONS.md failure we
actually hit). A naive eval design does the obvious A/B + LLM-judge and misses most of these. Score
each by keyword presence; the discriminating ones are the non-obvious failure guards (3,4,5,6,10).

1 CONTROL the model, vary only the skill (bare vs +skill, SAME model) + a frontier reference bar:
  r"same model|hold.*model|only.*(skill|variable)|control|A/B|bare (vs|and) .*skill|reference (bar|model)|frontier.*(bar|baseline)"
2 OBJECTIVE scoring — checklist/rubric/tells, not vibes/'quality':
  r"objective|rubric|checklist|tells|pass/fail|binary|specific criteria|not.*(vibe|subjective|quality)|gradeable"
3 DO NOT trust an LLM judge — it hallucinates/inflates; deterministic or human backstop:
  r"llm.?(judge|grader).*(bias|hallucin|inflat|unreliable|not trust)|deterministic (scor|grad|check)|keyword|execution (oracle|based)|human (grader|verif|spot.?check)|judge.*(unreliable|verify)|not.*llm.*(judge|grade)"
4 HEADROOM / CEILING check — if bare already aces it, the task proves nothing:
  r"ceiling|headroom|too easy|bare.*(already|aces|passes|strong)|floor effect|discriminat|task.*(hard enough|difficult enough)|no (gap|room)|saturat"
5 MULTIPLE RUNS — single runs lie (variance):
  r"multiple runs|N ?= ?[2-9]|several runs|repeat|variance|run.*(3|three|multiple) times|averaged|spread|nondetermin"
6 BLIND grading — grader doesn't know which arm / can't see the answer key:
  r"blind|grader (doesn.t|not).*(know|see)|anonymi|label.strip|without knowing.*(arm|which)|hide.*(which|arm|condition)"
7 REALISTIC / representative tasks, multiple, not one cherry-picked:
  r"realistic|representative|multiple tasks|variety|range of|diverse task|cherry.?pick|task (suite|set)|enough tasks"
8 EXECUTION / ground-truth where possible (run the code, don't judge it):
  r"execut|run the (code|test)|test suite|actually run|ground truth|oracle|acceptance test|compile.*run|behavior"
9 GUARD the fixtures / prevent contamination / test leakage:
  r"contaminat|leak|fixture.*(corrupt|guard|protect|readonly|read-only)|isolat|answer key.*(hidden|not shown|separate)|grader.*(separate|not readable)|don.t (show|expose).*(answer|test|solution)"
10 KNOWLEDGE vs PROCESS / mechanism — WHY the skill helps, not just that a number moved:
  r"why|mechanism|knowledge (vs|versus) (process|skill)|attribut|what (caused|explains)|confound|correlat.*causa|is it the skill|placebo|reason for the (gap|lift)"
11 PER-MODEL / generalization — a result on one model may not transfer:
  r"generaliz|per.?model|model.?specific|other models|transfer|different (model|family)|only.*(this|that) model|across models"
12 PRE-REGISTER the success criterion — decide what 'supported' means BEFORE seeing results:
  r"pre.?regist|decide.*(before|in advance)|success (criteri|threshold|bar)|what.*(count|means).*(support|pass)|define.*(pass|win) (before|upfront)|threshold.*(before|advance)"

## Scoring: each present = 1, /12. Hypothesis (derive-the-non-obvious class): a bare model designs
## the naive A/B+LLM-judge eval and hits ~half; a rigorous design (fable, or a skilled arm) catches
## the non-obvious failure guards (#3 LLM-judge distrust, #4 headroom, #6 blind, #9 contamination,
## #10 mechanism). If bare ~= fable, eval-design is at ceiling; if fable >> bare, real distillable gap.
