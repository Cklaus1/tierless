# GRADER checklist — infra-ops (13 items; planted defects)

1 secrets in -e flags AND echoed in CI logs — leak (use secret manager): r"secret.*(leak|log|manager|vault|env|exposed)|password.*(log|leak|plain|exposed)|API_KEY.*(leak|log|exposed)|hunter2|sk_live|credentials.*(log|leak|exposed)|secret manager"
2 :latest tag — not pinned/immutable, no rollback by digest: r":latest|latest tag|immutable|pin.*(tag|version|digest)|not pinned|sha.*digest|version.*tag"
3 stop-then-run = downtime, no rolling/blue-green: r"downtime|stop.*(before|then).*(run|start)|no rolling|blue.?green|zero.?downtime|gap.*(between|stop|start)|outage.*deploy"
4 no healthcheck — traffic hits a dead/starting container: r"health.?check|readiness|liveness|no health|before.*(traffic|serving)|starting.*container|not ready"
5 single prod host — SPOF, no redundancy/HA: r"single.*(host|point|prod)|SPOF|no redundan|one (host|server|instance)|HA\b|high avail|failover"
6 DB on same host as app — coupled failure, no separation: r"same host.*(db|database)|db.*(same|coupled|co-?located)|separate.*(db|database)|database.*(host|separate|dedicated)"
7 rollback is manual/fragile — no real rollback (keep previous image): r"rollback.*(manual|fragile|by hand|no|weak|real)|previous (image|version|deploy)|automated rollback|revert.*(image|deploy)"
8 no backups / DB backup story — single Postgres, data loss risk: r"backup|data loss|restore|snapshot|no backup|pg_dump|point.in.time"
9 sh not bash + no set -e — script errors silently ignored, half-deploy: r"set -e|errexit|/bin/sh|error handling.*script|silently.*(fail|continue|ignore)|half.?deploy|script.*(fail|error).*(continue|ignore)|no error check"
10 no image scanning / build provenance / supply chain: r"scan|vulnerab.*(image|scan)|supply chain|provenance|trivy|CVE.*image"
11 push :latest then pull — race / not atomic across future multi-host: r"race|atomic|not.*atomic|pull.*(stale|race)|concurrent deploy"
12 no observability/logging/metrics/alerting: r"observab|logging|metrics|alert|monitor|no (logs|metrics|monitoring)"
13 no staging / canary / gradual rollout before prod: r"staging|canary|gradual|percentage|ramp|test.*before prod|no staging"

## discriminating: #1 secret leak (esp. echoed in CI logs), #2 :latest, #3 stop-run downtime, #7
## fake rollback, #9 sh-no-set-e. Recite-generic: "add monitoring and backups" without the specifics.
