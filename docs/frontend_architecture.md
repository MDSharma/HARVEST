# Frontend Architecture

## Overview

The HARVEST frontend has been refactored from a single 5600+ line file (`harvest_fe.py`) into a modular package structure under `frontend/` for better maintainability and organization.

## Package Structure

```
frontend/
├── __init__.py           # App initialization, config loading, callback validation
├── markdown.py           # Markdown file caching and monitoring
├── layout.py             # UI layout building functions  
├── server_routes.py      # Flask routes (PDF proxy, ASReview proxy, etc.)
└── callbacks.py          # All Dash callbacks (can be split further)

harvest_fe.py             # Thin compatibility wrapper for backwards compat
wsgi_fe.py                # WSGI entry point (unchanged, imports from harvest_fe)
```

## Module Responsibilities

### `frontend/__init__.py`
- **Bytecode cache clearing**: Prevents stale callback registration issues
- **Configuration loading**: Loads from `config.py` with environment variable overrides
- **App creation**: Initializes Dash app with proper routing configuration
- **Callback validation**: Runtime guard preventing callbacks from updating forbidden markdown info-tab IDs
- **Module orchestration**: Imports layout, routes, and callbacks in correct order

Key exports:
- `app`: The Dash application instance
- `server`: The underlying Flask server (for WSGI deployment)
- `markdown_cache`: The MarkdownCache instance
- Configuration constants: `API_BASE`, `SCHEMA_JSON`, `APP_TITLE`, etc.

### `frontend/markdown.py`
- **MarkdownCache class**: Thread-safe caching of markdown files
- **File watching**: Uses watchdog to monitor `.md` files for changes
- **Schema injection**: Replaces `{SCHEMA_JSON}` placeholder in schema.md
- **HTML rendering**: Allows HTML in participate.md for iframe embedding

The markdown cache loads content at app startup and watches for file changes in development. The 5 info-tab markdown files (`annotator_guide.md`, `schema.md`, `admin_guide.md`, `db_model.md`, `participate.md`) are loaded into the layout statically and **never** updated by callbacks.

### `frontend/layout.py`
- **`create_execution_log_display()`**: Formats literature search pipeline execution logs
- **`sidebar()`**: Builds the sidebar with info tabs (Annotator Guide, Schema, Admin Guide, Database Model, Participate)
- **`get_layout()`**: Builds and returns the complete application layout

The layout includes:
- `dcc.Store` components for client-side state management
- Modals (Privacy Policy, Web of Science syntax help, delete confirmation, upload, etc.)
- Main tabs (Dashboard, Annotate, Browse, Admin, Literature Search)
- Header with logo and navigation
- Footer with partner logos (if configured)

### `frontend/server_routes.py`
Flask routes for server-side operations:
- **`/proxy/pdf/<project_id>/<filename>`**: Proxies PDF requests from frontend to backend
- **`/pdf-viewer`**: Serves PDF viewer HTML page
- **`/proxy/highlights/<project_id>/<filename>`**: Stores/retrieves PDF highlight annotations
- **`/proxy/asreview/<path:path>`**: Proxies requests to ASReview Literature Review service

These routes keep the backend internal (127.0.0.1:5001) while allowing the frontend to serve content to remote clients.

### `frontend/callbacks.py`
All 68 Dash callbacks for interactivity, including:
- **Email/OTP verification**: Validates contributor email and OTP codes
- **Literature search**: Interfaces with literature_search.py for paper discovery
- **DOI validation**: Validates and fetches metadata for DOIs
- **Triple annotation**: Manages entity and relation triple creation
- **Project management**: Admin functions for projects and DOI lists
- **Browse interface**: Queries and displays existing annotations
- **Dashboard statistics**: Shows annotation counts and recent activity

**TODO**: This can be further split into domain-specific modules:
- `callbacks_annotation.py`: Email, OTP, triples, DOI
- `callbacks_dashboard.py`: Stats, recent data, quick actions
- `callbacks_admin.py`: Admin login, projects, triple editor
- `callbacks_browse.py`: Browse tab queries
- `callbacks_literature.py`: Literature search and ASReview
- `callbacks_ui.py`: Modals, privacy policy

## Backwards Compatibility

### `harvest_fe.py`
A thin wrapper that imports and re-exports from the `frontend` package:
```python
from frontend import app, server, markdown_cache
```

This maintains backwards compatibility for:
- Direct imports: `from harvest_fe import server`
- Development server: `python harvest_fe.py`
- WSGI deployment: `gunicorn wsgi_fe:server`

### `wsgi_fe.py`
Unchanged. Still imports from `harvest_fe`:
```python
from harvest_fe import server
```

## Callback Guard

A key feature added in this refactor is runtime validation that **no callback outputs to the 5 forbidden markdown info-tab IDs**:
- `annotator-guide-content.children`
- `schema-tab-content.children`
- `admin-guide-content.children`
- `dbmodel-tab-content.children`
- `participate-tab-content.children`

This guard runs after all callbacks are registered and raises a `RuntimeError` if any violation is found. This prevents the production `KeyError` issues caused by stale multi-output callbacks updating these IDs.

The guard can be disabled by setting:
```bash
export HARVEST_STRICT_CALLBACK_CHECKS=false
```

But it defaults to `true` in production to prevent regression.

## Configuration

Configuration is loaded in this order:
1. Import from `config.py` (if available)
2. Override with environment variables
3. Validate (e.g., DEPLOYMENT_MODE must be 'internal' or 'nginx')

Key configuration:
- `DEPLOYMENT_MODE`: 'internal' (Flask serves at subpath) or 'nginx' (nginx handles routing)
- `URL_BASE_PATHNAME`: Base URL path (must start and end with `/`)
- `API_BASE`: Backend API URL (default: http://127.0.0.1:5001)
- `ENABLE_LITERATURE_SEARCH`: Enable literature search tab
- `ENABLE_PDF_HIGHLIGHTING`: Enable PDF viewer with highlighting
- `ENABLE_LITERATURE_REVIEW`: Enable ASReview integration

## Markdown Content Loading

Markdown files are loaded **once at app startup** into the layout. They are **not** updated dynamically by callbacks. This prevents the multi-output callback issues seen in production.

The `MarkdownCache` class monitors files for changes (in development) and reloads them, but this only affects the cached content. The layout itself is not updated until the app is restarted.

## Development Workflow

### Running the development server
```bash
python harvest_fe.py
```

### Running with Gunicorn (production)
```bash
export PYTHONDONTWRITEBYTECODE=1
gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
```

### Clearing bytecode cache (development)
```bash
export HARVEST_CLEAR_CACHE=true
python harvest_fe.py
```

### Disabling callback validation (not recommended)
```bash
export HARVEST_STRICT_CALLBACK_CHECKS=false
python harvest_fe.py
```

## Future Refactoring

The current structure is a good starting point, but further modularization is possible:

1. **Split callbacks.py** into domain-specific modules as outlined above
2. **Extract layout sections** into separate functions (e.g., `dashboard_layout()`, `annotate_layout()`)
3. **Create a utilities module** for common helper functions
4. **Add type hints** throughout for better IDE support and documentation
5. **Write unit tests** for individual callbacks and layout functions

## Migration Notes

### What Changed
- `harvest_fe.py` went from 5639 lines to 60 lines (thin wrapper)
- Core logic moved to `frontend/` package (4 modules totaling ~5300 lines)
- Added runtime callback validation guard
- Improved logging (replaced `print()` with `logger.*()`)
- Better code organization for future maintenance

### What Stayed the Same
- All public IDs, routes, and behaviors preserved
- WSGI entry point (`wsgi_fe:server`) unchanged
- Configuration behavior unchanged
- UI appearance and functionality unchanged
- All 68 callbacks work exactly as before

### Deployment Impact
- No configuration changes required
- No systemd service changes required
- No nginx configuration changes required
- `PYTHONDONTWRITEBYTECODE=1` still recommended
- Bytecode clearing logic still works the same way

## Testing

Run the existing test suite:
```bash
python test_scripts/test_wsgi_fe.py
```

Verify callback validation:
```python
from frontend import app
print(f"Callbacks registered: {len(app.callback_map)}")
# Should print: Callbacks registered: 68
```

Check for forbidden outputs:
```python
from frontend import validate_callback_map
validate_callback_map()
# Should print: ✓ Callback validation passed
```

## Security Considerations

1. **Bytecode clearing**: Only runs in development (`HARVEST_CLEAR_CACHE=true`)
2. **Path validation**: PDF and highlight routes validate filenames for path traversal
3. **Authentication**: Admin routes check authentication via backend API
4. **Proxy filtering**: ASReview proxy filters security-sensitive headers
5. **Callback validation**: Prevents accidental exposure of forbidden components

## Troubleshooting

### "Module not found" errors
- Ensure you're running from the HARVEST directory
- Check that `frontend/` directory exists with all modules
- Verify Python path includes current directory

### "Callback validation failed"
- This means a callback is trying to update forbidden markdown IDs
- Check the error message for the specific callback and output
- Remove or fix the offending callback
- This is a **protective error** - don't disable the check unless absolutely necessary

### Markdown content not updating
- Markdown is loaded at startup, not updated dynamically
- Restart the app to see markdown changes
- Watchdog monitoring only updates the cache, not the live layout

### Import errors from `harvest_fe.py`
- The thin wrapper should import from `frontend` package
- If import fails, check that `frontend/__init__.py` exists and is valid
- Check for circular import issues

## Summary

The refactored frontend maintains 100% behavioral compatibility while providing a much more maintainable codebase. The modular structure makes it easier to:
- Understand what each piece of code does
- Make targeted changes without affecting other parts
- Add new features in logical locations
- Test individual components
- Onboard new developers

The callback validation guard ensures we never regress to the problematic multi-output markdown callback pattern that caused production issues.
