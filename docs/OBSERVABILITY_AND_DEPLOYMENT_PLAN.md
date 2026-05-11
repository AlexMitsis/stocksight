# Observability & Deployment Plan

**Status:** Planned  
**Last Updated:** 2026-05-09  
**Target Epic:** EPIC 5 — Production Readiness

---

## Overview

This document outlines the infrastructure-as-code, CI/CD pipeline, and observability stack for the Stock Analysis Platform. The approach is designed for a hobby-project budget while remaining production-grade.

### Core Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cloud Provider | Azure | Existing subscription |
| IaC Tool | Azure Bicep | Native Azure, idempotent, what-if validation |
| Container Platform | Azure Container Apps (ACA) | Serverless, cheaper than AKS, revision-based blue-green |
| Observability Stack | Prometheus + Grafana (self-hosted) | $0 cost, already have `/metrics` endpoint |
| Monitoring Agent | None (Prometheus scrape) | Avoids Dynatrace $69/host/mo cost |
| CI/CD | GitHub Actions | Already have basic CI, extend with CD |
| Environments | Dev + Production | 2 environments, manual gate for production |
| Cost Controls | Azure Budget Alerts | Prevent surprise bills |

---

## Infrastructure as Code (Azure Bicep)

### Directory Structure

```
infra/
├── main.bicep                      # Top-level orchestration
├── modules/
│   ├── container-apps.bicep        # ACA environment + backend/frontend apps
│   ├── postgres.bicep              # PostgreSQL Flexible Server (pgvector)
│   ├── redis.bicep                 # Azure Cache for Redis (Standard tier)
│   ├── acr.bicep                   # Container Registry
│   ├── log-analytics.bicep         # Log Analytics workspace
│   ├── key-vault.bicep             # Secrets (API keys, connection strings)
│   ├── front-door.bicep            # Azure Front Door (CDN, WAF, SSL)
│   ├── network.bicep               # VNet, subnets, NSGs, private endpoints
│   ├── managed-identity.bicep      # OIDC for GitHub Actions
│   └── cost-management.bicep       # Budget alerts
├── parameters/
│   ├── dev.bicepparam
│   └── prod.bicepparam
└── scripts/
    └── deploy.sh                   # az deployment with what-if validation
```

### Architecture

```
                              Azure Front Door
                           (CDN, WAF, SSL, routing)
                                  │
                     ┌────────────┴────────────┐
                     │                         │
              Backend ACA                 Frontend ACA
            (FastAPI, port 8888)       (Vite/React, port 3000)
                     │
          ┌──────────┼──────────┐
          │          │          │
   PostgreSQL     Redis     Prometheus + Grafana
   (Flexible)   (Cache)    (self-hosted in ACA)
```

### Resource Details

| Resource | Dev SKU | Prod SKU | Estimated Cost (Dev) |
|----------|---------|----------|---------------------|
| ACA — Backend | B2S (1 replica) | B2S (2 replicas) | ~$30/mo |
| ACA — Frontend | B2S (1 replica) | B2S (2 replicas) | ~$30/mo |
| ACA — Prometheus | B2S (1 replica) | B2S (1 replica) | ~$15/mo |
| PostgreSQL | Burstable B1ms (2 vCores) | B2ms (4 vCores) | ~$25/mo |
| Redis | Standard C1 (1 GB) | Standard C2 (2.5 GB) | ~$50/mo |
| ACR | Basic | Basic | ~$5/mo |
| Front Door | Standard | Standard | ~$35/mo |
| Key Vault | Standard | Standard | ~$3/mo |
| Log Analytics | Pay-as-you-go | Pay-as-you-go | ~$10/mo |
| **Total** | | | **~$203/mo** |

### Deployment Script

`infra/scripts/deploy.sh` will:
1. Run `az deployment group what-if` to preview changes
2. Run `az deployment group create` to apply
3. Output resource IDs for CI/CD consumption
4. Handle idempotent updates (same script, any env)

---

## CI/CD Pipeline (GitHub Actions)

### Workflow Structure

```
.github/workflows/
├── ci.yml                  # PR validation (enhanced existing)
├── cd.yml                  # Build + deploy (new)
└── dependabot.yml          # Dependency updates (new)
```

### `ci.yml` — Pull Request Validation

Triggers on PR to `main` and push to `main`.

| Job | What it does | Notes |
|-----|-------------|-------|
| backend-tests | pytest with coverage | Existing |
| backend-lint | black + flake8 | Existing |
| backend-typecheck | mypy | Existing |
| frontend-tests | vitest with coverage | Existing |
| frontend-lint | ESLint | Existing |
| frontend-typecheck | tsc --noEmit | Existing |
| integration-test | docker-compose up, API smoke test | **New** — spins up real Postgres + Redis |
| security-scan | pip-audit + npm audit + Trivy | **New** |
| all-checks | Gate requiring all above | Existing (extend) |

### `cd.yml` — Continuous Deployment

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev, production]
```

**Job 1: Build & Scan**
- Docker Buildx (multi-arch)
- Log in to ACR via OIDC (no static secrets)
- Build backend + frontend images
- Tag with git SHA + env
- Trivy scan (fail on critical/high)
- Push to ACR

**Job 2: Deploy Dev** (auto on push to main)
- Environment: `dev` (no approval)
- Bicep what-if + deploy (idempotent)
- Run Alembic migrations (ephemeral job)
- Update ACA revision with new image
- Smoke test (health + chat API)
- Grafana annotation: mark deployment

**Job 3: Deploy Production** (manual dispatch only)
- Environment: `production` (requires approval)
- Same steps as dev with prod parameter file
- Uses prod Azure credentials from GitHub Secrets

### GitHub Environments Configuration

| Setting | Dev | Production |
|---------|-----|------------|
| Auto-deploy | Yes (push to main) | No (manual dispatch) |
| Required reviewers | No | Yes (2 reviewers) |
| Azure credentials | Dev SP | Prod SP |
| Waits for approval | No | Yes |

---

## Observability Stack (Prometheus + Grafana)

### Architecture

```
 ┌─────────────────────────────────────────────┐
 │              Grafana (ACA)                   │
 │  Dashboards: Latency, Errors, LLM Costs,    │
 │  Cache Hit Rate, DB Performance              │
 └────────────┬────────────────────────────────┘
              │ queries
 ┌────────────▼────────────────────────────────┐
 │           Prometheus (ACA)                   │
 │  Scrapes: /metrics (FastAPI),               │
 │  pg_exporter, redis_exporter                │
 └────────────┬────────────────────────────────┘
              │ scrape targets
    ┌─────────┼──────────┐
    │         │          │
 FastAPI   PostgreSQL   Redis
/metrics   pg_exporter  redis_exporter
```

### Existing Metrics (already in `backend/app/services/metrics.py`)

| Metric | Type | Description |
|--------|------|-------------|
| `rag_pgvector_retrieval_duration_seconds` | Histogram | pgvector retrieval time |
| `rag_chunks_retrieved` | Histogram | Number of context chunks |
| `rag_relevance_score` | Histogram | Cosine similarity scores |
| `rag_token_savings_ratio` | Gauge | Token savings from caching |
| `rag_storage_duration_seconds` | Histogram | Embedding storage time |
| `rag_storage_errors_total` | Counter | Storage failures |
| `rag_storage_success_total` | Counter | Successful storage operations |

### New Metrics to Add

| Metric | Type | Description |
|--------|------|-------------|
| `http_request_duration_seconds` | Histogram | Per-endpoint latency (p50, p95, p99) |
| `http_requests_total` | Counter | Request count by method, path, status |
| `http_requests_in_flight` | Gauge | Concurrent requests |
| `llm_token_usage_total` | Counter | Total LLM tokens consumed |
| `llm_token_cost_total` | Counter | Estimated cost (optional) |
| `cache_hit_ratio` | Gauge | LangCache hit rate |

### Grafana Dashboards

**Dashboard 1: Application Overview**
- Request rate (RPS), error rate, p50/p95/p99 latency
- Active users (by JWT count)
- Top slowest endpoints

**Dashboard 2: LLM & RAG**
- Token usage over time
- RAG retrieval duration
- Cache hit ratio
- Cost estimation

**Dashboard 3: Infrastructure**
- PostgreSQL connections, query time
- Redis memory, hit rate
- ACA CPU/memory per revision

**Dashboard 4: Business**
- Signups, daily active users
- Chat sessions per user
- Portfolio operations

### Grafana Alerts

- Error rate > 1% over 5min → Slack/Email
- p95 latency > 2s over 5min → Slack/Email
- Cache hit rate < 50% → Warning (Slack)
- PostgreSQL connections > 80% → Critical
- Token spend rate anomaly → Info

### Local Dev Variant

Added to `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  ports: ["9090:9090"]
  volumes: ["./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml"]

grafana:
  image: grafana/grafana:latest
  ports: ["3001:3000"]
  volumes: ["./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards"]
  depends_on: [prometheus]
```

---

## Files to Create / Modify

### New Files (~19)

| File | Purpose |
|------|---------|
| `infra/main.bicep` | Top-level Bicep orchestration |
| `infra/modules/container-apps.bicep` | ACA environment + apps |
| `infra/modules/postgres.bicep` | PostgreSQL Flexible Server |
| `infra/modules/redis.bicep` | Azure Cache for Redis |
| `infra/modules/acr.bicep` | Container Registry |
| `infra/modules/log-analytics.bicep` | Log Analytics workspace |
| `infra/modules/key-vault.bicep` | Secrets management |
| `infra/modules/front-door.bicep` | CDN + WAF |
| `infra/modules/network.bicep` | VNet + private endpoints |
| `infra/modules/managed-identity.bicep` | OIDC identities |
| `infra/modules/cost-management.bicep` | Budget alerts |
| `infra/parameters/dev.bicepparam` | Dev parameter values |
| `infra/parameters/prod.bicepparam` | Prod parameter values |
| `infra/scripts/deploy.sh` | Deployment script |
| `.github/workflows/cd.yml` | CD pipeline |
| `.github/dependabot.yml` | Auto-dependency updates |
| `frontend/Dockerfile` | Production Dockerfile (only dev exists) |
| `monitoring/prometheus.yml` | Prometheus scrape config |
| `monitoring/grafana/dashboards/*.json` | Pre-built dashboards |

### Modified Files (~7)

| File | Change |
|------|--------|
| `.github/workflows/ci.yml` | Add integration test + security scan jobs |
| `backend/app/core/config.py` | Add Prometheus/Grafana settings |
| `backend/app/main.py` | Add HTTP metrics middleware |
| `docker-compose.yml` | Add Prometheus + Grafana services |
| `.env.example` | Add observability env vars |
| `backend/pyproject.toml` | Add prometheus-client if missing |

---

## Implementation Order

| Phase | Tasks | Depends On |
|-------|-------|------------|
| **Phase 1: CI Enhancements** | Enhance `ci.yml` with integration test + security scan. Create `dependabot.yml`. | Nothing |
| **Phase 2: Production Dockerfile** | Create `frontend/Dockerfile`. | Nothing |
| **Phase 3: Local Observability** | Add Prometheus + Grafana to `docker-compose.yml`. Add HTTP metrics middleware. Verify in dev. | Phase 1 |
| **Phase 4: Bicep Modules** | Create all `infra/` files. Test locally with what-if. | Nothing (parallel with 1-3) |
| **Phase 5: CD Pipeline** | Create `cd.yml`. Wire up ACR push + ACA deploy. Test with dev environment. | Phase 2, Phase 4 |
| **Phase 6: Production Cutover** | Configure production parameters, GitHub Environments, approvals. Deploy to production. | Phase 5 |

---

## Prerequisites (One-Time Azure Setup)

1. **Azure Subscription** — Already exists
2. **Service Principals** — One for dev, one for prod with OIDC federation:
   ```
   az ad sp create-for-rbac --name "stockanalysis-dev" --role Contributor \
     --scopes /subscriptions/{sub-id}/resourceGroups/{rg-dev}
   ```
3. **GitHub Secrets** (configured in repo Settings → Secrets and variables → Actions):
   - `AZURE_CLIENT_ID_DEV` / `AZURE_CLIENT_ID_PROD`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - Any API keys for smoke tests
4. **Azure Container Registry** — Created before first CD run
5. **GitHub Environments** — Create `dev` and `production` with protection rules

---

## Open Issues / Pending Clarifications

1. **Azure Cache for Redis + RediSearch** — RediSearch module is only available in Redis Enterprise tiers which may be too expensive for a hobby project. If RediSearch isn't critical for LangCache semantic caching, we can use Standard tier and lose semantic caching. Need to verify LangCache's RediSearch dependency.

2. **Private networking cost** — VNet + private endpoints for PostgreSQL/Redis add ~$20-40/mo for the private link endpoints alone. Skipping private networking (using firewall rules instead) saves cost but is less secure. Need to assess risk tolerance for a hobby project.

3. **pgvector on Azure PostgreSQL** — Azure Database for PostgreSQL Flexible Server supports the `pgvector` extension. Need to confirm it's available on the Burstable B1ms tier (requires the `azure.extensions` server parameter).

4. **Front Door vs. direct ACA access** — Azure Front Door Standard (~$35/mo) may be overkill for a hobby project. Alternative: use ACA's built-in ingress with managed TLS certs ($0). Trade-off: no WAF, no CDN. Worth reconsidering once cost is factored in.

5. **Prometheus data retention** — Default Prometheus retention is 15 days locally. For longer retention, we'd need persistent storage (ACA file share) or Thanos. 15 days is likely fine for a hobby project, but we should confirm.

6. **CI/CD secrets rotation** — Service principal credentials should be rotated periodically. OIDC federation helps (no static secrets for GitHub), but the Azure federated credential config needs maintenance. Not yet planned.

7. **Disaster recovery** — No backup strategy documented yet. PostgreSQL Flexible Server supports automated backups (point-in-time restore, 7-35 day retention). Should confirm retention policy and whether backups are enabled by default.

8. **Domain name / SSL** — Need a custom domain for production. Azure Front Door or ACA ingress can handle SSL termination. Not yet specified if a domain is owned or needs to be purchased.

9. **Cost of running dev 24/7** — Estimated ~$203/mo for dev. Could reduce by stopping dev ACA outside of working hours or scaling to 0 replicas. Should decide if dev stays always-on or is started on-demand.

10. **Grafana provisioning** — Dashboards should be version-controlled as JSON (provisioned via config maps or mounted files). Need to decide if we use Grafana's provisioning API or manual dashboard creation.

11. **PostgreSQL Flexible Server compute tier** — Burstable B1ms may throttle under sustained load. For a hobby project with light usage this should be fine, but worth monitoring.

12. **ACA Dynatrace extension** — Since we chose Prometheus + Grafana over Dynatrace, the ACA Dynatrace extension is not needed. This reduces complexity and cost. No action required.

---

## Future Improvements (Post-MVP)

- **MCP Integration** — Story 5.2: TradingView chart MCP integration
- **Automated rollback** — ACA revision history allows reverting to previous revision. Should add rollback job to CD pipeline.
- **Performance testing** — Load test with k6 or locust before production cutover
- **Secrets rotation automation** — GitHub Actions workflow that rotates service principal credentials on a schedule
- **Multi-region failover** — ACA supports multiple regions, but adds significant cost
- **Log aggregation** — Add Loki to the Grafana stack for centralized log search instead of only Log Analytics
- **Synthetic monitoring** — Set up Grafana synthetic monitoring or a simple health-check cron job for uptime tracking
