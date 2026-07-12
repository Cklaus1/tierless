# Infra / deploy review

Review this deployment setup for a production web service. Find every real problem — reliability,
security, operability, rollout safety. Be specific to what's shown.

```yaml
# deploy.sh (run by CI on merge to main)
#!/bin/sh
docker build -t app:latest .
docker push registry/app:latest
ssh prod-1 "docker pull registry/app:latest && docker stop app && docker run -d --name app \
  -e DB_PASSWORD=hunter2 -e API_KEY=sk_live_abc123 registry/app:latest"

# healthcheck: none
# there is 1 prod host (prod-1). DB is a single Postgres on the same host.
# rollback procedure: re-run an old deploy.sh by hand.
# secrets: passed as -e flags above; also echoed in CI logs.
```
