#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for HARVEST backend.
This file is used by production WSGI servers like Gunicorn.

Usage:
    gunicorn -w 4 -b 127.0.0.1:5001 wsgi:app
    
Or with systemd service:
    ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:5001 wsgi:app
"""

import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the Flask app from harvest_be
from harvest_be import app

# Note: Avoid DB side effects at import time. If cleanup is desired on startup,
# configure a Gunicorn server hook (e.g., post_fork) or run a periodic job.
#
# Example Gunicorn config (gunicorn.conf.py):
# def post_fork(server, worker):
#     import logging
#     from harvest_be import cleanup_old_pdf_download_progress, DB_PATH
#     logger = logging.getLogger(__name__)
#     logger.info("[PDF Download] post_fork cleanup...")
#     try:
#         deleted = cleanup_old_pdf_download_progress(DB_PATH, max_age_seconds=3600)
#         if deleted > 0:
#             logger.info(f"[PDF Download] Cleaned up {deleted} old progress entries")
#     except Exception as e:
#         logger.warning(f"Cleanup failed: {e}")

# The 'app' variable is what Gunicorn will use
# Gunicorn expects a WSGI application object named 'application' or specified via command line
if __name__ == "__main__":
    # This won't be used by Gunicorn, but allows running directly for testing
    print("WARNING: This file is meant to be used with a WSGI server like Gunicorn.")
    print("For development, use: python3 harvest_be.py")
    print("For production, use: gunicorn -w 4 -b 127.0.0.1:5001 wsgi:app")
