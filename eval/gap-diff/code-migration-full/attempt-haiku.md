# Code Migration Plan: Python 2 / Django 1.8 to Python 3 / Modern Django

## Executive Summary

The leadership plan — "a rewrite in a clean new repo, launched in a big-bang cutover in 4 months" — is **dangerously wrong** on every axis. A full rewrite of a 200k-line, live SaaS with paying customers, in 4 months by a team of 6, is statistically near-certain to fail. The big-bang cutover is a single point of failure that risks the entire business. This plan pushes back hard and proposes a safer, more realistic approach.

---

## 1. Pushback on the Proposed Approach

### 1.1 "Rewrite in a clean new repo" is the wrong strategy

A greenfield rewrite of 200k lines of business logic is not a rewrite — it is a **re-implementation of a complex, customer-facing product**. The original code encodes years of edge-case handling, customer-specific quirks, and domain knowledge that no document captures. A rewrite will:

- **Miss business logic** that exists only in code (no spec exists for 200k lines).
- **Introduce new bugs** in every module, because the rewrite team does not have the same institutional knowledge as the original authors.
- **Take far longer than 4 months** for a team of 6 to do correctly. A reasonable estimate for a full rewrite of this scale is 12-18 months minimum, assuming perfect conditions that never exist.
- **Create a parallel development burden**: the team must maintain the old system while building the new one, cutting effective velocity in half.

### 1.2 "Big-bang cutover in 4 months" is unacceptable

A single-day migration of a live SaaS with paying customers carries unacceptable risk:

- **Zero rollback window**: If something breaks at cutover (and it will), customers are down immediately.
- **No gradual validation**: You cannot A/B test a full platform migration. You go live blind.
- **No customer trust**: Paying customers notice downtime or data corruption. Churn spikes.
- **No operational experience**: The team has never run the new system in production. First time is the go-live.
- **4 months is unrealistically short**: Even if the code migration were perfect (it won't be), you need time for testing, staging, load testing, security review, monitoring setup, runbook creation, and team training.

### 1.3 Team of 6 is insufficient

For a full rewrite of this scale in 4 months:
- You need at least 2 senior Django engineers, 1 backend, 1 frontend, 1 DevOps, 1 QA. That is 6 people with zero capacity for anything else.
- No one is left for bug fixes, customer support, or the existing product.
- If one person gets sick, the timeline breaks.

---

## 2. Recommended Strategy: Strangler Fig Pattern

Instead of a rewrite, use the **Strangler Fig pattern** (also called incremental migration):

1. **Migrate the Python 2 codebase to Python 3 + modern Django in place**, while the system stays live.
2. **Gradually decompose** the monolith into smaller services as you refactor.
3. **Ship continuously** — no big-bang cutover.

This approach:
- Keeps the system running throughout the migration.
- Allows gradual validation and rollback at any point.
- Lets the team learn the new stack while working on real features.
- Reduces risk dramatically.

---

## 3. Phased Migration Plan

### Phase 0: Assessment and Foundation (Weeks 1-3)

**Goal**: Understand the codebase, set up tooling, establish the migration baseline.

#### 3.1 Codebase Audit

- **Dependency inventory**: Catalog every third-party package, its Python 2 compatibility status, and modern alternatives. Django 1.8 dependencies are likely 5-10 years old. Many will need replacement.
- **Module dependency graph**: Map which modules import what. Identify circular dependencies, tightly coupled modules, and natural boundaries for decomposition.
- **Test coverage baseline**: Run existing tests (if any) and measure coverage. Expect low coverage — this is typical for Python 2/Django 1.8 codebases.
- **Database schema audit**: Document all models, custom SQL, raw queries, and data migrations. Django 1.8 ORM has known differences from modern Django.
- **Custom management commands**: Inventory all `manage.py` commands — they often contain critical business logic.
- **Middleware and custom tags/filters**: List all Django middleware, template tags, template filters, and admin customizations.
- **External integrations**: Document all API consumers, webhooks, message queue consumers/producers, and third-party service connections.

#### 3.2 Tooling Setup

- **CI/CD pipeline**: Set up automated testing, linting, and deployment for the new stack. This is critical for confidence.
- **Python 3 compatibility checker**: Run `2to3` and `python-future` tools to identify mechanical changes.
- **Static analysis**: Set up `flake8`, `mypy`, `bandit` for code quality and security.
- **Docker environment**: Containerize the application for consistent local and CI environments.
- **Feature flags**: Set up a feature flag system (e.g., flagsmith, or a simple database-backed system) to gradually roll out new functionality.

#### 3.3 Team Preparation

- **Training**: Ensure all 6 team members are proficient in Python 3 and modern Django (4.x).
- **Spike/prototype**: Have the team build a small proof-of-concept module in the new stack to validate the approach and uncover hidden complexities.

### Phase 1: Python 2 to Python 3 Migration (Weeks 3-10)

**Goal**: Get the entire codebase running on Python 3 with minimal functional changes.

#### 3.4 Python 3 Migration Steps

1. **Syntax changes** (mechanical, use `2to3` or `pyupgrade`):
   - `print` statements to `print()` functions.
   - `xrange` to `range`.
   - `dict.has_key()` to `in`.
   - Exception handling: `except Exception, e` to `except Exception as e`.
   - Integer division: `/` vs `//`.
   - Unicode: `str` is now bytes; `unicode` is now `str`. This is the **biggest source of bugs**.

2. **Standard library changes**:
   - `urllib` -> `urllib.request`, `urllib.parse`.
   - `ConfigParser` -> `configparser`.
   - `collections` changes (`iteritems`, `itervalues`, `iterkeys` removed).
   - `html` module changes.
   - `http` module restructuring.
   - `queue` instead of `Queue`.
   - `socketserver` instead of `SocketServer`.
   - `xmlrpc` changes.

3. **Third-party package migration**:
   - Replace packages that no longer support Python 3.
   - Update packages to versions compatible with Python 3 and modern Django.
   - This is often the most time-consuming part — some packages may be abandoned.

4. **Django 1.8 to Django 4.x/5.x migration**:
   - This is a **multi-step jump** (1.8 -> 2.2 -> 3.x -> 4.x/5.x). Do NOT jump directly.
   - Each major version has breaking changes. Plan for 3-4 intermediate upgrade steps.
   - Key breaking changes to anticipate:
     - Django 2.0: Removed `u` prefix support, `django.utils.encoding.force_text` -> `force_str`, URL routing changes (path() vs url()), `MIDDLEWARE` instead of `MIDDLEWARE_CLASSES`.
     - Django 2.0: Required Python 3.5+.
     - Django 2.2: LTS release, dropped Python 2 support entirely.
     - Django 3.0: Async views support, `USE_L10N` removed.
     - Django 3.1: `JsonResponse` changes, `TestClient` changes.
     - Django 3.2: `default_auto_field` required in app configs.
     - Django 4.0: Removed `force_text`, `force_bytes` changes, `django.conf.urls.url` removed.
     - Django 4.1: `UserAttributeSimilarValidator` changes.
     - Django 4.2: LTS, `django.utils.encoding.force_str` changes.
     - Django 5.0: `USE_THOUSAND_SEPARATOR` format changes, `django.utils.encoding.force_str` changes.
     - Django 5.1: `django.utils.encoding.force_str` changes.
   - **Strategy**: Upgrade one minor version at a time, test after each step.

5. **Testing after each step**:
   - Run the full test suite after each upgrade.
   - If no test suite exists, this phase becomes significantly riskier — see Section 5.

#### 3.5 Expected Challenges

- **Unicode everywhere**: Python 3 enforces unicode correctly. The Python 2 code likely has inconsistent unicode handling. Every string operation needs review.
- **Encoding issues**: File I/O, database connections, HTTP responses — all need explicit encoding.
- **Third-party packages**: Some may not have Python 3 support at all. Need to find alternatives or fork.
- **C extensions**: Any C extensions compiled for Python 2 need recompilation for Python 3.

### Phase 2: Incremental Decomposition (Weeks 10-26)

**Goal**: Gradually break the monolith into manageable pieces while continuing to ship features.

#### 3.6 Module-by-Module Migration

- **Identify natural boundaries**: Use the dependency graph from Phase 0 to find modules that are loosely coupled.
- **Migrate one module at a time**: Rewrite or refactor each module in the new stack, test it, then switch the routing.
- **Use feature flags**: Route traffic to old or new implementation based on feature flags.
- **Data sharing**: Use the same database during migration. The old and new code coexist on the same data.

#### 3.7 Database Migration

- **Schema changes**: Django 4.x/5.x ORM has different behavior for some operations. Review:
  - `null=True` on text fields (no longer allowed on some backends).
  - Default values for nullable fields.
  - `on_delete` behavior changes.
  - `related_name` changes.
- **Data migrations**: Plan for any data format changes needed for the new ORM.
- **Database version**: Ensure the database backend is compatible with modern Django (PostgreSQL 12+ recommended).

#### 3.8 API and Integration Migration

- **Internal APIs**: Gradually migrate internal API endpoints.
- **External integrations**: Keep existing integrations working while migrating the underlying code.
- **Webhooks**: Ensure webhook handlers work during the transition.

### Phase 3: Hardening and Launch (Weeks 26-30)

**Goal**: Production readiness, monitoring, and gradual rollout.

#### 3.9 Production Readiness

- **Load testing**: Verify the new system handles production traffic.
- **Security audit**: Penetration testing, dependency vulnerability scan, code review.
- **Monitoring**: Set up logging, metrics, tracing, alerting.
- **Runbooks**: Document operational procedures for the new system.
- **Disaster recovery**: Test backup/restore procedures.

#### 3.10 Gradual Rollout

- **Canary deployment**: Route 1% of traffic to the new system.
- **Monitor**: Watch for errors, performance issues, data corruption.
- **Increase gradually**: 5%, 10%, 25%, 50%, 100%.
- **Rollback plan**: If issues arise, flip the feature flag back.

---

## 4. Risk Register

### 4.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Unicode/encoding bugs cause data corruption | High | Critical | Extensive testing, code review, automated unicode checks |
| Third-party package incompatibility | High | High | Early audit, identify alternatives, budget for custom patches |
| Data loss during migration | Medium | Critical | Full backups, migration dry-runs, point-in-time recovery |
| Performance regression | Medium | High | Load testing at each phase, APM monitoring |
| Django upgrade introduces ORM bugs | Medium | High | Test every ORM change, review release notes carefully |
| C extension incompatibility | Low | High | Early audit of C extensions, budget for recompilation |

### 4.2 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Customer churn during migration | High | Critical | Keep system running, communicate proactively, no downtime |
| Missed deadline | Very High | High | Phased approach with visible progress, adjust scope |
| Budget overrun | High | Medium | Fixed timeline means fixed cost; scope reduction is the lever |
| Key team member departure | Medium | High | Cross-train, document everything, avoid bus factor of 1 |
| Security vulnerability in new code | Medium | Critical | Security audit, dependency scanning, code review |

### 4.3 Organizational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Team burnout from dual maintenance | High | High | Clear timeline, realistic scope, management support |
| Loss of institutional knowledge | High | High | Document everything, pair programming, code reviews |
| Leadership pressure for big-bang | High | Critical | Present this document, propose phased alternative with milestones |

---

## 5. Critical Missing Information

The task description is missing critical information that must be addressed before migration can begin:

1. **Test coverage**: Does the existing codebase have automated tests? If not, the migration risk increases dramatically. A 200k-line codebase with no tests is essentially undocumented.
2. **Database technology**: What database is in use? PostgreSQL, MySQL, SQLite? This affects migration complexity.
3. **Deployment infrastructure**: On-premise, cloud, hybrid? What CI/CD exists?
4. **External API contracts**: What APIs do customers depend on? Are there SLAs?
5. **Data volume**: How much data? This affects migration time and strategy.
6. **Compliance requirements**: PCI, HIPAA, SOC 2? These affect what changes are allowed and testing requirements.
7. **Custom Django modifications**: How much of Django has been monkey-patched or subclassed?
8. **Template complexity**: Are templates using Django 1.8-specific features?
9. **Caching strategy**: Memcached, Redis, database caching?
10. **Background job system**: Celery, RQ, custom? This often contains critical async logic.

---

## 6. Realistic Timeline

The 4-month timeline is not realistic for a safe migration. Here is a more honest estimate:

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 0: Assessment | 3 weeks | Week 3 |
| Phase 1: Python 3 + Django upgrade | 8 weeks | Week 11 |
| Phase 2: Incremental decomposition | 16 weeks | Week 27 |
| Phase 3: Hardening and rollout | 4 weeks | Week 31 |
| **Total** | **~31 weeks** | **~7.5 months** |

This assumes:
- No major team changes.
- No critical customer requests that pull people off the migration.
- Test coverage is at least 40% (if lower, add 2-4 weeks for test writing).
- Third-party packages have Python 3 alternatives (if not, add 2-4 weeks).

If leadership insists on 4 months, the only viable option is to **reduce scope**: migrate only the most critical modules and leave the rest for a second phase. This is still risky but more manageable than a full rewrite.

---

## 7. Specific Recommendations

### 7.1 Do NOT do a rewrite

A rewrite of a live, complex SaaS product is one of the highest-risk engineering endeavors. History shows that most large-scale rewrites fail. The Strangler Fig pattern has a much higher success rate because:

- You get working software at every step.
- You can rollback at any point.
- You learn from the migration and improve the design.
- You don't need to rediscover all the business logic.

### 7.2 Do NOT do a big-bang cutover

Even with a perfect migration, a single-day cutover is dangerous. Use gradual rollout:

- Feature flags for module-by-module cutover.
- Canary deployments for traffic shifting.
- Parallel run for critical paths (old and new both process requests, compare results).

### 7.3 Invest heavily in testing

If the codebase lacks tests, this is the single highest-ROI investment:

- Write integration tests for critical business flows first.
- Use property-based testing for data transformation logic.
- Record and replay HTTP interactions for external APIs.
- Use contract testing for API consumers.

### 7.4 Upgrade Django incrementally

Do not jump from 1.8 to 4.x/5.x in one step. Each step:

1. Django 1.8 -> 1.11 (LTS, last to support Python 2)
2. Django 1.11 -> 2.2 (LTS, first to require Python 3)
3. Django 2.2 -> 3.2 (LTS)
4. Django 3.2 -> 4.2 (LTS)
5. Django 4.2 -> 5.x (if desired)

Each step should be tested independently.

### 7.5 Plan for the "long tail" of Python 2

Even after the migration, some Python 2 artifacts may persist:

- Legacy data formats that need conversion.
- Reports or exports that assume Python 2 string behavior.
- Customer integrations that depend on specific response formats.
- Scheduled jobs that were never tested on Python 3.

Budget time for this cleanup phase.

---

## 8. What to Tell Leadership

> "A full rewrite in 4 months by a team of 6 carries a very high risk of failure. The codebase encodes years of domain knowledge that cannot be captured in a spec. A big-bang cutover means the entire business goes live with untested code on day one.
>
> We recommend a phased migration using the Strangler Fig pattern:
>
> 1. **Month 1-2**: Migrate the codebase to Python 3 and upgrade Django incrementally. The system stays live throughout.
> 2. **Month 3-5**: Gradually refactor and decompose modules, testing each one before switching over.
> 3. **Month 6**: Hardening, load testing, and gradual production rollout.
>
> This approach keeps the system running, allows rollback at any point, and delivers working software every week. It takes approximately 7 months instead of 4, but the risk of business disruption drops from 'very high' to 'manageable'.
>
> If the 4-month deadline is non-negotiable, we can deliver a subset of modules within that timeframe, but the full migration will require additional time."

---

## 9. Summary of Key Decisions

| Decision | Recommended | Why |
|----------|------------|-----|
| Migration strategy | Strangler Fig (incremental) | Lower risk, working software at every step |
| Cutover strategy | Gradual rollout with feature flags | No single point of failure |
| Django upgrade path | Incremental (1.8 -> 1.11 -> 2.2 -> 3.2 -> 4.2 -> 5.x) | Each step has breaking changes |
| Timeline | 7 months (realistic) or 4 months with reduced scope | 4 months for full migration is unrealistic |
| Team size | 6 is minimum; 8-10 is ideal | 6 leaves no room for error |
| Testing investment | Heavy (integration + property-based) | 200k lines without tests is too risky |
| Rewrite | No | Highest-risk engineering decision possible |