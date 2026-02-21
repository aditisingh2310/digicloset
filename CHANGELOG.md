# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Intelligent Recommendations**: Integrated OpenCLIP (ViT-B-32) for multimodal semantic image embeddings.
- **Vector Storage**: Integrated local FAISS (Facebook AI Similarity Search) index for efficient and free similarity search.
- **Project Governance**: Established `REPOSITORY_RULES.md` update, `docs/model_registry.yaml`, and updated `README.md` with new governance framework (Cost Tracking, Model Registry, Experimentation Protocols).
- **CI/CD**: Added backend build jobs to `.github/workflows/docker-image.yml` to ensure backend services are built and tested in the CI pipeline.
- **Scripts**: Added `local_verification.ps1` PowerShell script to facilitate local testing of Docker builds for all services (model-service, backend) in both upgrade packs.
- **Documentation**: Added maintainer information for Aditi Singh to `package.json`, `README.md`, and `CONTRIBUTING.md`.
- **Backend Configuration**: Restored missing `requirements.txt` and `Dockerfile` for `digicloset-upgrade-pack/backend` and `digicloset-upgrade-pack-complete/backend`.
- **Model Service Configuration**: Restored missing `requirements.txt` for `digicloset-upgrade-pack/model-service` and `digicloset-upgrade-pack-complete/model-service`.
- **Security Middleware**: SSRF protection, magic-byte MIME validation, file extension allowlist, path traversal guards, and input sanitization.
- **Rate Limiting**: `slowapi` integration with per-endpoint limits (10/min cross-sell, 5/min bg-removal).
- **Performance**: Image auto-resize to 512px, SHA-256 keyed LRU cache for embeddings and colors.
- **Observability**: Prometheus-style `/metrics` endpoint, `/health` and `/ready` probes with cache statistics.
- **Architecture**: C4 model documentation (`docs/ARCHITECTURE.md`), model versioning strategy (`docs/MODEL_VERSIONS.md`).
- **Testing**: Added `test_security.py` (MIME, path traversal, size guard) and `test_performance.py` (cache, latency, metrics).

### Changed
- **Dockerfiles**: Updated `digicloset-upgrade-pack/model-service/Dockerfile` and `digicloset-upgrade-pack-complete/model-service/Dockerfile` to use correct `COPY` paths relative to the build context.
- **Workflow**: Fixed syntax error in `.github/workflows/generator-generic-ossf-slsa3-publish.yml` (removed duplicate `uses:` key).

### Fixed
- **Root Configuration**: Restored missing `package.json` in the project root to fix frontend build dependency resolution.
- **CI Pipeline**: Resolved failures in the "Docker Image CI" workflow caused by missing backend build definitions and incorrect Dockerfile paths.

## [1.0.0] - 2026-02-13
### Initialized
- Initial project structure and documentation.
