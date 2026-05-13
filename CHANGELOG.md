# Changelog

All notable changes to this project are documented here. Format roughly
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the
project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Frontend test suite (`vitest` + Testing Library) with 10 baseline tests
  covering the agent API client and the BakeoffCard component.
- CI now runs `npm test` on every push.
- CI now runs `docker compose config --quiet` to validate the compose file
  + Dockerfile paths on every push, catching wiring typos before release.
- `release.yml` now creates a GitHub Release entry with auto-generated
  notes on every `v*` tag push (was: tag only, no Release page).

## [0.3.1] — 2026-05-12

**First complete release.** All three Docker images publish to GHCR.

### Fixed
- Backend image build failed in v0.3.0 because `COPY RAG/` referenced a
  gitignored directory. `RAG/converted_markdown/*.md` is now committed (it
  is public TEP literature, not secret), and the `.gitignore` rule was
  narrowed to `RAG/*` with explicit re-includes.

### Published images
```
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/backend:v0.3.1
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/console:v0.3.1
ghcr.io/chennanli/agent_orchestration_rootcauseanalysis/frontend:v0.3.1
```

## [0.3.0] — 2026-05-12  *(broken — use v0.3.1)*

**Do not use this tag.** The release workflow succeeded for `frontend` and
`console` but the `backend` image build failed (gitignored `RAG/` path).
The two published images are left in place for historical accuracy; pulling
`backend:v0.3.0` will 404.

### Added (the intended scope of this release)
- Three-image CI/CD: backend / console / frontend all built and pushed to
  GHCR on every `v*` tag (`release.yml` matrix build).
- `docker-compose.yml` orchestrating the full stack — `docker compose up`
  is now the recommended way to run the demo.
- README quick-start section with API-key signup links and a "Published
  images" subsection listing the GHCR paths.
- New `Dockerfile.console` with a slim ~150 MB image (was pulling the
  whole 1.5 GB requirements.txt).
- `frontend/Dockerfile` rewritten to build from REPO_ROOT context (fixes a
  pre-existing build-context contradiction).
- `BACKEND_INGEST_URL` and `UNIFIED_CONSOLE_URL` env vars so the three
  containers can resolve each other by service name.

## [0.2.x]

Pre-CD work — see `git log` for the granular history. Highlights:

- 8 business-logic tests for the agent tools (PCA detection on fault1,
  policy gate on control-style phrasing, KB retrieval).
- 6 backend import-smoke tests; CI fully wired (`ci.yml`).
- Misc tab (export-as-Markdown, email, operator notes, KB upload).
- "Naive LLM vs NAT agent" bake-off feature.
- Follow-up chat respects the originally-selected model + BYOK API key.

[Unreleased]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/releases/tag/v0.3.1
[0.3.0]: https://github.com/chennanli/Agent_Orchestration_RootCauseAnalysis/releases/tag/v0.3.0
