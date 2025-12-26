# HARVEST – Copilot Instructions

**Purpose:** Guide GitHub Copilot to generate secure, stable, and maintainable code that aligns with HARVEST’s architecture, and to **automatically review and implement** relevant **qodo-code-review** PR suggestions that improve **security** and **operational stability**.

---
## Table of Contents

- [Repository Structure](#repository-structure)
- [Design Principles](#design-principles)
- [Configuration & Dependency Injection](#configuration--dependency-injection)
- [Security & Stability Enforcement](#security--stability-enforcement)
- [Code Quality & Style](#code-quality--style)
- [Testing Strategy (`test_scripts/`)](#testing-strategy-test_scripts)
- [Frontend Guidelines (`frontend/`)](#frontend-guidelines-frontend)
- [Deployment Modes & Nginx](#deployment-modes--nginx)
- [Documentation Practices (`docs/`)](#documentation-practices-docs)
- [qodo-code-review Integration](#qodo-code-review-integration)
- [Copilot Behaviors & Completion Rules](#copilot-behaviors--completion-rules)
- [Automation Directive](#automation-directive)
- [PR Review Checklist](#pr-review-checklist)
- [Observability & Logging](#observability--logging)
- [Database & Migration Practices](#database--migration-practices)
- [PDF Handling & Validation](#pdf-handling--validation)
- [Performance & Resource Management](#performance--resource-management)
- [Secrets Management](#secrets-management)
- [CI/CD (Recommended)](#cicd-recommended)
- [Examples & Patterns](#examples--patterns)
- [Maintenance & Versioning](#maintenance--versioning)
- [Notes for Copilot](#notes-for-copilot)
- [Appendix: Optional Copilot Configuration Stub](#appendix-optional-copilot-configuration-stub)

---

## Repository Structure

- `frontend/`: Dash/React modular components for HARVEST’s UI  
- `admin/`: Admin scripts and user management utilities  
- `docs/`: Documentation (installation, deployment, schema updates)  
- `test_scripts/`: Pytest-compatible validation scripts
- `scripts/`: Any additional function specific scripts
- `assets/`: Static files and documentation served by HARVEST  
- `config.py`: Centralized configuration for DB paths, ports, and API keys  
- `email_config.py`: Email configuration (SMTP settings, credentials, templates)

> **Copilot must preserve** this modular separation and **avoid cross-layer coupling** (e.g., no backend internals leaking into frontend code directly; no admin utilities coupling to runtime-only services).

---

## Design Principles

- **Modularity & Separation of Concerns**: Keep backend, frontend, and admin tools isolated with clean interfaces.  
- **Explicit Configuration**: All ports, DB paths, API keys, and email settings are injected via **`config.py`** or **`email_config.py`** and environment variables. No hardcoded values.  
- **Idempotency & Stability**: Favor idempotent operations, graceful error handling, and deterministic behavior.  
- **Least Privilege & Defense-in-Depth**: Default-deny on inputs, minimal permissions, validation at boundaries.  
- **Documentation-Driven Development**: All changes that impact runtime, deployment, or schema must be documented in `docs/`.

---

## Configuration & Dependency Injection

- Read runtime values **only** via `config.py` or `email_config.py` and environment variables.  
- **Do not** hardcode SMTP credentials, ports, or email addresses.  
- Provide sensible **defaults** in config files and allow **env overrides**.

**Copilot should:**  
- Suggest secure patterns for email configuration (TLS, authentication).  
- Use dependency injection for email clients; avoid global state.
- Propose clear **fallbacks** (e.g., if env missing, log a warning and use safe defaults).
- Validate email addresses before sending.

---

## Security & Stability Enforcement

**Copilot must prioritize security and operational stability** in all completions and reviews. Implement improvements **by default** when suggested by **qodo-code-review** unless they **conflict with HARVEST’s architecture**.

### Security Rules
- **Authentication & Passwords**:  
  - Use **bcrypt** (via `bcrypt` or `passlib`) for password hashing.  
  - Never store plaintext secrets or tokens.  
- **Input Validation & Sanitization**:  
  - Validate user inputs and file paths (no path traversal; use `pathlib` safely).  
  - Enforce strict MIME/type checks for uploads, especially PDFs.  
- **File & PDF Handling**:  
  - Sanitize filenames; store under controlled directories; restrict executable bits.  
  - Validate PDFs (size limits, structure checks, fail-fast on malformed content).  
- **Database Safety**:  
  - Use parameterized queries/ORM; no string concatenation for SQL.  
  - Migrations must be **reversible** and covered by tests.  
- **Secrets Management**:  
  - Access secrets via env or secure stores only; **never** hardcode.  
- **Network/HTTP**:  
  - Enforce timeouts, retries with backoff, bounded concurrency.  
  - Validate external responses (status, schema).  
- **Subprocess & OS**:  
  - Avoid `shell=True`; sanitize arguments; handle stdout/stderr robustly.  
- **Logging**:  
  - Use structured logging with levels; **no `print`** in production code.  
  - Redact sensitive data in logs.

### Stability Rules
- **Error Handling**:  
  - Fail fast on invalid state; use exception types; actionable messages.  
- **Resource Cleanup**:  
  - Always use context managers for files, DB connections, locks.  
- **Resilience**:  
  - Add retries/circuit breakers for flaky dependencies; rate-limit as needed.  
- **Performance & Memory**:  
  - Stream large files; avoid loading entire PDFs/DB dumps unnecessarily.

---

## Code Quality & Style

- Follow **PEP8**, add **type hints**, and prefer **Pythonic idioms**: context managers, comprehensions, `dataclasses`.  
- Use `logging` instead of `print`.  
- Keep functions small and single-purpose; avoid side effects.  
- Prefer pure functions in data transforms; isolate I/O at boundaries.

---

## Testing Strategy (`test_scripts/`)

**Copilot should generate and update tests** with any code changes—especially when integrating qodo suggestions.

- **Pytest fixtures**: centralize DB setup/teardown, temp dirs, and config injection.  
- **Coverage targets**:  
  - DB migrations (forward/backward).  
  - PDF downloads & validation.  
  - Annotation workflows (create/edit/delete).  
  - API routing and asset path resolution (frontend↔backend boundary).  
- **No hardcoded DB paths**: use temp dirs and `config.py` injection.  
- **Property-based tests** (where useful) for parsers/validators.  
- **Performance tests** for large PDFs or batch operations.

---

## Frontend Guidelines (`frontend/`)

- Maintain **consistent asset paths** and **API routing** aligned with Nginx proxy rules.  
- Avoid hardcoded URLs; use env-driven base paths.  
- Handle 4xx/5xx gracefully; surface actionable messages.  
- Keep components **modular** and props **typed** (TypeScript preferred where applicable).  
- Do not embed secrets in client code; use server-side tokens/relay endpoints.

---

## Deployment Modes & Nginx

- Respect `HARVEST_DEPLOYMENT_MODE`:
  - `internal`: direct local dev server.
  - `nginx`: behind Nginx reverse proxy.

**Copilot should:**  
- Propose **Nginx configs** (secure defaults: `proxy_read_timeout`, `client_max_body_size`, `X-Forwarded-*` headers).  
- Ensure backend listens on the configured port; trust `X-Forwarded-Proto` for HTTPS-aware redirects.  
- Update `docs/DEPLOYMENT_GUIDE.md` when config/env changes are suggested.

---

## Documentation Practices (`docs/`)

- **Always update** relevant docs when code/config changes:  
  - `INSTALLATION.md` for setup prerequisites, env vars, dependencies.  
  - `DEPLOYMENT_GUIDE.md` for proxy rules and modes.  
  - `SCHEMA.md` for DB changes and migration notes.  
- Provide **migration steps** and **rollback instructions** for schema updates.  
- Include **security notes** (password policy, session lifetime, headers, CSP).

---

## qodo-code-review Integration

> Applies equally if your pipeline refers to it as **qodo-merge-pro**—align with the PR tool used in this repository.

- Treat **qodo-code-review PR suggestions** as **authoritative for security and stability**.  
- **Default to implementing** qodo recommendations unless they:  
  - Break HARVEST’s modular architecture, or  
  - Conflict with documented security requirements.
- Align completions with qodo PR diffs:  
  - Prefer **minimal, targeted changes** over large rewrites.  
  - Preserve public interfaces; refactor internals if required.  
- **Mandatory** updates with any implementation:  
  - Tests in `test_scripts/` covering new/changed behavior.  
  - Documentation in `docs/` reflecting configs, schema, or deployment impacts.  
- If a qodo suggestion conflicts, **adapt it** to fit architecture and document the adapted approach.

---

### Email Security Rules
- Use **TLS/SSL** for SMTP connections.  
- Never hardcode SMTP credentials; load from environment or secure store.  
- Validate recipient addresses and sanitize subject/body to prevent injection.  
- Use safe template rendering (e.g., Jinja2 with autoescaping).  
- Implement retry logic for transient SMTP failures; log errors without exposing credentials.

---

## Copilot Behaviors & Completion Rules

- **Code Completion**:  
  - Use secure patterns; inject config via `config.py`; avoid hardcoded paths/secrets.  
  - Prefer Python idioms and modular imports.  
- **Testing**:  
  - Generate pytest fixtures; no hardcoded DB paths; add regression tests for bug fixes.  
- **Frontend Guidance**:  
  - Suggest asset path fixes; maintain Nginx-compatible routing; avoid inline secrets.  
- **Deployment**:  
  - Propose Nginx rules when `HARVEST_DEPLOYMENT_MODE=nginx`; include timeouts/body limits.  
- **Docs**:  
  - Auto-suggest updates to `docs/DEPLOYMENT_GUIDE.md` when config/env variables change.  
- **Security First**:  
  - If a completion can be implemented securely or insecurely, **choose the secure path** and add comments explaining the choice.

---

## Copilot Behaviors for Email Features
- When generating email-related code:  
  - Use `email_config.py` for SMTP settings and credentials.  
  - Enforce TLS and authentication checks.  
  - Suggest structured logging for email send failures.  
  - Avoid inline HTML with unescaped user input; prefer safe templates.  
- Add tests for email sending logic (mock SMTP server, validate retries and error handling).  
- Update `docs/DEPLOYMENT_GUIDE.md` for email configuration changes.

---

## Automation Directive

**Goal:** Make Copilot proactively implement qodo-code-review suggestions that improve security/stability.

- **Auto-review** qodo PR diffs and propose merged completions that:  
  - Preserve HARVEST architecture and module boundaries.  
  - Improve security (validation, auth, secrets, logging) and stability (timeouts, retries, cleanup).  
  - Include **tests** and **docs** updates in the same PR.  
- When unsure, **default to the qodo recommendation** and note any architectural adaptations.  
- Add a short **PR summary** describing security/stability gains, tests added, and docs updated.

---

## PR Review Checklist

- [ ] **Security**: No hardcoded secrets; input validation; parameterized queries; bcrypt for passwords; safe file handling.  
- [ ] **Stability**: Timeouts/retries; structured error handling; resource cleanup; deterministic behavior.  
- [ ] **Architecture**: Preserves module boundaries; uses `config.py`; no cross-layer coupling.  
- [ ] **Tests**: Pytest fixtures added/updated; coverage for new paths; reversible migrations tested.  
- [ ] **Docs**: Relevant guides updated in `docs/` (installation, deployment, schema).  
- [ ] **Frontend**: Asset paths and API routing consistent with Nginx; no client-side secrets.  
- [ ] **Logging**: Structured logs; sensitive data redacted; no `print` in production code.  
- [ ] **Performance**: No unbounded memory use; streaming for large files; reasonable limits.  
- [ions with property-based tests where appropriate.

---

## PDF Handling & Validation

- Enforce file size and page count limits.  
- Validate structure; fail fast on malformed PDFs.  
- Sanitize metadata; remove active content if encountered.  
- Store under controlled paths; never execute or render untrusted embedded content server-side.

---

## Performance & Resource Management

- Use streaming APIs for large files; avoid loading entire PDFs into memory.  
- Cap concurrency; apply backpressure where needed.  
- Measure and document time/memory characteristics for heavy workflows.

---

## Secrets Management

- All secrets via environment or secure stores; rotate regularly.  
- Never log secrets; ensure redaction in error paths.  
- Provide a `SECRETS.md` (if applicable) documenting required env vars and rotation procedures.

---

## CI/CD (Recommended)

- Run linting, type checks, and tests on PRs.  
- Block merges when security/stability checks fail.  
- Auto-generate docs previews (e.g., deployment guide diffs) for config changes.

---
