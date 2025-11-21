# harvest_fe.py
"""
HARVEST Frontend - Thin Compatibility Wrapper

This module provides backwards compatibility by importing and re-exporting
the Dash app and Flask server from the new modular frontend package.

The actual implementation has been refactored into the frontend/ package:
  - frontend/__init__.py: App initialization, config, logging
  - frontend/markdown.py: Markdown file caching with watchdog monitoring
  - frontend/layout.py: UI layout building functions (sidebar, main layout)
  - frontend/server_routes.py: Flask routes for PDF/ASReview proxying
  - frontend/callbacks.py: All Dash callbacks for interactivity

For WSGI deployment (e.g., with Gunicorn), import from this module:
    from harvest_fe import server

Or import directly from frontend package:
    from frontend import app, server
"""

# Import and re-export from frontend package
from frontend import (
    app,
    server,
    markdown_cache,
    # Export configuration for backwards compatibility
    DEPLOYMENT_MODE,
    URL_BASE_PATHNAME,
    API_BASE,
    SCHEMA_JSON,
    APP_TITLE,
)

# For backwards compatibility, also make these available
from frontend import (
    PARTNER_LOGOS,
    ENABLE_LITERATURE_SEARCH,
    ENABLE_PDF_HIGHLIGHTING,
    ENABLE_LITERATURE_REVIEW,
    BACKEND_PUBLIC_URL,
    EMAIL_HASH_SALT,
    PORT,
)

# -----------------------
# Main entry point for development server
# -----------------------
if __name__ == "__main__":
    # Run development server
    # In production, use: gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
    import os
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8050")),
        debug=False
    )
