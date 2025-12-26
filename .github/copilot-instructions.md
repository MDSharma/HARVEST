
# HARVEST – Copilot Instructions

**Purpose:** Guide GitHub Copilot to generate secure, stable, and maintainable code that aligns with HARVEST’s architecture, and to **automatically review and implement** relevant **qodo-code-review** PR suggestions that improve **security** and **operational stability**.

---

## Repository Structure

- `frontend/`: Dash/React modular components for HARVEST’s UI  
- `admin/`: Admin scripts and user management utilities  
- `docs/`: Documentation (installation, deployment, schema updates)  
- `test_scripts/`: Pytest-compatible validation scripts  
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
- Validate email addresses before sending.

---

## Security & Stability Enforcement

**Copilot must prioritize security and operational stability** in all completions and reviews. Implement improvements **by default** when suggested by **qodo-code-review** unless they **conflict with HARVEST’s architecture**.

### Email Security Rules
- Use **TLS/SSL** for SMTP connections.  
- Never hardcode SMTP credentials; load from environment or secure store.  
- Validate recipient addresses and sanitize subject/body to prevent injection.  
- Use safe template rendering (e.g., Jinja2 with autoescaping).  
- Implement retry logic for transient SMTP failures; log errors without exposing credentials.

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

## qodo-code-review Integration
*(Same as before, but email-related changes must also follow these rules.)*

---

## PR Review Checklist (Email Additions)
- [ ] SMTP credentials loaded securely (env/config).  
- [ ] TLS enforced for SMTP.  
- [ ] Email templates sanitized; no injection risk.  
- [ ] Retry logic implemented for transient failures.  
- [ ] Tests added for email send logic.  
- [ ] Docs updated for email configuration.

---

*(All other sections remain as in the previous version, including security, testing, deployment, docs, etc.)*
