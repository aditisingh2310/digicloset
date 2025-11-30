# Threat Model (concise)
## Assets
- User data, authentication tokens, static assets

## Threats
- Dependency vulnerabilities (mitigated by Dependabot + npm audit)
- RCE via unvalidated input (static analysis and runtime probes)
- Secrets leakage (recommend using secrets manager, do not commit .env)

## Mitigations
- Run SAST (CodeQL), DAST in pipeline, dependency scanning
- Use secrets manager for production secrets
- Enforce least privilege for cloud resources
