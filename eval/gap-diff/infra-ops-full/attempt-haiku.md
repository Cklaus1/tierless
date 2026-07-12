# Infrastructure / Deploy Review — Full Findings

## 1. Secrets Management (CRITICAL)

### 1.1 Hardcoded credentials in deploy script
The script embeds two secrets directly in plaintext:
- `DB_PASSWORD=hunter2`
- `API_KEY=sk_live_abc123`

These are visible in version control (the script itself is committed), in CI build logs (the task note says "also echoed in CI logs"), in `docker inspect` on the host, in `docker ps --env` output, and in any log aggregation that captures container start commands. Anyone with read access to the repo, CI history, or the production host can extract them.

**Impact**: Complete compromise of the database and any service protected by the API key. Credential rotation is impossible without a full redeploy audit.

### 1.2 Secrets passed via `-e` Docker flags
Even if the values were not hardcoded, passing secrets as `-e` environment variables is unsafe:
- `docker inspect <container>` exposes all environment variables to anyone who can run Docker commands on the host.
- Environment variables appear in `/proc/<pid>/environ` on the container host.
- They are inherited by child processes and may leak into logs via frameworks that dump env at startup.
- They are not rotated without rebuilding or restarting the container.

**Better approach**: Use Docker secrets, HashiCorp Vault, AWS Secrets Manager, or a similar secrets manager. Mount secrets as read-only bind-mounted files or use a sidecar pattern for secret injection.

### 1.3 Secrets echoed in CI logs
The task note explicitly states secrets are "also echoed in CI logs." This means the CI pipeline likely has `set -x` or echo statements that print the full docker run command. CI logs are often accessible to a broader set of team members, stored indefinitely, and may be indexed by third-party log aggregation services.

---

## 2. Single Point of Failure (CRITICAL)

### 2.1 Only one production host
There is exactly one host (`prod-1`). If this host goes down — hardware failure, cloud provider outage, network partition, disk full, kernel panic — the entire service is unavailable with zero redundancy. There is no load balancer, no failover, no health-based routing.

**Impact**: Any infrastructure incident causes 100% downtime. No SLA is achievable.

### 2.2 Single Postgres on the same host
The database runs on the same host as the application. This compounds the single point of failure:
- If the app consumes all disk space (logs, temp files, Docker layers), the database is affected.
- If the app consumes all memory (OOM killer), the database may be killed first or last depending on cgroup settings.
- If the app is compromised, the attacker has direct access to the database without any network boundary.
- Resource contention between app and database on CPU, memory, and I/O is unmanaged.

**Impact**: A single host failure takes down both the application and its data store simultaneously. No backup, no replication, no point-in-time recovery is described.

---

## 3. Container Health and Resilience (HIGH)

### 3.1 No health checks defined
The comment explicitly states "healthcheck: none." Docker has no way to determine if the application is actually functioning:
- The container may be running but the app process is hung.
- The app may be running but unable to connect to the database.
- Docker will not restart a container that is running but unhealthy.
- No load balancer or orchestrator can route traffic away from a broken instance.

**Impact**: The service appears "up" in monitoring while serving errors or timeouts. Recovery requires manual intervention.

### 3.2 No restart policy
The `docker run` command does not specify `--restart`. If the container crashes, it will not automatically restart. The process is dead and stays dead until someone notices and manually restarts it.

**Impact**: Any unhandled crash causes permanent downtime until manual recovery.

### 3.3 No resource limits
There are no `--memory`, `--cpus`, `--pids`, or `--ulimit` constraints. A memory leak or runaway process can:
- Consume all host memory, triggering the OOM killer and taking down the database.
- Consume all CPU, making the host unresponsive.
- Open unlimited file descriptors or child processes.

**Impact**: A single application bug can take down the entire host and its database.

---

## 4. Deployment and Rollout Safety (HIGH)

### 4.1 No rolling update or zero-downtime deployment
The script does `docker stop app` then `docker run`. This creates a guaranteed downtime window:
- Every deployment causes an outage.
- The length of the outage depends on image pull time + container start time.
- There is no way to deploy during business hours without impacting users.

**Impact**: Every deploy is a planned outage. No SLA can be maintained.

### 4.2 Uses `:latest` tag exclusively
The script builds and pushes `app:latest` and pulls `registry/app:latest`. This means:
- There is no immutable reference between build and deploy. The image tagged `latest` at build time could be overwritten by another CI run before this deploy pulls it.
- You cannot reproduce a past deployment because `latest` is mutable.
- Rollback is impossible by design — you cannot "pull an old `latest`."
- If the push fails or is interrupted, the registry may have a partial or corrupted `latest` tag.

**Impact**: Unreproducible builds, impossible rollbacks, race conditions between build and deploy.

### 4.3 No image signing or verification
There is no mechanism to verify that the image pulled from the registry is the one that was built and tested. An attacker who compromises the registry (or the CI credentials) could push a malicious image, and it would run unchallenged on production.

**Impact**: Supply chain attack vector with no detection.

### 4.4 No pre-deploy checks
The script does not:
- Verify the build succeeded (no `docker images` check after build).
- Verify the push succeeded (no `docker push` return code check).
- Verify the pull succeeded on the host.
- Check disk space, connectivity, or database reachability before deploying.

**Impact**: Silent failures — the script may appear to succeed while the container never actually started.

### 4.5 No post-deploy verification
After starting the container, there is no health check, no smoke test, no verification that the application is responding correctly. The script exits immediately after `docker run`, with no confirmation that the service is actually serving traffic.

**Impact**: A broken image can be deployed and the CI pipeline reports success.

---

## 5. Rollback Strategy (HIGH)

### 5.1 Manual rollback by re-running old script
The documented rollback procedure is "re-run an old deploy.sh by hand." This is not a procedure — it is an admission of no procedure:
- The script always uses `:latest`, so running an old script does not roll back to an old image. It pulls `latest` again.
- There is no record of which image version was running before.
- There is no way to identify which past commit/image corresponds to a known-good state.
- Manual intervention is required, increasing mean time to recovery (MTTR).
- There is no audit trail of who rolled back and when.

**Impact**: Rollback is effectively impossible as documented. Recovery from a bad deploy requires ad-hoc investigation.

---

## 6. Security (HIGH)

### 6.1 SSH to production from CI
The script uses `ssh prod-1` to deploy directly from CI. This means:
- CI has SSH access to the production host. If CI is compromised, the attacker has direct shell access to production.
- SSH keys or credentials for prod-1 are stored in CI secrets.
- There is no jump host, no bastion, no MFA, no session recording.
- The SSH connection is not authenticated via short-lived tokens or cloud IAM.

**Impact**: CI compromise = production compromise.

### 6.2 No network isolation
The application container has no network restrictions:
- No `--network` flag to isolate it from the host network.
- No firewall rules described for the host.
- The database on the same host is accessible without any network policy.

**Impact**: If the app is compromised, lateral movement to the database is trivial.

### 6.3 No container security hardening
The container runs with default settings:
- No `--read-only` flag to prevent filesystem writes.
- No `--user` flag to run as non-root.
- No `--cap-drop=ALL` to drop Linux capabilities.
- No seccomp or AppArmor profiles.

**Impact**: A container escape or app vulnerability gives the attacker full root access to the host.

### 6.4 No TLS/SSL for registry communication
The `docker push` and `docker pull` commands do not specify any TLS configuration. If the registry is accessed over HTTP, images could be tampered with in transit (man-in-the-middle).

**Impact**: Image tampering during transit.

---

## 7. Observability and Operability (HIGH)

### 7.1 No logging configuration
The `docker run` command does not specify any logging driver (`--log-driver`, `--log-opt`). This means:
- Logs go to the default JSON file driver with no size limits.
- Log files can grow indefinitely and fill the host disk.
- There is no centralized log aggregation described.
- No log rotation is configured.

**Impact**: Disk fill from logs causes service outage. No way to debug issues without SSH access.

### 7.2 No monitoring described
There is no mention of:
- Application metrics (request rate, error rate, latency).
- Infrastructure metrics (CPU, memory, disk, network).
- Alerting on any of these signals.
- Distributed tracing.

**Impact**: No visibility into system health. Incidents are detected by users, not by the team.

### 7.3 No structured logging
Without any logging configuration, there is no guarantee the application produces structured (JSON) logs that can be parsed and searched. Unstructured logs are difficult to aggregate and analyze at scale.

---

## 8. Data Safety (CRITICAL)

### 8.1 No database backups described
There is no mention of:
- Automated backups (full, incremental, or WAL archiving).
- Backup retention policy.
- Backup testing (restore drills).
- Point-in-time recovery capability.

**Impact**: Data loss is inevitable at some point (disk failure, bug, attack). Without backups, data loss is permanent.

### 8.2 No data volume persistence strategy
The `docker run` command does not use `-v` or `--mount` to persist the database data to a named volume or host path. If the container is removed, all database data is lost. Even if a volume is used (not shown), there is no backup strategy for it.

**Impact**: Container removal = data loss.

---

## 9. Error Handling and Script Robustness (MEDIUM)

### 9.1 No `set -e` in the shell script
The script does not start with `#!/bin/sh` followed by `set -e`. Without `set -e`:
- If `docker build` fails, the script continues to `docker push` (which also fails).
- If `docker push` fails, the script continues to `ssh prod-1` and may deploy a stale or broken image.
- Each command's exit code is ignored, so failures are silent.

**Impact**: Partial failures cascade into unpredictable states.

### 9.2 No idempotency or locking
If the script is run twice (accidentally or by CI retry):
- The second run stops the running container and starts a new one, potentially losing in-flight requests.
- There is no lock to prevent concurrent deployments.
- The container name `app` is hardcoded — if a previous run left a stopped container, `docker stop` may fail or succeed silently.

**Impact**: Accidental double-deploy causes unnecessary downtime.

### 9.3 No timeout on SSH command
The `ssh prod-1 "..."` command has no timeout. If the host is unresponsive, the CI job hangs indefinitely, wasting CI minutes and blocking other jobs.

**Impact**: CI resource exhaustion from hung SSH sessions.

---

## 10. Image and Build (MEDIUM)

### 10.1 No multi-stage build described
The Dockerfile (referenced by `docker build -t app:latest .`) is not shown, but the build command does not specify any build arguments, cache configuration, or multi-stage build optimization. A single-stage build that copies source code and dependencies into the image increases attack surface and image size.

### 10.2 No .dockerignore mentioned
Without a `.dockerignore`, the build context may include:
- `.git/` directory (exposing commit history, potentially secrets).
- Local dependencies, node_modules, or build artifacts.
- IDE configuration files, local environment files (.env.local).
- Test files and development dependencies.

**Impact**: Larger images, longer builds, potential secret exposure in build context.

### 10.3 No base image pinning
The Dockerfile likely uses a base image (e.g., `FROM node:latest` or `FROM python:3.12`). Using `:latest` or untagged base images means:
- Builds are non-reproducible.
- A new base image version could introduce breaking changes or vulnerabilities.
- No vulnerability scanning baseline.

**Impact**: Non-reproducible builds, unexpected breakages, security regressions.

---

## 11. Compliance and Audit (MEDIUM)

### 11.1 No deployment audit trail
There is no mechanism to record:
- Which image version was deployed and when.
- Who triggered the deployment.
- What the deployment result was.
- Any rollback events.

**Impact**: No compliance with audit requirements (SOC 2, ISO 27001, PCI-DSS). Impossible to answer "what is running in production right now?"

### 11.2 No change management
Deployments happen automatically on merge to main with no:
- Code review gate beyond the merge itself.
- Staging/pre-production environment.
- Approval workflow for production changes.
- Feature flag or gradual rollout mechanism.

**Impact**: Any merge to main immediately affects production with no safety net.

---

## Summary of Findings by Severity

| Severity | Count | Key Areas |
|----------|-------|-----------|
| CRITICAL | 4 | Hardcoded secrets, single host, single DB host, no DB backups |
| HIGH | 7 | No health checks, no restart policy, no resource limits, no zero-downtime deploy, broken rollback, SSH from CI, no container hardening |
| MEDIUM | 5 | No logging config, no `set -e`, no image pinning, no audit trail, no staging environment |

## Top Recommendations (Priority Order)

1. **Remove all hardcoded secrets** — use a secrets manager; never pass via `-e`.
2. **Add at least one more production host** with a load balancer — eliminate the single point of failure.
3. **Separate the database onto its own host** (or managed service like RDS) with automated backups and replication.
4. **Tag images with commit SHA** instead of `:latest`; never use mutable tags for production.
5. **Add health checks and `--restart=unless-stopped`** to every container.
6. **Add `set -e` and proper error handling** to the deploy script.
7. **Implement a proper rollback strategy** using immutable image tags and version tracking.
8. **Add resource limits** (`--memory`, `--cpus`) to prevent host-level resource exhaustion.
9. **Add post-deploy smoke tests** to verify the service is actually responding.
10. **Implement monitoring and alerting** for both application and infrastructure metrics.