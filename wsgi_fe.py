#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for HARVEST frontend (Dash application).
This file is used by production WSGI servers like Gunicorn.

Usage:
    gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
    
Or with systemd service (recommended - prevents bytecode caching issues):
    [Service]
    Environment="PYTHONDONTWRITEBYTECODE=1"
    ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
    
This prevents Python bytecode (.pyc) generation which can cause stale callback
registration issues when code is updated. See harvest_fe.py for details.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the Dash app from harvest_fe
# The 'server' variable is the Flask server instance that Gunicorn will use
try:
    from harvest_fe import server
except ImportError as e:
    logger.error(f"Failed to import harvest_fe: {e}")
    logger.error("Ensure harvest_fe.py is in the same directory and all dependencies are installed.")
    sys.exit(1)
except AttributeError as e:
    logger.error(f"Failed to access 'server' attribute from harvest_fe: {e}")
    logger.error("Ensure harvest_fe.py exposes 'server = app.server'")
    sys.exit(1)

# The 'server' variable is what Gunicorn will use
# Gunicorn expects a WSGI application object named 'application' or specified via command line
if __name__ == "__main__":
    # This won't be used by Gunicorn, but allows running directly for testing
    logger.warning("WARNING: This file is meant to be used with a WSGI server like Gunicorn.")
    logger.warning("For development, use: python3 harvest_fe.py")
    logger.warning("For production, use: gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server")
    sys.exit(1)
