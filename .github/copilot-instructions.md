## Repository Structure
- `frontend/`: Dash/React modular components for HARVEST’s UI
- `admin/`: Admin scripts and user management utilities
- `docs/`: Documentation (installation, deployment, schema updates)
- `test_scripts/`: Pytest-compatible validation scripts
- `assets/`: Static files and documentation served by HARVEST
- `config.py`: Centralized configuration for DB paths, ports, and API keys

## Key Guidelines
1. Follow **Python best practices** (PEP8, type hints, logging instead of print).
2. Maintain modular separation of backend, frontend, and admin tools.
3. Use **dependency injection via `config.py`** for ports, DB paths, and API keys.
4. Document all changes in `docs/` and consolidate guides (INSTALLATION, DEPLOYMENT, SCHEMA).
5. Respect deployment modes (`internal`, `nginx`) and suggest correct proxy configs.
6. Enforce **security** (bcrypt for admin passwords, PDF validation, input sanitization).
7. Generate **pytest-compatible tests** for DB migrations, PDF downloads, and annotation workflows.
8. When frontend code is modified, ensure **asset paths and API routing** remain consistent with Nginx proxy rules.
9. Prefer **Python idioms** (context managers, comprehensions, dataclasses) for backend code.
10. When documenting or suggesting changes, update the `docs/` folder with consolidated guides.

## qodo-merge-pro Integration
- Always **consider qodo-merge-pro PR suggestions** when generating completions.
- Treat qodo-merge-pro recommendations as authoritative unless they conflict with HARVEST’s architecture or security guidelines.
- When merging PR code suggestions, ensure:
  - Code remains consistent with HARVEST’s modular structure.
  - Documentation updates are reflected in `docs/`.
  - Tests in `test_scripts/` validate new functionality.
- Copilot should **adapt completions to align with qodo-merge-pro PR diffs**, offering context-aware improvements rather than overwriting.

## Copilot Behaviors
- **Code Completion**: Prefer Python idioms and modular imports.
- **Testing**: Generate pytest fixtures and avoid hardcoded DB paths.
- **Frontend Guidance**: Suggest React/Dash asset path fixes, avoid hardcoding URLs.
- **Deployment**: Propose Nginx configs when `HARVEST_DEPLOYMENT_MODE=nginx`.
- **Docs**: Auto-suggest updates to `docs/DEPLOYMENT_GUIDE.md` when config/env variables change.
