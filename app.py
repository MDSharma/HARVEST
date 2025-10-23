#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified launcher for Text2Trait application.
Starts both backend API and frontend Dash app in a single process.
"""

import os
import sys
import threading
import time
from werkzeug.middleware.proxy_fix import ProxyFix

# Import backend app
from t2t_training_be import app as backend_app, init_db, DB_PATH

# Import frontend app
from t2t_training_fe import app as frontend_app

# Configuration
BACKEND_PORT = int(os.environ.get("T2T_BACKEND_PORT", "5001"))
FRONTEND_PORT = int(os.environ.get("T2T_FRONTEND_PORT", "8050"))
HOST = os.environ.get("T2T_HOST", "0.0.0.0")
DEBUG = os.environ.get("T2T_DEBUG", "false").lower() == "true"

# Reverse proxy configuration
USE_PROXY_FIX = os.environ.get("T2T_USE_PROXY_FIX", "true").lower() == "true"

def run_backend():
    """Run the Flask backend API."""
    print(f"Starting Backend API on {HOST}:{BACKEND_PORT}")

    # Apply ProxyFix for reverse proxy compatibility
    if USE_PROXY_FIX:
        backend_app.wsgi_app = ProxyFix(
            backend_app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_prefix=1
        )

    backend_app.run(
        host=HOST,
        port=BACKEND_PORT,
        debug=DEBUG,
        use_reloader=False,
        threaded=True
    )

def run_frontend():
    """Run the Dash frontend application."""
    print(f"Starting Frontend on {HOST}:{FRONTEND_PORT}")

    # Configure Dash for reverse proxy
    if USE_PROXY_FIX:
        frontend_app.server.wsgi_app = ProxyFix(
            frontend_app.server.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_prefix=1
        )

    # Set production settings
    if not DEBUG:
        frontend_app.server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300
        frontend_app.server.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

    frontend_app.run_server(
        host=HOST,
        port=FRONTEND_PORT,
        debug=DEBUG,
        use_reloader=False,
        threaded=True
    )

def main():
    """Main entry point - starts both services."""
    print("=" * 60)
    print("Text2Trait Training Data Builder")
    print("=" * 60)
    print(f"Database: {DB_PATH}")
    print(f"Debug Mode: {DEBUG}")
    print(f"Reverse Proxy Mode: {USE_PROXY_FIX}")
    print("=" * 60)

    # Initialize database
    print("Initializing database...")
    init_db(DB_PATH)
    print("Database ready!")

    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Give backend a moment to start
    time.sleep(2)

    # Start frontend in main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
