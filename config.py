#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for HARVEST Training Application
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

# Backend Public URL (for documentation/reference in nginx mode)
# NOTE: This is currently NOT used by the application code.
# The frontend server always connects to the backend via localhost (127.0.0.1:5001)
# for server-side API requests, regardless of deployment mode.
#
# This setting is kept for reference to document the public-facing backend URL
# in your nginx configuration, but it does not affect actual connections.
#
# Example: If your nginx config has 'location /harvest/api/', document it here:
BACKEND_PUBLIC_URL = ""  # For reference only (e.g., "https://yourdomain.com/harvest")

# URL Base Pathname (required when app is served at a subpath)
# This is the base path where the application is mounted in the URL structure
# 
# In nginx mode: nginx strips the prefix, Flask listens at root, but generates URLs with this prefix
# In internal mode: Flask serves directly at this path (e.g., http://localhost:8050/harvest/)
#
# Examples:
#   - "/" (default, app at root)
#   - "/harvest/" (app at https://domain.com/harvest/)
#   - "/t2t/" (app at https://domain.com/t2t/)
# IMPORTANT: Must start and end with forward slashes
URL_BASE_PATHNAME = "/"  # Default: "/" for root deployment

# Database Configuration
DB_PATH = "harvest.db"  # Path to SQLite database file

# API Configuration
# Email required by Unpaywall API for PDF access checking
# Please update this to your email address
UNPAYWALL_EMAIL = "your-email@example.com"  # CHANGE THIS to your email

# Contact email for OpenAlex API (polite pool for faster responses)
# OpenAlex recommends including a contact email for better service
# This can be the same as UNPAYWALL_EMAIL or a different contact email
HARVEST_CONTACT_EMAIL = "your-email@example.com"  # CHANGE THIS to your email

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

# Security Configuration
# Email Hashing Salt - IMPORTANT: Change this to a unique value for your installation
# This salt is used to hash email addresses for privacy in the Browse tab
# Use a long, random string that is kept secret and consistent across application restarts
# Example: Generate with: python -c "import secrets; print(secrets.token_hex(32))"
EMAIL_HASH_SALT = "change-this-to-a-random-secure-value-for-your-installation"

# Web of Science API Configuration
# To enable Web of Science searches in the Literature Search tab, you need an API key
# Sign up for a Web of Science Expanded API key at: https://developer.clarivate.com/
# After obtaining a key, enter it below or set the WOS_API_KEY environment variable
# Environment variable takes precedence if both are set
# Example: WOS_API_KEY = "your-api-key-here"
WOS_API_KEY = ""  # Enter your Web of Science API key here

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
