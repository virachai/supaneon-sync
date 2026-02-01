# .github/copilot-instructions.md — supaneon-sync

**Purpose:** Help an AI coding agent become productive in this repository quickly. The repo currently contains only a minimal `README.md` and no source, test, or CI manifests; treat that as the starting point.

---

## Quick snapshot ✅
- Current repo state: only `README.md` at root; no `src/`, no `tests/`, no `package.json`, `pyproject.toml`, `go.mod`, or `.github/workflows` detected.
- If you expect production code, ask clarifying questions before making assumptions.

## Immediate steps for an agent (in order) 🔧
1. Detect project language and tooling by searching for these files (in priority order):
   - `package.json`, `pnpm-workspace.yaml`, `yarn.lock` (Node)
   - `pyproject.toml`, `requirements.txt`, `Pipfile` (Python)
   - `go.mod` (Go), `Cargo.toml` (Rust), `.csproj` (Dotnet)
   - `Dockerfile`, `Makefile`, `README.md` entries
2. If a manifest exists, run the canonical build/test commands for that ecosystem and report failures. Examples:
   - Node: `npm ci && npm test` or `pnpm install && pnpm test`
   - Python: `python -m venv .venv && pip install -r requirements.txt && pytest`
   - Go: `go test ./...`
3. If no manifest is present (current repo), stop and ask the maintainers these specific questions:
   - "Which language/runtime should this project use?"
   - "What problem does `supaneon-sync` solve (expected inputs/outputs, storage, APIs)?"
   - "Are there deployment targets (Docker, services, cloud accounts)?"
4. When given direction, propose a minimal scaffold PR that includes:
   - `src/` (language-appropriate layout), `tests/`, a basic `README.md` section describing intended behavior, and a GitHub Actions workflow that runs linters and tests.
   - Example minimal CI: `pull_request` + `push` workflow that installs deps and runs tests for the chosen language.
5. Make only small, well-documented PRs. Each PR must include tests and update `README.md` if behavior changes.

## Project-specific patterns & checks (what to look for when code appears) 🔎
- Naming: search for `sync`, `poll`, `watch`, or `push` functions/commands — these usually indicate synchronization logic.
- Idempotency & retries: sync utilities should handle partial failures, retries, and deduplication; add tests for these cases.
- Configuration: prefer environment variables for secrets and service endpoints (12-factor style). Look for `config.*`, `.env`, or `settings` files.
- External integrations: identify API endpoints/credentials referenced in code and prefer stubbing/mocking them in tests rather than requiring live secrets.

## Integration points & external dependencies ⚙️
- When you find network calls, record hostnames/URLs and add TODOs to get credentials or mocked responses.
- Add integration tests gated behind an opt-in mechanism (`ENABLE_INTEGRATION_TESTS=true`) so CI remains fast for PRs.

## PR & review expectations ✅
- Create focused PRs (one small feature/bugfix per PR).
- Attach failing tests that capture the bug before the fix when possible.
- Update `README.md` and include usage examples and required env vars.
- Use Conventional Commits where applicable: `feat:`, `fix:`, `chore:`.

---

> Notes: This file reflects the repository's current minimal state (only `README.md`). If you add new files, update this document with any discovered conventions, build/test commands, and important integration endpoints.

Please review — Is there domain knowledge (APIs, expected behavior, deployment targets, or preferred language) I should capture or add examples for? 🔁