#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI entry point for HARVEST frontend (Dash application).
This file is used by production WSGI servers like Gunicorn.

Usage:
    gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
    
Or with systemd service:
    ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server
"""

import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the Dash app from harvest_fe
# The 'server' variable is the Flask server instance that Gunicorn will use
from harvest_fe import server

# The 'server' variable is what Gunicorn will use
# Gunicorn expects a WSGI application object named 'application' or specified via command line
if __name__ == "__main__":
    # This won't be used by Gunicorn, but allows running directly for testing
    print("WARNING: This file is meant to be used with a WSGI server like Gunicorn.")
    print("For development, use: python3 harvest_fe.py")
    print("For production, use: gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server")
