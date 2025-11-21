# frontend/__init__.py
"""
HARVEST Frontend Package
Modular Dash application for HARVEST triple annotation interface.
"""
# IMPORTANT: Clear bytecode cache BEFORE any other imports to prevent stale callback issues
# This must run before Dash imports to ensure clean callback registration
import os
import sys
import glob
import shutil

# Clear bytecode cache if requested or if .pyc files exist that might be stale
# This prevents Dash from loading old callback definitions
_module_dir = os.path.dirname(os.path.abspath(__file__))
_pycache_dir = os.path.join(_module_dir, "__pycache__")
_should_clear = (
    os.getenv('HARVEST_CLEAR_CACHE', '').lower() in ('true', '1', 'yes') or
    os.getenv('PYTHONDONTWRITEBYTECODE', '').lower() in ('true', '1', 'yes')
)

if _should_clear and os.path.exists(_pycache_dir):
    # Clear this module's cache directory
    for cache_file in glob.glob(os.path.join(_pycache_dir, "*.pyc")):
        try:
            os.remove(cache_file)
        except (OSError, PermissionError):
            pass  # Silently continue if clearing individual file fails

# Prevent bytecode generation for this session
sys.dont_write_bytecode = True

import logging
import dash
from dash import Dash
import dash_bootstrap_components as dbc

# Setup logging
logger = logging.getLogger(__name__)

# Import configuration
try:
    from config import (
        PARTNER_LOGOS, ENABLE_LITERATURE_SEARCH, ENABLE_PDF_HIGHLIGHTING,
        ENABLE_LITERATURE_REVIEW, DEPLOYMENT_MODE, BACKEND_PUBLIC_URL, 
        URL_BASE_PATHNAME, EMAIL_HASH_SALT, PORT
    )
except ImportError:
    # Fallback if config not available
    PARTNER_LOGOS = []
    ENABLE_LITERATURE_SEARCH = True  # Default to enabled
    ENABLE_PDF_HIGHLIGHTING = True  # Default to enabled
    ENABLE_LITERATURE_REVIEW = False  # Default to disabled (requires ASReview service)
    DEPLOYMENT_MODE = os.getenv("HARVEST_DEPLOYMENT_MODE", "internal")
    BACKEND_PUBLIC_URL = os.getenv("HARVEST_BACKEND_PUBLIC_URL", "")
    URL_BASE_PATHNAME = os.getenv("HARVEST_URL_BASE_PATHNAME", "/")
    EMAIL_HASH_SALT = os.getenv("EMAIL_HASH_SALT", "default-insecure-salt-change-me")
    PORT = int(os.getenv("PORT", "8050"))

# Override config with environment variables if present
DEPLOYMENT_MODE = os.getenv("HARVEST_DEPLOYMENT_MODE", DEPLOYMENT_MODE)
BACKEND_PUBLIC_URL = os.getenv("HARVEST_BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)
URL_BASE_PATHNAME = os.getenv("HARVEST_URL_BASE_PATHNAME", URL_BASE_PATHNAME)

# Validate deployment mode
if DEPLOYMENT_MODE not in ["internal", "nginx"]:
    raise ValueError(f"Invalid DEPLOYMENT_MODE: {DEPLOYMENT_MODE}. Must be 'internal' or 'nginx'")

# Validate URL_BASE_PATHNAME
if not URL_BASE_PATHNAME.startswith("/") or not URL_BASE_PATHNAME.endswith("/"):
    raise ValueError(f"URL_BASE_PATHNAME must start and end with '/'. Got: {URL_BASE_PATHNAME}")

# Configure Dash pathname routing based on deployment mode
# In nginx mode: nginx strips the path prefix, so Flask listens at root
# In internal mode: Flask serves at the configured subpath directly
if DEPLOYMENT_MODE == "nginx":
    # nginx handles path routing - Flask listens at root
    DASH_ROUTES_PATHNAME_PREFIX = "/"
    DASH_REQUESTS_PATHNAME_PREFIX = URL_BASE_PATHNAME
else:
    # internal mode - Flask serves directly at subpath
    DASH_ROUTES_PATHNAME_PREFIX = URL_BASE_PATHNAME
    DASH_REQUESTS_PATHNAME_PREFIX = URL_BASE_PATHNAME

# -----------------------
# Config Constants
# -----------------------
APP_TITLE = "HARVEST: Human-in-the-loop Actionable Research and Vocabulary Extraction Technology"

# Headers to filter out in ASReview proxy to prevent iframe issues
ASREVIEW_PROXY_FILTERED_HEADERS = frozenset([
    'location',  # Redirects
    'content-location',  # Alternative location
    'content-security-policy',  # Can block iframe embedding
    'x-frame-options',  # Explicitly controls iframe embedding
    'strict-transport-security',  # HSTS can cause issues
    'set-cookie',  # Cookies should not be proxied
    'server',  # Server info not needed
    'date',  # Will be set by our response
    'transfer-encoding',  # Can cause chunking issues
])

# Determine API base URL for server-side requests
API_BASE = os.getenv("HARVEST_API_BASE", "http://127.0.0.1:5001")
API_CHOICES = f"{API_BASE}/api/choices"
API_SAVE = f"{API_BASE}/api/save"
API_RECENT = f"{API_BASE}/api/recent"
API_VALIDATE_DOI = f"{API_BASE}/api/validate-doi"
API_ADMIN_AUTH = f"{API_BASE}/api/admin/auth"
API_PROJECTS = f"{API_BASE}/api/projects"
API_ADMIN_PROJECTS = f"{API_BASE}/api/admin/projects"
API_ADMIN_TRIPLE = f"{API_BASE}/api/admin/triple"

# Local fallback schema (used if /api/choices is not reachable)
SCHEMA_JSON = {
    "orl": "opinion role labeling",
    "span-attribute": {
        "Gene": "gene",
        "Regulator": "regulator",
        "Variant": "variant",
        "Protein": "protein",
        "Trait": "phenotype",
        "Enzyme": "enzyme",
        "QTL": "qtl",
        "Coordinates": "coordinates",
        "Metabolite": "metabolite",
    },
    "relation-type": {
        "is_a": "is_a",
        "part_of": "part_of",
        "develops_from": "develops_from",
        "is_related_to": "is_related_to",
        "is_not_related_to": "is_not_related_to",
        "increases": "increases",
        "decreases": "decreases",
        "influences": "influences",
        "does_not_influence": "does_not_influence",
        "may_influence": "may_influence",
        "may_not_influence": "may_not_influence",
        "disrupts": "disrupts",
        "regulates": "regulates",
        "contributes_to": "contributes_to",
        "inhers_in": "inhers_in",
    },
}

OTHER_SENTINEL = "__OTHER__"

# -----------------------
# Create Dash App
# -----------------------
# Clear Python bytecode cache to prevent stale callback registrations (development only)
if os.getenv('HARVEST_CLEAR_CACHE', '').lower() in ('true', '1', 'yes'):
    logger.warning("HARVEST_CLEAR_CACHE is enabled - clearing Python bytecode cache")
    
    # Clear __pycache__ directories (only in current module directory, not recursive for security)
    module_dir = os.path.dirname(__file__)
    pycache_dir = os.path.join(module_dir, "__pycache__")
    if os.path.exists(pycache_dir):
        try:
            shutil.rmtree(pycache_dir)
            logger.info(f"Cleared bytecode cache: {pycache_dir}")
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not clear cache {pycache_dir}: {e}")
    
    # Clear .pyc files in current directory only
    try:
        for pyc_file in glob.glob(os.path.join(module_dir, "*.pyc")):
            os.remove(pyc_file)
            logger.info(f"Removed bytecode file: {pyc_file}")
    except (OSError, PermissionError, FileNotFoundError) as e:
        logger.warning(f"Could not remove .pyc files: {e}")
    
    logger.info("Bytecode cache clearing completed")

external_stylesheets = [dbc.themes.BOOTSTRAP]
app: Dash = dash.Dash(
    __name__, 
    external_stylesheets=external_stylesheets, 
    suppress_callback_exceptions=True,
    routes_pathname_prefix=DASH_ROUTES_PATHNAME_PREFIX,
    requests_pathname_prefix=DASH_REQUESTS_PATHNAME_PREFIX
)
app.title = APP_TITLE
server = app.server  # Flask server for WSGI deployment

# Add custom JavaScript for iframe message listening
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <!-- Bootstrap Icons -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <script>
            // Listen for messages from PDF viewer iframe
            window.addEventListener('message', function(event) {
                console.log('Parent received message:', event.data);
                if (event.data && event.data.type === 'pdf-text-selected') {
                    console.log('Processing pdf-text-selected message');
                    // Wait a bit for DOM to be ready
                    setTimeout(function() {
                        const sentenceTextarea = document.getElementById('sentence-text');
                        console.log('Sentence textarea element:', sentenceTextarea);
                        if (sentenceTextarea) {
                            sentenceTextarea.value = event.data.text;
                            // Trigger change event so Dash detects the change
                            const changeEvent = new Event('input', { bubbles: true });
                            sentenceTextarea.dispatchEvent(changeEvent);
                            console.log('Sentence field updated with:', event.data.text);
                        } else {
                            console.warn('sentence-text element not found');
                        }
                    }, 100);
                }
            });
        </script>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Initialize markdown cache
from frontend.markdown import create_markdown_cache
markdown_cache = create_markdown_cache(SCHEMA_JSON)

# Note: Modules will be imported after app is created to avoid circular imports
# They will be imported at the end of this file

# -----------------------
# Callback Guard - Validate No Multi-Output to Markdown Info Tabs
# -----------------------
# These IDs should NEVER have callbacks that update them dynamically
FORBIDDEN_MARKDOWN_OUTPUT_IDS = [
    "annotator-guide-content.children",
    "schema-tab-content.children",
    "admin-guide-content.children",
    "dbmodel-tab-content.children",
    "participate-tab-content.children",
]

def validate_callback_map():
    """
    Validate that no callback outputs to the forbidden markdown info-tab IDs.
    Raises RuntimeError if any callback tries to update these components.
    """
    if not os.getenv('HARVEST_STRICT_CALLBACK_CHECKS', 'true').lower() in ('true', '1', 'yes'):
        logger.info("HARVEST_STRICT_CALLBACK_CHECKS is disabled - skipping callback validation")
        return
    
    logger.info("Validating callback map for forbidden markdown outputs...")
    violations = []
    
    for callback_id, callback_spec in app.callback_map.items():
        # Check if any output matches forbidden IDs
        output = callback_spec.get('output', '')
        if isinstance(output, str):
            outputs_to_check = [output]
        else:
            # Handle multi-output case
            outputs_to_check = [str(o) for o in output] if output else []
        
        for output_str in outputs_to_check:
            for forbidden_id in FORBIDDEN_MARKDOWN_OUTPUT_IDS:
                if forbidden_id in output_str:
                    violations.append({
                        'callback_id': callback_id,
                        'output': output_str,
                        'forbidden_id': forbidden_id
                    })
    
    if violations:
        error_msg = "CALLBACK VALIDATION FAILED: Found callbacks outputting to forbidden markdown info-tab IDs:\n"
        for v in violations:
            error_msg += f"  - Callback {v['callback_id']} outputs to {v['forbidden_id']}\n"
        error_msg += "\nThese IDs should only be populated at app startup, never updated by callbacks.\n"
        error_msg += "This prevents KeyError issues seen in production with stale multi-output callbacks."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info("✓ Callback validation passed - no forbidden markdown outputs found")

# The validation will be called after all modules are imported
# (see end of this file)

logger.info("HARVEST frontend app created")
