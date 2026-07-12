# GRADER checklist — requirements-elicitation (13 items; the ask hides real forks)

1 does NOT just start building — clarifies first: r"before (building|coding|start)|clarif|question.*(first|before)|don.?t.*(start|build).*(yet|before)|not.*(jump|start).*(coding|building)|ask.*before"
2 restate with a done-condition / define scope: r"done.*(mean|condition|definition)|what.*(done|success) looks like|scope|define.*(export|done)|acceptance"
3 the real DRIVER — 'legal wants it' = likely GDPR/CCPA data-portability compliance: r"gdpr|ccpa|data portab|compliance|legal.*(requirement|regulat|why)|regulat|right to.*(data|access|export)|privacy law"
4 WHAT data — 'everything' is ambiguous (all fields? related? other users' data?): r"what data|everything.*(mean|ambig|vague)|which (data|fields|records)|all.*(data|fields).*(mean|really)|scope of.*(data|export)|whose data"
5 FORMAT — CSV/JSON/machine-readable (GDPR requires portable format): r"format|csv|json|machine.?readable|portable.*format|xml|which format|structured"
6 the SECURITY/authz fork — user exports only THEIR data, not others' (PII/tenant): r"only.*(their|own) data|authoriz|other users|cross.*(user|tenant)|PII|leak.*(other|user)|scope.*(user|own)|access control"
7 DELIVERY/volume — 'downloads everything' may be huge → async job not sync button: r"async|large.*(data|volume|download)|background job|sync.*(vs|not).*async|volume|timeout|too (big|large).*(sync|download)|email.*link|job"
8 'should be quick' is challenged — it's NOT quick (pushes back on the estimate): r"not.*(quick|simple|easy)|quick.*(assumption|wrong|challenge|underestimat)|more.*(complex|involved)|underestimat|push back.*(quick|estimate)|actually.*(hard|complex)"
9 the DEADLINE ('this quarter') as scope pressure — MVP vs full: r"deadline|this quarter|timeline|MVP|scope.*(deadline|cut)|phase|minimum.*(viable|version)|what.*(ship|first).*(quarter|deadline)"
10 who is the ACTUAL user / stakeholder — end-user self-serve vs legal/admin export: r"who.*(user|export|for)|self.?serve|end.?user vs|admin.*(export|vs)|stakeholder|which user"
11 audit/logging — exports of personal data may need audit trail: r"audit|log.*(export|access)|track.*(who|export)|compliance.*(log|audit)|record.*(export|access)"
12 sensitive data handling — what to EXCLUDE (other people's PII, secrets, internal fields): r"exclude|redact|sensitive|internal (field|data)|secret|not.*(include|export).*(password|internal|other)|filter.*(sensitive|internal)"
13 rate-limit / abuse — export endpoint could be abused for scraping/DoS: r"rate.?limit|abuse|scrap|dos|throttle|repeated.*export"

## discriminating: #1 don't-build-yet, #3 GDPR-is-the-real-driver, #6 authz-only-own-data, #7
## async-for-volume, #8 not-actually-quick. A shallow answer builds a CSV button; a rigorous one
## surfaces the compliance framing + the authz/volume/scope forks the one-liner hides.
