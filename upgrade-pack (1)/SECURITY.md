# Security Policy (upgrade pack)
## Reporting a Vulnerability
- Please raise an issue labelled `security` or contact security@example.com.
- Provide reproduction steps, impact, and suggested fixes.

## Security Controls included
- CodeQL workflow (static analysis)
- Dependabot config for dependency updates
- Basic runtime probes and resource limits in k8s manifests
- Dockerfile multi-stage production build to avoid dev dependencies in runtime
