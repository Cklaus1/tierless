# Infra / deploy review — deploy.sh + single-host prod

Findings grouped by severity. Line references are to the script as shown.

---

## A. Outright bugs in the script (it doesn't even do what it intends)

1. **Build/push tag mismatch.** The image is built as `app:latest` but the push is `registry/app:latest`. There is no `docker tag app:latest registry/app:latest` step, so either:
   - the push fails outright (no such local image), or
   - worse, it *succeeds* by pushing a **stale** `registry/app:latest` left over from a previous manual tag — silently deploying old code while CI shows green.

2. **Second-and-later deploys fail on container name conflict.** `docker stop app` stops the container but does not remove it, and there is no `--rm` on the run and no `docker rm app`. So `docker run --name app ...` fails with "name already in use" on every deploy after the first — **and by that point the old container is already stopped**, so the failure mode is: deploy fails *and* the site is down, with nothing running.

3. **No error handling: `#!/bin/sh` with no `set -e` (and `sh` has no `pipefail`).** If `docker build` or `docker push` fails, the script continues to the `ssh` step and deploys whatever `registry/app:latest` currently is (stale image). The script's exit code is just the last command's, so CI can report success on a deploy that built nothing and shipped old code.

4. **Failure ordering guarantees downtime on any run failure.** Inside the ssh command, the old container is stopped *before* the new one is known to start. If `docker run` fails for any reason (bad image, crashing entrypoint, port conflict, disk full), the service is down with no automatic recovery — the script has already destroyed the working state and there is no health-gated cutover and no automatic restore of the old container.

5. **`docker pull` failure isn't isolated either** — but note the `&&` chain at least stops there. The asymmetry is the point: pull failure = safe no-op, run failure = outage. The design has no "verify new is healthy before killing old" step at all.

6. **No port publishing / runtime config shown.** As written there is no `-p`/`--network` flag, so the container isn't reachable from outside Docker's bridge network. If that's elided, fine — but it also means no reverse proxy / LB is part of the deploy, which matters for draining (see B4).

---

## B. Rollout safety / reliability

1. **Guaranteed downtime on every deploy.** stop-then-start on a single host is a hard outage window every merge to main (image pull time + app boot time, unbounded if boot is slow). No blue/green, no second container on another port behind a proxy, no rolling anything.

2. **No health check of any kind — pre- or post-deploy.** The comment says it explicitly. There is:
   - no container `HEALTHCHECK` / no `--health-cmd`,
   - no post-deploy smoke test (`curl -f http://.../healthz` with retries),
   - no gate that fails CI when the new container crash-loops.
   A deploy that ships a container that exits immediately is reported as success; you find out from users. Minimum fix: after `docker run`, poll a health endpoint, and on failure restart the previous image and fail the pipeline.

3. **No `--restart` policy.** The container won't come back after an app crash or a host reboot. A reboot of prod-1 (kernel patch, OOM, power) is an outage until a human redeploys by hand. Use `--restart unless-stopped` at minimum.

4. **No graceful shutdown / connection draining.** `docker stop` sends SIGTERM and SIGKILLs after 10s. In-flight requests are dropped on every deploy; if the app doesn't handle SIGTERM it's just killed. There is no LB to drain from, so even a well-behaved app drops connections.

5. **No concurrency control on deploys.** Two merges to main in quick succession run two copies of this script concurrently: interleaved `push`/`pull` of the mutable `latest` tag, interleaved `stop`/`run`, name-conflict races. End state is nondeterministic — you can end up with the *older* commit live and CI green on both. Deploys need a lock (CI concurrency group) and ideally queueing.

6. **Mutable `:latest` tag everywhere — no immutable versioning.**
   - You cannot tell what is deployed ("what's live right now?" is unanswerable from the registry or the host).
   - `docker pull latest` on the host may race with a concurrent push.
   - Rollback to a *specific* known-good build is impossible, because every build overwrites the only tag.
   Tag with the git SHA (`registry/app:$GIT_SHA`) and deploy that exact tag; keep `latest` as a convenience alias at most.

7. **The stated rollback procedure is broken, not just slow.** "Re-run an old deploy.sh by hand":
   - The old script builds `app:latest` from *whatever is checked out at the time*, and pushes/pulls `latest` — so re-running an old copy of the script deploys the **current** code unless you also check out the old commit.
   - Even checking out the old commit, `docker build` is not reproducible: unpinned base images, `apt-get`/package installs, and dependency ranges mean the "rollback" build can differ from what was actually running (and can fail to build at all).
   - It's manual, undocumented, requires SSH access and knowledge of the secrets, and has no target time. Real rollback should be: `docker run` a previously pushed immutable tag — no rebuild.
   - There is **no database migration story** in either direction: nothing runs migrations on deploy (so how do schema changes ship?), and nothing addresses that rolling the app back after a schema migration may break the old code. Rollback safety for anything touching the DB is undefined.

8. **No deploy audit trail.** Nothing records which commit/image went out when, by whom. Combined with `:latest`, incident response starts with archaeology.

---

## C. Security

1. **Production secrets hardcoded in the script, which lives in the repo.** `DB_PASSWORD=hunter2` and `API_KEY=sk_live_abc123` are in git history — visible to every current and past person (and every CI job, fork, laptop clone) with read access to the repo. They are permanently in history even after removal.

2. **Secrets are echoed in CI logs** (stated). CI logs typically have broader access, longer retention, and get forwarded to log aggregators. Both credentials must be treated as **already compromised**: rotate the DB password and the live API key immediately, before any other fix.

3. **`-e` env injection leaks secrets on the host** even after fixing the repo/logs: they appear in `docker inspect app`, in `/proc/<pid>/environ`, in the shell history of whoever runs deploys manually, and in the process table (`ps`) while the `docker run` command line exists. Use a secrets manager (Vault / AWS SSM / GCP Secret Manager), or at minimum `--env-file /etc/app/env` with a root-owned 0600 file on the host, plus CI secret masking.

4. **Secret rotation is coupled to a code change** — rotating a credential means editing deploy.sh and merging to main, which itself triggers a deploy. That makes emergency rotation slow and noisy.

5. **`sk_live_abc123` looks like a live payment/provider key** — the blast radius of the CI-log leak is financial, not just data.

6. **`hunter2` is a weak/joke password** for the production database, independent of the leak.

7. **CI holds an unrestricted SSH shell to prod.** `ssh prod-1 "docker ..."` means the CI system has a key that can run arbitrary commands (and docker access = root-equivalent on the host). Compromise of CI, of the repo (anyone who can merge to main runs arbitrary code as this deploy), or of any pipeline dependency = full prod + DB compromise. Mitigations: restricted key (`command=` forced command in authorized_keys), a dedicated deploy user, or invert to a pull-based deploy (agent on host polls registry) so CI holds no prod credentials.

8. **Anyone who can merge to main can exfiltrate the secrets and own prod** — the deploy script runs on merge with no additional approval, environment protection, or review gate on the deploy step itself.

9. **SSH host-key handling unspecified.** Either the first run fails on host-key verification, or (more likely in CI) `StrictHostKeyChecking=no` is set somewhere, which enables MITM of the deploy channel that carries the secrets.

10. **Registry auth not shown** — no `docker login`; either the registry is unauthenticated (anyone can push `registry/app:latest` = trivial supply-chain takeover of prod, since prod blindly pulls and runs `latest`), or credentials sit in plaintext `~/.docker/config.json` on prod and in CI.

11. **No image integrity controls:** no digest pinning, no signing/verification (cosign/Notary), no vulnerability scanning in the pipeline. Prod runs whatever the mutable tag points at.

12. **Container hardening absent:** no `--read-only`, no `--cap-drop`, presumably running as root in the container, no resource limits — one compromised or leaking app process can take the whole host, which is also the database host.

---

## D. Architecture / operability

1. **Single prod host = single point of failure.** Any hardware failure, kernel panic, disk death, or fat-fingered command on prod-1 is a total outage. It also structurally prevents zero-downtime deploys.

2. **Postgres colocated on the same host is the worst risk in the whole setup:**
   - Losing prod-1 loses the **application and the data simultaneously**.
   - **No backups are mentioned anywhere.** If there are none, the entire production dataset exists as a single copy on one machine. This is a potential company-ending failure mode and should be fixed before anything else except the secret rotation: automated dumps/WAL archiving (pgBackRest/wal-g) to off-host storage, restore drills, and ideally move Postgres to a managed service or separate host.
   - The app and DB compete for CPU/RAM/disk; a runaway app container (no resource limits, see C12) can OOM or disk-fill the database.
   - Docker operations during deploys (image pulls filling disk) can destabilize the DB.

3. **Disk exhaustion over time:** no `docker image prune` — every deploy leaves the old image behind; and the default `json-file` log driver has no rotation configured (`--log-opt max-size/max-file`), so container logs grow unboundedly. Both eventually fill the disk **shared with Postgres**.

4. **No monitoring or alerting mentioned.** Combined with no healthcheck and no restart policy, the detection mechanism for outages is customers. Minimum: uptime check on a health endpoint with paging, host disk/memory alerts, DB alerts.

5. **No log strategy:** when the container is removed on the next (fixed) deploy, its logs go with it; nothing ships logs off-host, so post-incident debugging after a host loss is impossible.

6. **No environment separation implied** — this deploys straight to prod on merge with no staging bake, and the only host is prod, so there is nowhere to test the deploy script itself (evidenced by bug A2 apparently never having been hit or having been worked around by hand).

7. **Config baked into the deploy script** (secrets, host name) rather than per-environment config; adding a second host or a staging env requires editing the script.

---

## E. What "good enough" looks like (prioritized)

1. **Today:** rotate `DB_PASSWORD` and `API_KEY` (they are burned); set up off-host Postgres backups and verify a restore.
2. **This week:** fix the script — `set -eu`; `docker build -t registry/app:$GIT_SHA && docker push` that tag; on the host `docker pull` the SHA tag, start the new container (`--rm` on old / `docker rm -f app` before run, or better, run new alongside old and cut over), `--restart unless-stopped`, `--env-file` or secrets manager instead of `-e`, log rotation opts, then **health-check with retries and fail the pipeline (and restore the old container) if unhealthy**; add a CI concurrency lock; mask CI secrets; prune old images.
3. **This month:** move secrets to a secret manager; restrict the CI SSH key to a forced command or go pull-based; add monitoring/alerting; record deploys (tag + timestamp) somewhere durable; define a real rollback = `deploy <old-sha>`; document the DB migration/rollback policy.
4. **Next:** second app host or managed platform behind an LB for zero-downtime deploys and host-failure tolerance; Postgres off the app host (managed if possible); staging environment; image scanning/signing.
