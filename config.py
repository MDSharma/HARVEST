#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for T2T Training Application
Edit these settings before running the application
"""

# Server Configuration
HOST = "127.0.0.1"  # Host address for the server
PORT = 8050  # Port for the Dash frontend
BE_PORT = 5001  # Port for the Flask backend

# Database Configuration
DB_PATH = "t2t_training.db"  # Path to SQLite database file

# API Configuration
# Email required by Unpaywall API for PDF access checking
# Please update this to your email address
UNPAYWALL_EMAIL = "your-email@example.com"  # CHANGE THIS to your email

# Admin Configuration
# Optional: Comma-separated list of admin email addresses
# These emails will have admin access in addition to database admin_users
ADMIN_EMAILS = ""  # Example: "admin@example.com,researcher@university.edu"

# PDF Storage Configuration
PDF_STORAGE_DIR = "project_pdfs"  # Directory for storing project PDFs

# Feature Flags
ENABLE_PDF_DOWNLOAD = True  # Enable automatic PDF downloading
ENABLE_PDF_VIEWER = True  # Enable embedded PDF viewer on Annotate tab

# PDF Download Options
ENABLE_METAPUB_FALLBACK = False  # Try metapub if Unpaywall fails (requires NCBI_API_KEY environment variable)
ENABLE_HABANERO_DOWNLOAD = True  # Try habanero/institutional access (works within institutional networks)
HABANERO_PROXY_URL = ""  # Optional: Proxy URL for institutional access (e.g., "http://proxy.university.edu:8080")
