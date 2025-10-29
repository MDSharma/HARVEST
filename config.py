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

# Deployment Mode Configuration
# Choose between "internal" (default) or "nginx" deployment modes
#
# "internal" mode (default):
#   - Frontend proxies all backend requests through /proxy/* routes
#   - Backend runs on 127.0.0.1 (localhost only, not accessible externally)
#   - Ideal for: Development, single-server deployments, simplified setup
#   - Security: Backend is protected from direct external access
#
# "nginx" mode:
#   - Frontend makes direct requests to backend API
#   - Backend must be accessible at BACKEND_PUBLIC_URL
#   - Requires reverse proxy (nginx, Apache, etc.) for routing
#   - Ideal for: Production deployments, multiple instances, SSL termination, load balancing
#   - Security: Requires proper firewall rules and reverse proxy configuration
#
DEPLOYMENT_MODE = "internal"  # Options: "internal" or "nginx"

# Backend Public URL (required for nginx mode, ignored for internal mode)
# This is the externally accessible URL where the backend API can be reached
# Examples:
#   - "https://api.yourdomain.com" (production with SSL)
#   - "http://yourdomain.com/api" (behind reverse proxy at /api path)
#   - "http://backend.internal:5001" (internal network with DNS)
BACKEND_PUBLIC_URL = ""  # Only used when DEPLOYMENT_MODE = "nginx"

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

# PDF Download Options - Legacy Sources
ENABLE_METAPUB_FALLBACK = False  # Try metapub if Unpaywall fails (requires NCBI_API_KEY environment variable)
ENABLE_HABANERO_DOWNLOAD = True  # Try habanero/institutional access (works within institutional networks)
HABANERO_PROXY_URL = ""  # Optional: Proxy URL for institutional access (e.g., "http://proxy.university.edu:8080")

# NCBI API Key for Metapub (optional)
# To use metapub for PDF downloads, you need an NCBI API key
# Sign up for a free API key at: https://www.ncbi.nlm.nih.gov/account/
# After creating an account, go to Settings > API Key Management to generate a key
# Example: NCBI_API_KEY = "279xxxxxxxxd504e09"
NCBI_API_KEY = ""  # Enter your NCBI API key here if using metapub

# Enhanced PDF Download System Configuration
# The new enhanced system uses a separate database (pdf_downloads.db) for tracking
# and provides multiple additional sources with smart selection
ENABLE_ENHANCED_PDF_DOWNLOAD = True  # Use enhanced multi-source PDF download system
PDF_DOWNLOAD_DB_PATH = "pdf_downloads.db"  # Path to PDF download tracking database

# Additional PDF Source Configuration
# Europe PMC - Biomedical literature (no dependencies required)
ENABLE_EUROPE_PMC = True  # Enable Europe PMC source (REST API, no extra dependencies)

# CORE.ac.uk - Open access research papers
ENABLE_CORE = True  # Enable CORE.ac.uk source (REST API, no extra dependencies)
CORE_API_KEY = ""  # Optional: Get free API key at https://core.ac.uk/services/api for better results

# Semantic Scholar - Academic paper metadata and PDFs
ENABLE_SEMANTIC_SCHOLAR = True  # Enable Semantic Scholar source (REST API, no extra dependencies)

# Publisher Direct Access - Predictable URLs for open access publishers
ENABLE_PUBLISHER_DIRECT = True  # Enable direct publisher URL construction (no extra dependencies)

# SciHub - Optional last resort (use responsibly, may not be legal in all jurisdictions)
# DISABLED BY DEFAULT - Enable only if you understand the legal implications
ENABLE_SCIHUB = False  # Enable SciHub source (use with caution, check local laws)

# Smart Download Configuration
# These settings control the intelligent source selection and retry logic
PDF_SMART_RETRY_ENABLED = True  # Enable automatic retry queue for temporary failures
PDF_SMART_RETRY_MAX_ATTEMPTS = 3  # Maximum retry attempts for temporary failures
PDF_SMART_RETRY_BASE_DELAY_MINUTES = 60  # Base delay before first retry (uses exponential backoff)
PDF_RATE_LIMIT_DELAY_SECONDS = 1  # Delay between API requests to respect rate limits
PDF_CLEANUP_RETENTION_DAYS = 90  # Days to keep download attempt history before cleanup

# User Agent Rotation
# Rotate User-Agent headers to avoid being blocked by some sources
PDF_USER_AGENT_ROTATION = True  # Enable rotating User-Agent strings

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
