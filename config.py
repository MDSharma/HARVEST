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
ENABLE_PDF_HIGHLIGHTING = True  # Enable PDF highlighting/annotation feature in PDF viewer
ENABLE_LITERATURE_SEARCH = True  # Enable Literature Search tab (requires admin authentication)

# PDF Download Options
ENABLE_METAPUB_FALLBACK = False  # Try metapub if Unpaywall fails (requires NCBI_API_KEY environment variable)
ENABLE_HABANERO_DOWNLOAD = True  # Try habanero/institutional access (works within institutional networks)
HABANERO_PROXY_URL = ""  # Optional: Proxy URL for institutional access (e.g., "http://proxy.university.edu:8080")

# NCBI API Key for Metapub (optional)
# To use metapub for PDF downloads, you need an NCBI API key
# Sign up for a free API key at: https://www.ncbi.nlm.nih.gov/account/
# After creating an account, go to Settings > API Key Management to generate a key
# Example: NCBI_API_KEY = "279xxxxxxxxd504e09"
NCBI_API_KEY = ""  # Enter your NCBI API key here if using metapub

# Partner Logos Configuration
# Local logo files (jpg or png) in the document root
# Place your logo files (UOE.png, UM.jpg, ARIA.jpg) in the same directory as this file
PARTNER_LOGOS = [
    {
        "name": "University of Exeter",
        "url": "UOE.png",
        "alt": "University of Exeter Logo"
    },
    {
        "name": "Maastricht University",
        "url": "UM.jpg",
        "alt": "Maastricht University Logo"
    },
    {
        "name": "Advanced Research and Invention Agency",
        "url": "ARIA.jpg",
        "alt": "Funded By Advanced Research + Invention Agency"
    }
]
