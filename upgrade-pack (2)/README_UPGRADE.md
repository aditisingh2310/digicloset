        # Upgrade Pack - Enterprise Readiness
        This upgrade pack contains files to close gaps identified in the original repository:
        - Automated tests scaffolding (frontend & backend)
        - GitHub Actions CI (lint, tests, dependency scan, container scan)
        - Basic Kubernetes manifests + Helm improvements
        - Documentation: ARCHITECTURE.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md
        - Standardized .env.example and developer requirements
        - Lint config for TypeScript and Python

How to use:
        1. Inspect the files in this pack and merge them into your repo (preferably on a new branch).
        2. Tweak the CI secrets (SNYK_TOKEN, DOCKERHUB_USERNAME/PA, etc) in GitHub repo settings.
        3. Run the CI and fix any issues the scanners/tests highlight.

