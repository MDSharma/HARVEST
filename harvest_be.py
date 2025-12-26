#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import logging
from typing import Dict, Any, List, Tuple
import threading
import time
from datetime import datetime
import secrets
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

from flask import Flask, request, jsonify
from flask_cors import CORS

from harvest_store import (
    init_db,
    fetch_entity_dropdown_options,
    fetch_relation_dropdown_options,
    upsert_sentence,
    upsert_doi_metadata,
    insert_triple_rows,
    add_relation_type,
    add_entity_type,
    generate_doi_hash,
    is_admin_user,
    verify_admin_password,
    create_admin_user,
    create_project,
    get_all_projects,
    get_project_by_id,
    update_project,
    delete_project,
    update_triple,
    check_admin_status,
    init_pdf_download_progress,
    update_pdf_download_progress,
    get_pdf_download_progress,
    cleanup_old_pdf_download_progress,
    is_download_stale,
    reset_stale_download,
    create_batches,
    get_project_batches,
    get_batch_dois,
    update_doi_status,
    get_doi_status_summary,
    set_browse_visible_fields,
    get_browse_visible_fields,
)

# Import configuration
try:
    from config import (
        DB_PATH, BE_PORT as PORT, HOST, ENABLE_PDF_HIGHLIGHTING,
        DEPLOYMENT_MODE, BACKEND_PUBLIC_URL,
        NCBI_API_KEY
    )
    # Set NCBI_API_KEY as environment variable for metapub if defined
    if NCBI_API_KEY:
        os.environ['NCBI_API_KEY'] = NCBI_API_KEY
except ImportError:
    # Fallback to environment variables if config.py doesn't exist
    DB_PATH = os.environ.get("HARVEST_DB", "harvest.db")
    PORT = int(os.environ.get("HARVEST_PORT", "5001"))
    HOST = os.environ.get("HARVEST_HOST", "0.0.0.0")
    ENABLE_PDF_HIGHLIGHTING = True  # Default to enabled
    DEPLOYMENT_MODE = os.environ.get("HARVEST_DEPLOYMENT_MODE", "internal")
    BACKEND_PUBLIC_URL = os.environ.get("HARVEST_BACKEND_PUBLIC_URL", "")
    NCBI_API_KEY = ""

# Setup logging first
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Override config with environment variables if present
DB_PATH = os.environ.get("HARVEST_DB", DB_PATH)

# Validate and parse PORT safely
raw_port = os.environ.get("HARVEST_PORT", str(PORT))
try:
    PORT = int(raw_port)
    if not (1 <= PORT <= 65535):
        raise ValueError("Port out of range")
except Exception:
    logger.warning(f"Invalid HARVEST_PORT='{raw_port}', falling back to default PORT={PORT}")
    # Keep existing PORT from config/import

HOST = os.environ.get("HARVEST_HOST", HOST)
DEPLOYMENT_MODE = os.environ.get("HARVEST_DEPLOYMENT_MODE", DEPLOYMENT_MODE)
BACKEND_PUBLIC_URL = os.environ.get("HARVEST_BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)

# Validate deployment mode
if DEPLOYMENT_MODE not in ["internal", "nginx"]:
    raise ValueError(f"Invalid DEPLOYMENT_MODE: {DEPLOYMENT_MODE}. Must be 'internal' or 'nginx'")

# Ensure database directory exists and DB_PATH is not a directory
abs_db_path = os.path.abspath(DB_PATH)
if os.path.isdir(abs_db_path):
    raise ValueError(f"HARVEST_DB points to a directory, expected file path: {abs_db_path}")
db_dir = os.path.dirname(abs_db_path) or "."
if db_dir and db_dir != '/' and not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")
    except Exception as e:
        raise RuntimeError(f"Failed to create database directory '{db_dir}': {e}") from e

    logger.info(f"Created database directory: {db_dir}")

# Initialize required directories (.cache, project_pdfs)
try:
    from init_directories import init_harvest_directories
    success, messages = init_harvest_directories()
    if not success:
        logger.warning("Some required directories could not be created. The application may encounter issues.")
        for msg in messages:
            if "Failed" in msg or "not" in msg.lower():
                logger.warning(msg)
except Exception as e:
    logger.warning(f"Failed to initialize directories: {e}. The application may encounter issues.")

# Initialize DB on startup
init_db(DB_PATH)

app = Flask(__name__)

# Configure CORS based on deployment mode
if DEPLOYMENT_MODE == "nginx":
    # In nginx mode, allow CORS from any origin since requests come directly from client
    # The reverse proxy should handle origin restrictions
    CORS(app, origins="*", supports_credentials=True)
    logger.info(f"CORS enabled for nginx mode (allowing all origins)")
else:
    # In internal mode, only allow localhost origins
    CORS(app, origins=["http://localhost:*", "http://127.0.0.1:*", "http://0.0.0.0:*"])
    logger.info(f"CORS enabled for internal mode (localhost only)")

# Browse tab display configuration defaults/validation
DEFAULT_BROWSE_VISIBLE_FIELDS = [
    "project_id",
    "sentence_id",
    "sentence",
    "source_entity_name",
    "source_entity_attr",
    "relation_type",
    "sink_entity_name",
    "sink_entity_attr",
    "triple_id",
]
ALLOWED_BROWSE_FIELDS = {
    "sentence_id",
    "triple_id",
    "project_id",
    "doi",
    "doi_hash",
    "literature_link",
    "relation_type",
    "source_entity_name",
    "source_entity_attr",
    "sink_entity_name",
    "sink_entity_attr",
    "sentence",
    "triple_contributor",
}
MAX_BROWSE_LIMIT = 10000

# Token storage for admin sessions (in-memory)
# Format: {token: {"email": email, "expires_at": timestamp}}
_admin_tokens = {}
_token_lock = threading.Lock()
TOKEN_EXPIRATION = 86400  # 24 hours in seconds

def generate_admin_token(email: str) -> str:
    """Generate a secure random token for admin session."""
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + TOKEN_EXPIRATION
    with _token_lock:
        _admin_tokens[token] = {"email": email, "expires_at": expires_at}
    return token

def verify_admin_token(token: str) -> str | None:
    """Verify admin token and return email if valid, None otherwise."""
    if not token:
        return None
    
    with _token_lock:
        token_data = _admin_tokens.get(token)
        if not token_data:
            return None
        
        # Check expiration
        if time.time() > token_data["expires_at"]:
            # Token expired, remove it
            del _admin_tokens[token]
            return None
        
        return token_data["email"]

def revoke_admin_token(token: str) -> bool:
    """Revoke an admin token."""
    with _token_lock:
        if token in _admin_tokens:
            del _admin_tokens[token]
            return True
        return False

def cleanup_expired_tokens():
    """Clean up expired tokens (should be called periodically)."""
    with _token_lock:
        current_time = time.time()
        expired_tokens = [
            token for token, data in _admin_tokens.items()
            if current_time > data["expires_at"]
        ]
        for token in expired_tokens:
            del _admin_tokens[token]
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired admin tokens")

def verify_admin_auth(payload: dict) -> tuple[bool, str | None]:
    """
    Verify admin authentication from request payload.
    Accepts either token OR email/password.
    Returns: (is_authenticated, email)
    """
    # Try token-based auth first
    token = payload.get("token", "").strip()
    if token:
        email = verify_admin_token(token)
        if email:
            return True, email
    
    # Fall back to email/password auth for backwards compatibility
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    
    if email and password:
        if verify_admin_password(DB_PATH, email, password) or is_admin_user(email):
            return True, email
    
    return False, None

# DOI Validation Cache - stores validation results to avoid redundant API calls
# Format: {doi: {"valid": bool, "reason": str, "timestamp": float}}
_doi_validation_cache = {}
_doi_cache_lock = threading.Lock()
DOI_CACHE_TTL = 3600  # 1 hour cache TTL

def _validate_single_doi(doi: str) -> Tuple[str, bool, str]:
    """
    Validate a single DOI via CrossRef API.
    Returns: (doi, is_valid, reason)
    """
    # Normalize DOI
    doi_normalized = normalize_doi(doi)
    if not doi_normalized:
        return (doi, False, "Empty DOI")
    
    # Check format first (fast check before API call)
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$'
    if not re.match(doi_pattern, doi_normalized):
        return (doi, False, "Invalid DOI format")
    
    # Check cache first
    with _doi_cache_lock:
        cached = _doi_validation_cache.get(doi_normalized)
        if cached and (time.time() - cached["timestamp"]) < DOI_CACHE_TTL:
            return (doi, cached["valid"], cached.get("reason", ""))
    
    # Validate via CrossRef API
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(
            f"https://api.crossref.org/works/{doi_normalized}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            # Cache success
            with _doi_cache_lock:
                _doi_validation_cache[doi_normalized] = {
                    "valid": True,
                    "reason": "",
                    "timestamp": time.time()
                }
            return (doi, True, "")
        elif response.status_code == 404:
            reason = "DOI not found in CrossRef database"
            # Cache failure
            with _doi_cache_lock:
                _doi_validation_cache[doi_normalized] = {
                    "valid": False,
                    "reason": reason,
                    "timestamp": time.time()
                }
            return (doi, False, reason)
        else:
            return (doi, False, f"CrossRef validation failed (HTTP {response.status_code})")
            
    except requests.exceptions.Timeout:
        return (doi, False, "CrossRef API timeout")
    except requests.exceptions.RequestException as e:
        return (doi, False, f"Network error: {str(e)}")
    except Exception as e:
        return (doi, False, f"Validation error: {str(e)}")

def validate_dois_concurrent(dois: List[str], max_workers: int = 10) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Validate multiple DOIs concurrently with caching.
    
    Args:
        dois: List of DOI strings to validate
        max_workers: Maximum number of concurrent validation threads
        
    Returns:
        Tuple of (valid_dois, invalid_dois)
        - valid_dois: List of normalized valid DOIs
        - invalid_dois: List of dicts with {"doi": original_doi, "reason": error_message}
    """
    if not dois:
        return ([], [])
    
    valid_dois = []
    invalid_dois = []
    
    # Use ThreadPoolExecutor for concurrent validation
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all validation tasks
        future_to_doi = {executor.submit(_validate_single_doi, doi): doi for doi in dois}
        
        # Process results as they complete
        for future in as_completed(future_to_doi):
            try:
                original_doi, is_valid, reason = future.result()
                if is_valid:
                    # Add normalized version
                    valid_dois.append(normalize_doi(original_doi))
                else:
                    invalid_dois.append({"doi": original_doi, "reason": reason})
            except Exception as e:
                original_doi = future_to_doi[future]
                invalid_dois.append({"doi": original_doi, "reason": f"Unexpected error: {str(e)}"})
        
        # Add small delay to be respectful to CrossRef API (total, not per request)
        # Since we're making concurrent requests, we add a small delay at the end
        time.sleep(0.1)
    
    return (list(set(valid_dois)), invalid_dois)  # Deduplicate valid DOIs

def slugify(s: str) -> str:
    """Simple slug for entity type 'value' column (lowercase, underscores)."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "db": DB_PATH,
        "deployment_mode": DEPLOYMENT_MODE,
        "backend_url": BACKEND_PUBLIC_URL if DEPLOYMENT_MODE == "nginx" else "internal"
    })

@app.get("/api/choices")
def choices():
    """Provide dropdown options for entity/relations."""
    try:
        entity_opts = fetch_entity_dropdown_options(DB_PATH)
        relation_opts = fetch_relation_dropdown_options(DB_PATH)
        return jsonify({"entity_types": entity_opts, "relation_types": relation_opts})
    except Exception as e:
        logger.error(f"Failed to fetch choices: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch dropdown options"}), 500

# Helper function for DOI normalization
def normalize_doi(doi: str) -> str:
    """
    Normalize a DOI by removing URL prefixes and converting to lowercase.
    
    Args:
        doi: The DOI string to normalize
        
    Returns:
        Normalized DOI string
    """
    if not doi:
        return ""
    doi = doi.strip()
    # Remove URL prefixes
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    # Convert to lowercase
    doi = doi.lower()
    return doi

@app.post("/api/validate-doi")
def validate_doi():
    """
    Validate a DOI and fetch metadata from CrossRef API.
    Expected JSON: { "doi": "10.1234/example" }
    Returns: { "valid": true/false, "metadata": {...} }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    doi = (payload.get("doi") or "").strip()
    if not doi:
        return jsonify({"error": "Missing 'doi'"}), 400

    # Normalize DOI: remove URL prefix and convert to lowercase
    doi = normalize_doi(doi)

    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$'
    if not re.match(doi_pattern, doi):
        return jsonify({"valid": False, "error": "Invalid DOI format"}), 200

    try:
        headers = {"Accept": "application/json"}
        response = requests.get(f"https://api.crossref.org/works/{doi}", headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            message = data.get("message", {})

            title = message.get("title", [""])[0] if message.get("title") else ""

            authors = []
            for author in message.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                if given and family:
                    authors.append(f"{given} {family}")
                elif family:
                    authors.append(family)
            authors_str = ", ".join(authors) if authors else ""

            year = ""
            if message.get("published-print"):
                date_parts = message["published-print"].get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    year = str(date_parts[0][0])
            elif message.get("published-online"):
                date_parts = message["published-online"].get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    year = str(date_parts[0][0])

            return jsonify({
                "valid": True,
                "doi": doi,
                "metadata": {
                    "title": title,
                    "authors": authors_str,
                    "year": year,
                }
            })
        else:
            return jsonify({"valid": False, "error": "DOI not found in CrossRef"}), 200

    except Exception as e:
        logger.error(f"Failed to validate DOI: {e}", exc_info=True)
        return jsonify({"valid": False, "error": "Failed to fetch DOI metadata"}), 200

@app.post("/api/save")
def save():
    """
    Expected JSON:
    {
      "sentence": "gene FLC regulates flowering time",
      "literature_link": "doi_or_url",
      "sentence_id": null | number (optional),
      "triples": [
        {
          "source_entity_name": "FLC",
          "source_entity_attr": "Gene" | "other",
          "new_source_entity_attr": "NewType (optional when 'other')",

          "relation_type": "regulates" | "other",
          "new_relation_type": "activates (optional when 'other')",

          "sink_entity_name": "flowering time",
          "sink_entity_attr": "Trait" | "other",
          "new_sink_entity_attr": "PhenotypeX (optional when 'other')"
        }
      ]
    }
    """
    try:
        payload: Dict[str, Any] = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    sentence = (payload.get("sentence") or "").strip()
    literature_link = (payload.get("literature_link") or "").strip()
    contributor_email = (payload.get("contributor_email") or "").strip()
    doi = (payload.get("doi") or "").strip() or None
    sentence_id = payload.get("sentence_id")
    project_id = payload.get("project_id")  # Get project_id from payload
    triples: List[Dict[str, Any]] = payload.get("triples") or []

    if not sentence:
        return jsonify({"error": "Missing 'sentence'"}), 400
    if not contributor_email:
        return jsonify({"error": "Missing 'contributor_email'"}), 400
    if not triples:
        return jsonify({"error": "Missing 'triples' array"}), 400

    # Handle any "other" entries (add new entity or relation types)
    try:
        for t in triples:
            # Relation type
            if t.get("relation_type") == "other":
                new_rel = (t.get("new_relation_type") or "").strip()
                if not new_rel:
                    return jsonify({"error": "relation_type is 'other' but 'new_relation_type' is empty"}), 400
                add_relation_type(DB_PATH, new_rel)
                t["relation_type"] = new_rel  # replace with actual value

            # Source entity attr
            if t.get("source_entity_attr") == "other":
                new_attr = (t.get("new_source_entity_attr") or "").strip()
                if not new_attr:
                    return jsonify({"error": "source_entity_attr is 'other' but 'new_source_entity_attr' is empty"}), 400
                add_entity_type(DB_PATH, new_attr, slugify(new_attr))
                t["source_entity_attr"] = new_attr

            # Sink entity attr
            if t.get("sink_entity_attr") == "other":
                new_attr = (t.get("new_sink_entity_attr") or "").strip()
                if not new_attr:
                    return jsonify({"error": "sink_entity_attr is 'other' but 'new_sink_entity_attr' is empty"}), 400
                add_entity_type(DB_PATH, new_attr, slugify(new_attr))
                t["sink_entity_attr"] = new_attr
    except Exception as e:
        logger.error(f"Failed to register new types: {e}", exc_info=True)
        return jsonify({"error": "Failed to register new entity types"}), 500

    # Upsert DOI metadata if present and get doi_hash
    doi_hash = None
    if doi:
        try:
            doi_hash = upsert_doi_metadata(DB_PATH, doi)
        except Exception as e:
            logger.error(f"Failed to save DOI metadata: {e}", exc_info=True)
            return jsonify({"error": "Failed to save DOI metadata"}), 500

    # Upsert the sentence, then insert triples
    try:
        sid = upsert_sentence(DB_PATH, sentence_id, sentence, literature_link, doi_hash)
        insert_triple_rows(DB_PATH, sid, triples, contributor_email, project_id)
        return jsonify({"ok": True, "sentence_id": sid, "doi_hash": doi_hash})
    except Exception as e:
        logger.error(f"Failed to save data: {e}", exc_info=True)
        return jsonify({"error": "Failed to save annotation data"}), 500

@app.delete("/api/triple/<int:triple_id>")
def delete_triple(triple_id: int):
    """
    Delete a triple. Only the original contributor or admin can delete.
    Expected JSON: { "email": "user@example.com", "password": "optional_for_admin" }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    requester_email = (payload.get("email") or "").strip()
    password = payload.get("password")

    if not requester_email:
        return jsonify({"error": "Missing 'email'"}), 400

    # Check admin status
    is_admin = check_admin_status(DB_PATH, requester_email, password)

    from harvest_store import get_conn
    try:
        conn = get_conn(DB_PATH)
        cur = conn.cursor()

        # Get triple info before deletion
        cur.execute("SELECT contributor_email, sentence_id FROM triples WHERE id = ?;", (triple_id,))
        result = cur.fetchone()

        if not result:
            conn.close()
            return jsonify({"error": "Triple not found"}), 404

        triple_owner, sentence_id = result[0], result[1]

        if not is_admin and triple_owner != requester_email:
            conn.close()
            return jsonify({"error": "Permission denied. Only the creator or admin can delete this triple."}), 403

        # Delete the triple
        cur.execute("DELETE FROM triples WHERE id = ?;", (triple_id,))
        
        # Check if sentence has any remaining triples
        cur.execute("SELECT COUNT(*) FROM triples WHERE sentence_id = ?;", (sentence_id,))
        remaining_triples = cur.fetchone()[0]
        
        # If no triples remain, delete the orphaned sentence
        if remaining_triples == 0:
            cur.execute("DELETE FROM sentences WHERE id = ?;", (sentence_id,))
            conn.commit()
            conn.close()
            return jsonify({"ok": True, "message": "Triple and associated sentence deleted (no other triples remained)"})
        
        conn.commit()
        conn.close()

        return jsonify({"ok": True, "message": "Triple deleted successfully"})
    except Exception as e:
        logger.error(f"Failed to delete triple: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete triple"}), 500

@app.get("/api/rows")
@app.get("/api/recent")
def rows():
    """
    List recent rows with DOI information.
    Note: Article metadata (title, authors, year) are not stored and would need to be fetched on-demand from CrossRef.
    Supports filtering by project_id via query parameter: /api/rows?project_id=1
    """
    from harvest_store import get_conn
    try:
        project_id = request.args.get('project_id', type=int)
        limit = request.args.get('limit', type=int)
        if limit is not None and limit <= 0:
            limit = None
        if limit and limit > MAX_BROWSE_LIMIT:
            limit = MAX_BROWSE_LIMIT
        
        conn = get_conn(DB_PATH)
        cur = conn.cursor()
        query = """
            SELECT s.id, s.text, s.literature_link, s.doi_hash,
                   dm.doi, t.id, t.source_entity_name,
                   t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                   t.contributor_email as triple_contributor, t.project_id
            FROM sentences s
            LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
            LEFT JOIN triples t ON s.id = t.sentence_id
        """
        params = []
        if project_id:
            query += " WHERE t.project_id = ?"
            params.append(project_id)
        query += " ORDER BY s.id DESC, t.id ASC"
        if limit and limit > 0:
            query += " LIMIT ?"
            params.append(limit)

        cur.execute(query, tuple(params))
        
        data = cur.fetchall()
        conn.close()
        cols = ["sentence_id", "sentence", "literature_link", "doi_hash",
                "doi", "triple_id",
                "source_entity_name", "source_entity_attr", "relation_type",
                "sink_entity_name", "sink_entity_attr", "triple_contributor", "project_id"]
        out = [dict(zip(cols, row)) for row in data]
        return jsonify(out)
    except Exception as e:
        logger.error(f"Failed to fetch rows: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch annotation data"}), 500

# -----------------------------
# Admin endpoints
# -----------------------------
@app.post("/api/admin/auth")
def admin_auth():
    """
    Authenticate admin user and return session token.
    Expected JSON: { "email": "admin@example.com", "password": "secret" }
    Returns: { "authenticated": true/false, "token": "...", "email": "...", "expires_in": 86400 }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    # Check if user exists in admin_users table
    authenticated = verify_admin_password(DB_PATH, email, password)
    
    # Also check if email is in environment variable list
    is_env_admin = is_admin_user(email)

    if authenticated or is_env_admin:
        # Generate and return token
        token = generate_admin_token(email)
        return jsonify({
            "authenticated": True,
            "is_admin": True,
            "token": token,
            "email": email,
            "expires_in": TOKEN_EXPIRATION
        })
    else:
        return jsonify({
            "authenticated": False,
            "is_admin": False
        }), 401


@app.get("/api/browse-fields")
def get_browse_fields():
    """
    Return the global browse visible fields configuration.
    Public endpoint so all sessions load the same defaults.
    """
    try:
        fields = get_browse_visible_fields(DB_PATH) or DEFAULT_BROWSE_VISIBLE_FIELDS
        sanitized = [f for f in fields if f in ALLOWED_BROWSE_FIELDS]
        if not sanitized:
            sanitized = DEFAULT_BROWSE_VISIBLE_FIELDS
        return jsonify({"fields": sanitized})
    except Exception as exc:  # pragma: no cover - defensive default
        logger.error(f"Failed to fetch browse fields: {exc}", exc_info=True)
        return jsonify({"fields": DEFAULT_BROWSE_VISIBLE_FIELDS})


@app.post("/api/admin/browse-fields")
def update_browse_fields():
    """
    Update the global browse visible fields configuration (admin only).
    Expected JSON: { "token": "...", OR "email": "...", "password": "...", "fields": [...] }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    is_authenticated, email = verify_admin_auth(payload)
    if not is_authenticated:
        return jsonify({"error": "Invalid admin credentials"}), 403

    fields = payload.get("fields") or payload.get("visible_fields") or []
    if not isinstance(fields, list):
        return jsonify({"error": "fields must be a list"}), 400

    sanitized = [f for f in fields if isinstance(f, str) and f in ALLOWED_BROWSE_FIELDS]
    if not sanitized:
        return jsonify({"error": "At least one valid field is required"}), 400

    try:
        set_browse_visible_fields(DB_PATH, sanitized)
        return jsonify({"ok": True, "fields": sanitized, "updated_by": email})
    except Exception as exc:
        logger.error(f"Failed to update browse fields: {exc}", exc_info=True)
        return jsonify({"error": "Failed to save browse field configuration"}), 500

@app.post("/api/admin/create-user")
def admin_create_user():
    """
    Create a new admin user (requires existing admin authentication).
    Expected JSON: { "admin_email": "admin@example.com", "admin_password": "secret", 
                     "new_email": "newadmin@example.com", "new_password": "newsecret" }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    admin_email = (payload.get("admin_email") or "").strip()
    admin_password = payload.get("admin_password") or ""
    new_email = (payload.get("new_email") or "").strip()
    new_password = payload.get("new_password") or ""

    if not admin_email or not admin_password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, admin_email, admin_password) or is_admin_user(admin_email)):
        return jsonify({"error": "Invalid admin credentials"}), 403

    if not new_email or not new_password:
        return jsonify({"error": "Missing new user email or password"}), 400

    success = create_admin_user(DB_PATH, new_email, new_password)
    if success:
        return jsonify({"ok": True, "message": "Admin user created successfully"})
    else:
        return jsonify({"error": "Failed to create admin user"}), 500

@app.put("/api/admin/triple/<int:triple_id>")
def admin_update_triple(triple_id: int):
    """
    Update a triple (admin only).
    Expected JSON: { "email": "admin@example.com", "password": "secret",
                     "source_entity_name": "...", "source_entity_attr": "...", etc. }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403

    # Extract update fields
    source_entity_name = payload.get("source_entity_name")
    source_entity_attr = payload.get("source_entity_attr")
    relation_type = payload.get("relation_type")
    sink_entity_name = payload.get("sink_entity_name")
    sink_entity_attr = payload.get("sink_entity_attr")

    success = update_triple(DB_PATH, triple_id, source_entity_name, source_entity_attr,
                          relation_type, sink_entity_name, sink_entity_attr)
    
    if success:
        return jsonify({"ok": True, "message": "Triple updated successfully"})
    else:
        return jsonify({"error": "Failed to update triple or triple not found"}), 404

# -----------------------------
# Project management endpoints
# -----------------------------
@app.post("/api/admin/projects")
def create_new_project():
    """
    Create a new project (admin only).
    Expected JSON: { "token": "...", OR "email": "admin@example.com", "password": "secret",
                     "name": "Project Name", "description": "...", "doi_list": ["10.1234/...", ...] }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Verify admin authentication (token or email/password)
    is_authenticated, email = verify_admin_auth(payload)
    if not is_authenticated:
        return jsonify({"error": "Invalid admin credentials"}), 403

    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    doi_list = payload.get("doi_list") or []

    if not name:
        return jsonify({"error": "Project name is required"}), 400
    if not doi_list or not isinstance(doi_list, list):
        return jsonify({"error": "DOI list is required and must be an array"}), 400

    # Validate DOIs concurrently with caching
    valid_dois, invalid_dois = validate_dois_concurrent(doi_list)
    
    if not valid_dois:
        return jsonify({"error": "No valid DOIs provided", "invalid_dois": invalid_dois}), 400

    project_id = create_project(DB_PATH, name, description, valid_dois, email)
    
    if project_id > 0:
        response_data = {
            "ok": True, 
            "project_id": project_id, 
            "message": "Project created successfully",
            "valid_count": len(valid_dois)
        }
        
        # Include warning about invalid DOIs if any
        if invalid_dois:
            response_data["warning"] = f"{len(invalid_dois)} DOI(s) failed validation and were excluded"
            response_data["invalid_dois"] = invalid_dois
            
        return jsonify(response_data)
    else:
        return jsonify({"error": "Failed to create project"}), 500

@app.get("/api/projects")
def list_projects():
    """
    List all projects (public endpoint).
    Returns: [{ "id": 1, "name": "...", "description": "...", "doi_list": [...] }]
    """
    try:
        projects = get_all_projects(DB_PATH)
        return jsonify(projects)
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Error fetching projects: {e}")
        return jsonify({"error": "Failed to fetch projects"}), 500

@app.get("/api/projects/<int:project_id>")
def get_project(project_id: int):
    """
    Get a specific project by ID (public endpoint).
    """
    try:
        project = get_project_by_id(DB_PATH, project_id)
        if project:
            return jsonify(project)
        else:
            return jsonify({"error": "Project not found"}), 404
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Error fetching project: {e}")
        return jsonify({"error": "Failed to fetch project"}), 500

@app.put("/api/admin/projects/<int:project_id>")
def update_existing_project(project_id: int):
    """
    Update a project (admin only).
    Expected JSON: { "token": "...", OR "email": "admin@example.com", "password": "secret",
                     "name": "...", "description": "...", "doi_list": [...] }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Verify admin authentication (token or email/password)
    is_authenticated, email = verify_admin_auth(payload)
    if not is_authenticated:
        return jsonify({"error": "Invalid admin credentials"}), 403

    name = payload.get("name")
    description = payload.get("description")
    doi_list = payload.get("doi_list")
    invalid_dois = []
    
    # Normalize and validate DOI list if provided
    if doi_list is not None and isinstance(doi_list, list):
        valid_dois, invalid_dois = validate_dois_concurrent(doi_list)
        doi_list = valid_dois
        
        # If no valid DOIs but invalid ones exist, return error
        if not doi_list and invalid_dois:
            return jsonify({
                "error": "No valid DOIs provided",
                "invalid_dois": invalid_dois
            }), 400

    success = update_project(DB_PATH, project_id, name, description, doi_list)
    
    if success:
        response_data = {
            "ok": True, 
            "message": "Project updated successfully"
        }
        
        # Include warning about invalid DOIs if any
        if doi_list is not None and invalid_dois:
            response_data["warning"] = f"{len(invalid_dois)} DOI(s) failed validation and were excluded"
            response_data["invalid_dois"] = invalid_dois
            response_data["valid_count"] = len(doi_list)
            
        return jsonify(response_data)
    else:
        return jsonify({"error": "Failed to update project or project not found"}), 404

@app.post("/api/admin/validate-dois")
def validate_dois():
    """
    Validate DOIs via CrossRef API (admin only).
    Expected JSON: { 
        "email": "admin@example.com", 
        "password": "secret",
        "dois": ["10.1234/example1", "10.1234/example2", ...]
    }
    Returns: {
        "valid": [...],  // List of valid DOIs
        "invalid": [{"doi": "...", "reason": "..."}]  // List of invalid DOIs with reasons
    }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    dois = payload.get("dois", [])

    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403

    if not isinstance(dois, list) or not dois:
        return jsonify({"error": "dois must be a non-empty list"}), 400

    import requests
    import time
    
    valid_dois = []
    invalid_dois = []
    
    for doi in dois:
        doi = normalize_doi(doi)  # Normalize DOI
        if not doi:
            continue
            
        try:
            # Check DOI via CrossRef API
            url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                valid_dois.append(doi)
            elif response.status_code == 404:
                invalid_dois.append({"doi": doi, "reason": "DOI not found in CrossRef database"})
            else:
                invalid_dois.append({"doi": doi, "reason": f"HTTP {response.status_code}"})
        except requests.exceptions.Timeout:
            invalid_dois.append({"doi": doi, "reason": "Request timeout"})
        except requests.exceptions.RequestException as e:
            invalid_dois.append({"doi": doi, "reason": f"Network error: {str(e)}"})
        except Exception as e:
            invalid_dois.append({"doi": doi, "reason": f"Error: {str(e)}"})
        
        # Rate limit: be nice to CrossRef API
        time.sleep(0.05)  # 50ms delay between requests
    
    return jsonify({
        "valid": valid_dois,
        "invalid": invalid_dois
    })

@app.post("/api/admin/projects/<int:project_id>/add-dois")
def add_dois_to_project(project_id: int):
    """
    Add DOIs to an existing project (admin only).
    Expected JSON: { 
        "email": "admin@example.com", 
        "password": "secret",
        "dois": ["10.1234/example1", "10.1234/example2", ...]
    }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Verify admin authentication (token or email/password)
    is_authenticated, email = verify_admin_auth(payload)
    if not is_authenticated:
        return jsonify({"error": "Invalid admin credentials"}), 403

    new_dois = payload.get("dois", [])

    if not isinstance(new_dois, list) or not new_dois:
        return jsonify({"error": "dois must be a non-empty list"}), 400

    # Get current project
    project = get_project_by_id(DB_PATH, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Get current DOI list (already normalized to lowercase in storage)
    current_dois = project.get("doi_list", [])
    
    # Validate new DOIs concurrently with caching
    valid_new_dois, invalid_dois = validate_dois_concurrent(new_dois)
    
    # If no valid DOIs but invalid ones exist, still report them as warning
    if not valid_new_dois:
        if invalid_dois:
            return jsonify({
                "ok": True,
                "message": "No valid DOIs to add",
                "warning": f"{len(invalid_dois)} DOI(s) failed validation",
                "invalid_dois": invalid_dois,
                "added_count": 0,
                "total_dois": len(current_dois)
            })
        else:
            return jsonify({"error": "No DOIs provided"}), 400
    
    # Create set of existing DOIs for deduplication
    existing_dois_set = set(current_dois)
    updated_dois = list(existing_dois_set | set(valid_new_dois))
    added_count = len(updated_dois) - len(current_dois)

    # Update project with new DOI list
    success = update_project(DB_PATH, project_id, doi_list=updated_dois)
    
    if success:
        response_data = {
            "ok": True, 
            "message": f"Added {added_count} new DOI(s) to project",
            "total_dois": len(updated_dois),
            "added_count": added_count
        }
        
        # Include warning about invalid DOIs if any
        if invalid_dois:
            response_data["warning"] = f"{len(invalid_dois)} DOI(s) failed validation and were excluded"
            response_data["invalid_dois"] = invalid_dois
            response_data["valid_count"] = len(valid_new_dois)
            
        return jsonify(response_data)
    else:
        return jsonify({"error": "Failed to update project"}), 500

@app.post("/api/admin/projects/<int:project_id>/remove-dois")
def remove_dois_from_project(project_id: int):
    """
    Remove DOIs from an existing project (admin only).
    Expected JSON: { 
        "email": "admin@example.com", 
        "password": "secret",
        "dois": ["10.1234/example1", "10.1234/example2", ...],
        "delete_pdfs": true/false  (optional, default: false)
    }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    dois_to_remove = payload.get("dois", [])
    delete_pdfs = payload.get("delete_pdfs", False)

    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403

    if not isinstance(dois_to_remove, list) or not dois_to_remove:
        return jsonify({"error": "dois must be a non-empty list"}), 400

    # Get current project
    project = get_project_by_id(DB_PATH, project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Get current DOI list (already normalized to lowercase in storage)
    current_dois = project.get("doi_list", [])
    
    # Normalize DOIs to remove to lowercase
    dois_to_remove_lower = {doi.strip().lower() for doi in dois_to_remove if doi.strip()}
    
    # Remove specified DOIs
    updated_dois = [doi for doi in current_dois if doi not in dois_to_remove_lower]
    removed_count = len(current_dois) - len(updated_dois)

    # Update project with new DOI list
    success = update_project(DB_PATH, project_id, doi_list=updated_dois)
    
    if not success:
        return jsonify({"error": "Failed to update project"}), 500

    # Delete PDFs if requested
    deleted_pdfs = []
    failed_deletions = []
    if delete_pdfs and removed_count > 0:
        try:
            from pdf_manager import get_project_pdf_dir
            project_dir = os.path.abspath(get_project_pdf_dir(project_id))
            
            for doi in dois_to_remove:
                doi_hash = generate_doi_hash(doi)
                if not doi_hash:
                    failed_deletions.append(f"{doi}: invalid DOI hash")
                    continue
                
                pdf_filename = f"{doi_hash}.pdf"
                pdf_path = os.path.abspath(os.path.join(project_dir, pdf_filename))
                
                # Security: Ensure the resolved path is within the project directory
                if not pdf_path.startswith(project_dir):
                    logger.error(f"Path traversal attempt detected: {doi} -> {pdf_path}")
                    failed_deletions.append(f"{doi}: invalid path")
                    continue
                
                if os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                        deleted_pdfs.append(doi)
                    except OSError as e:
                        failed_deletions.append(f"{doi}: {str(e)}")
        except Exception as e:
            logger.error(f"Error during PDF deletion for project {project_id}: {e}")
            failed_deletions.append(f"General error: {str(e)}")
    
    response_data = {
        "ok": True, 
        "message": f"Removed {removed_count} DOIs from project",
        "total_dois": len(updated_dois),
        "deleted_pdfs": len(deleted_pdfs)
    }
    
    if failed_deletions:
        response_data["deletion_warnings"] = failed_deletions
    
    return jsonify(response_data)

@app.delete("/api/admin/projects/<int:project_id>")
def delete_existing_project(project_id: int):
    """
    Delete a project (admin only).
    Expected JSON: { 
        "email": "admin@example.com", 
        "password": "secret",
        "handle_triples": "delete" | "reassign" | "keep"  (optional, default: "keep")
        "target_project_id": <id>  (required if handle_triples is "reassign")
    }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    handle_triples = payload.get("handle_triples", "keep")  # Default: keep triples (set project_id to NULL)
    target_project_id = payload.get("target_project_id")

    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403
    
    # Validate handle_triples option
    if handle_triples not in ["delete", "reassign", "keep"]:
        return jsonify({"error": "Invalid handle_triples option. Must be 'delete', 'reassign', or 'keep'"}), 400
    
    if handle_triples == "reassign" and not target_project_id:
        return jsonify({"error": "target_project_id required when handle_triples is 'reassign'"}), 400

    try:
        from harvest_store import get_conn
        conn = get_conn(DB_PATH)
        cur = conn.cursor()
        
        # Check how many triples are associated with this project
        cur.execute("SELECT COUNT(*) FROM triples WHERE project_id = ?;", (project_id,))
        triple_count = cur.fetchone()[0]
        
        orphaned_count = 0
        # Handle triples based on option
        if handle_triples == "delete":
            # Get all sentence_ids for triples we're about to delete
            cur.execute("SELECT DISTINCT sentence_id FROM triples WHERE project_id = ?;", (project_id,))
            sentence_ids = [row[0] for row in cur.fetchall()]
            
            # Delete all triples associated with this project
            cur.execute("DELETE FROM triples WHERE project_id = ?;", (project_id,))
            
            # Now check for orphaned sentences and delete them
            for sentence_id in sentence_ids:
                cur.execute("SELECT COUNT(*) FROM triples WHERE sentence_id = ?;", (sentence_id,))
                remaining_triples = cur.fetchone()[0]
                if remaining_triples == 0:
                    # This sentence has no more triples, delete it
                    cur.execute("DELETE FROM sentences WHERE id = ?;", (sentence_id,))
                    orphaned_count += 1
            
            conn.commit()
        elif handle_triples == "reassign":
            # Reassign triples to target project
            cur.execute("UPDATE triples SET project_id = ? WHERE project_id = ?;", (target_project_id, project_id))
            conn.commit()
        elif handle_triples == "keep":
            # Set project_id to NULL (uncategorized)
            cur.execute("UPDATE triples SET project_id = NULL WHERE project_id = ?;", (project_id,))
            conn.commit()
        
        # Now delete the project
        success = delete_project(DB_PATH, project_id)
        
        conn.close()
        
        if success:
            # Clean up project PDF directory
            import shutil
            from pdf_manager import get_project_pdf_dir
            project_pdf_dir = get_project_pdf_dir(project_id)
            
            pdf_cleanup_msg = ""
            if os.path.exists(project_pdf_dir):
                try:
                    shutil.rmtree(project_pdf_dir)
                    pdf_cleanup_msg = " Project PDF directory cleaned up."
                except Exception as e:
                    logging.warning(f"Failed to delete project PDF directory {project_pdf_dir}: {e}")
                    pdf_cleanup_msg = " (Warning: Could not remove PDF directory)"
            
            message = f"Project deleted successfully. {triple_count} triple(s) "
            if handle_triples == "delete":
                message += f"and {orphaned_count} orphaned sentence(s) were also deleted."
            elif handle_triples == "reassign":
                message += f"were reassigned to project {target_project_id}."
            else:
                message += "were set to uncategorized."
            message += pdf_cleanup_msg
            return jsonify({"ok": True, "message": message, "triples_affected": triple_count})
        else:
            return jsonify({"error": "Failed to delete project"}), 500
    except Exception as e:
        logger.error(f"Failed to delete project: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete project"}), 500

# PDF Management Endpoints
def _run_pdf_download_task(project_id: int, doi_list: List[str], project_dir: str):
    """Background task to download PDFs and update progress in database"""
    import json
    
    # Use the unified smart PDF manager
    try:
        from pdf_manager import process_dois_smart as process_function
        from pdf_manager import get_project_pdf_dir, generate_doi_hash
        print(f"[PDF Download Task] Using smart PDF download system")
    except ImportError as e:
        # Fallback to standard if smart version not available
        print(f"[PDF Download Task] Warning: Smart PDF manager not available, falling back to standard: {e}")
        from pdf_manager import process_project_dois_with_progress as process_function
        from pdf_manager import get_project_pdf_dir, generate_doi_hash
    
    print(f"[PDF Download Task] Starting background download for project {project_id}")
    
    # Note: Progress is already initialized in the main thread before this task starts
    # This avoids race condition where frontend polls before initialization
    
    # Track progress locally during processing
    downloaded = []
    needs_upload = []
    errors = []
    
    try:
        # Process DOIs with progress callback
        def progress_callback(current_idx: int, doi: str, success: bool, message: str, source: str = ""):
            print(f"[PDF Download Task] Progress: {current_idx + 1}/{len(doi_list)} - {doi}: {message}")
            
            doi_hash = ""
            try:
                from pdf_manager import generate_doi_hash
                doi_hash = generate_doi_hash(doi)
                filename = f"{doi_hash}.pdf"
            except (ImportError, ValueError, Exception) as e:
                print(f"[PDF Download Task] Warning: Could not generate doi_hash for {doi}: {e}")
                filename = "unknown.pdf"
            
            if success:
                downloaded.append((doi, filename, message, source))
            else:
                # Categorize failures: needs_upload (not available) vs errors (technical issues)
                # Patterns indicating the resource simply isn't available vs actual errors
                needs_upload_patterns = ["failed", "not found", "not open access", "not available", 
                                        "no accessible", "not a pdf", "too small"]
                is_needs_upload = any(pattern in message.lower() for pattern in needs_upload_patterns)
                
                if is_needs_upload:
                    needs_upload.append((doi, filename, message))
                else:
                    errors.append((doi, message))
            
            # Update database with current progress, including the last source used
            update_pdf_download_progress(DB_PATH, project_id, {
                "current": current_idx + 1,
                "current_doi": doi,
                "current_source": source if source else "none",
                "downloaded": downloaded,
                "needs_upload": needs_upload,
                "errors": errors
            })
        
        # Initialize the PDF download database (always use smart mode now)
        try:
            from pdf_download_db import init_pdf_download_db
            init_pdf_download_db()
            # Smart version needs project_id parameter
            results = process_function(doi_list, project_id, project_dir, progress_callback)
        except Exception as e:
            print(f"[PDF Download Task] Error: {e}")
            # Try fallback without project_id if using old function
            try:
                results = process_function(doi_list, project_dir, progress_callback)
            except TypeError:
                # Must be the smart function, re-raise original error
                raise e
        
        # Update final status in database
        update_pdf_download_progress(DB_PATH, project_id, {
            "status": "completed",
            "downloaded": results["downloaded"],
            "needs_upload": results["needs_upload"],
            "errors": results["errors"],
            "end_time": time.time()
        })
        
        print(f"[PDF Download Task] Completed - Downloaded: {len(results['downloaded'])}, "
              f"Needs upload: {len(results['needs_upload'])}, Errors: {len(results['errors'])}")
        
    except Exception as e:
        import traceback
        print(f"[PDF Download Task] Error: {e}")
        print(traceback.format_exc())
        update_pdf_download_progress(DB_PATH, project_id, {
            "status": "error",
            "end_time": time.time()
        })

@app.post("/api/admin/projects/<int:project_id>/download-pdfs")
def download_project_pdfs(project_id: int):
    """
    Start PDF download for all DOIs in a project (admin only).
    Expected JSON: { "email": "admin@example.com", "password": "secret", "force_restart": false }
    
    If force_restart is true, will reset any stale downloads and start fresh.
    
    Returns: Immediate response, use /download-pdfs/status to check progress
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception as e:
        print(f"[PDF Download] Invalid JSON: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    force_restart = payload.get("force_restart", False)

    if not email or not password:
        print(f"[PDF Download] Missing authentication for project {project_id}")
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        print(f"[PDF Download] Invalid credentials for {email}")
        return jsonify({"error": "Invalid admin credentials"}), 403
    
    # Check if download is already running for this project (check database)
    progress = get_pdf_download_progress(DB_PATH, project_id)
    if progress and progress.get("status") == "running":
        # Check if the download is stale (not updated recently)
        if is_download_stale(DB_PATH, project_id, stale_threshold_seconds=300):
            print(f"[PDF Download] Detected stale download for project {project_id}, resetting...")
            reset_stale_download(DB_PATH, project_id)
            # Re-fetch progress after reset
            progress = get_pdf_download_progress(DB_PATH, project_id)
        elif force_restart:
            print(f"[PDF Download] Force restart requested for project {project_id}")
            reset_stale_download(DB_PATH, project_id)
            progress = get_pdf_download_progress(DB_PATH, project_id)
        else:
            print(f"[PDF Download] Download already in progress for project {project_id}")
            return jsonify({
                "error": "Download already in progress for this project",
                "hint": "If the download appears stuck, you can force restart it by setting 'force_restart': true"
            }), 409
    
    # Get project
    project = get_project_by_id(DB_PATH, project_id)
    if not project:
        print(f"[PDF Download] Project {project_id} not found")
        return jsonify({"error": "Project not found"}), 404
    
    try:
        import json
        from pdf_manager import get_project_pdf_dir
        
        doi_list = json.loads(project["doi_list"]) if isinstance(project["doi_list"], str) else project["doi_list"]
        project_dir = get_project_pdf_dir(project_id)
        
        print(f"[PDF Download] Starting download for project {project_id} ({project.get('name', 'Unknown')}) "
              f"with {len(doi_list)} DOIs")
        print(f"[PDF Download] Target directory: {project_dir}")
        print(f"[PDF Download] Requested by: {email}")
        
        # Initialize progress in database before starting thread to avoid race condition
        if not init_pdf_download_progress(DB_PATH, project_id, len(doi_list), project_dir):
            print(f"[PDF Download] Failed to initialize download progress for project {project_id}")
            return jsonify({"error": "Failed to initialize download progress. See server logs."}), 500
        
        # Start background thread
        thread = threading.Thread(
            target=_run_pdf_download_task,
            args=(project_id, doi_list, project_dir),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "ok": True,
            "message": "PDF download started",
            "project_id": project_id,
            "total_dois": len(doi_list),
            "status_url": f"/api/admin/projects/{project_id}/download-pdfs/status"
        })
        
    except Exception as e:
        import traceback
        print(f"[PDF Download] Error starting download: {e}")
        print(traceback.format_exc())
        # Don't expose detailed error messages to client
        return jsonify({"error": "Failed to start download. Please check server logs for details."}), 500

@app.get("/api/admin/projects/<int:project_id>/download-pdfs/status")
def get_pdf_download_status(project_id: int):
    """
    Get the current status of PDF download for a project from database.
    Returns progress information if download is in progress or completed.
    Also includes information about whether the download is stale.
    """
    print(f"[PDF Download Status] Checking status for project {project_id}")
    
    progress = get_pdf_download_progress(DB_PATH, project_id)
    
    if not progress:
        return jsonify({"status": "not_started"}), 404
    
    print(f"[PDF Download Status] Project {project_id}: status={progress.get('status')}, "
          f"current={progress.get('current')}/{progress.get('total')}")
    
    # Check if download is stale (for running downloads only)
    is_stale = False
    time_since_update = None
    if progress.get("status") == "running":
        is_stale = is_download_stale(DB_PATH, project_id, stale_threshold_seconds=300)
        import time
        updated_at = progress.get("updated_at", 0)
        time_since_update = int(time.time() - updated_at)
    
    # Get active download mechanisms
    try:
        from pdf_manager import get_active_download_mechanisms
        active_mechanisms = get_active_download_mechanisms()
        mechanisms_info = [
            {"name": m['name'], "description": m.get('description', '')}
            for m in active_mechanisms
        ]
    except Exception as e:
        print(f"[PDF Download Status] Could not get active mechanisms: {e}")
        mechanisms_info = []
    
    # Return current progress
    response = {
        "ok": True,
        "status": progress.get("status"),
        "total": progress.get("total", 0),
        "current": progress.get("current", 0),
        "current_doi": progress.get("current_doi", ""),
        "current_source": progress.get("current_source", ""),
        "downloaded_count": len(progress.get("downloaded", [])),
        "needs_upload_count": len(progress.get("needs_upload", [])),
        "errors_count": len(progress.get("errors", [])),
        "downloaded": progress.get("downloaded", [])[:10],  # Return first 10 for preview
        "needs_upload": progress.get("needs_upload", [])[:10],
        "errors": progress.get("errors", [])[:5],
        "project_dir": progress.get("project_dir", ""),
        "active_mechanisms": mechanisms_info,  # List of active download sources
        # Include full results when completed
        "full_results": {
            "downloaded": progress.get("downloaded", []),
            "needs_upload": progress.get("needs_upload", []),
            "errors": progress.get("errors", [])
        } if progress.get("status") == "completed" else None
    }
    
    # Add stale detection info for running downloads
    if progress.get("status") == "running":
        response["is_stale"] = is_stale
        response["time_since_update_seconds"] = time_since_update
        if is_stale:
            response["warning"] = "Download appears to be stale (not updated recently). You can force restart it."
    
    return jsonify(response)

@app.get("/api/pdf-download-config")
def get_pdf_download_config():
    """Get PDF download configuration and available sources (public endpoint)"""
    try:
        from pdf_manager import get_active_download_mechanisms
        
        # Get active download mechanisms from database
        active_mechanisms = get_active_download_mechanisms()
        
        # Format for API response
        sources = []
        for idx, mechanism in enumerate(active_mechanisms, 1):
            sources.append({
                "name": mechanism['name'],
                "enabled": mechanism.get('enabled', True),
                "available": True,  # If it's in active list, it's available
                "order": idx,
                "description": mechanism.get('description', ''),
                "success_rate": mechanism.get('success_rate', 0.0),
                "total_attempts": mechanism.get('total_attempts', 0),
                "avg_response_time_ms": mechanism.get('avg_response_time_ms', 0.0)
            })
        
        return jsonify({
            "ok": True,
            "sources": sources,
            "total_sources": len(sources),
            "active_sources": len([s for s in sources if s['enabled']])
        })
        
    except Exception as e:
        logger.error(f"Failed to get PDF configuration: {e}", exc_info=True)
        return jsonify({"error": "Failed to get PDF configuration"}), 500


# =============================================================================
# DOI Batch Management API Endpoints
# =============================================================================

@app.post("/api/admin/projects/<int:project_id>/batches")
def create_batches_endpoint(project_id: int):
    """
    Create batches for a project's DOIs (admin only).
    Request body:
    {
        "batch_size": 20,  # DOIs per batch (default 20)
        "strategy": "sequential"  # or "random"
    }
    """
    # Check admin authentication
    if not request.json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    email = request.json.get("admin_email")
    password = request.json.get("admin_password")
    
    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401
    
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 401
    
    try:
        batch_size = request.json.get("batch_size", 20)
        strategy = request.json.get("strategy", "sequential")
        
        # Validate batch size
        if not isinstance(batch_size, int) or batch_size < 5 or batch_size > 100:
            return jsonify({"error": "batch_size must be between 5 and 100"}), 400
        
        # Validate strategy
        if strategy not in ["sequential", "random"]:
            return jsonify({"error": "strategy must be 'sequential' or 'random'"}), 400
        
        # Create batches
        batches = create_batches(DB_PATH, project_id, batch_size, strategy)
        
        if not batches:
            return jsonify({"error": "Failed to create batches. Project may not exist or have no DOIs."}), 404
        
        return jsonify({
            "ok": True,
            "batches": batches,
            "total_batches": len(batches)
        })
        
    except Exception as e:
        logger.error(f"Failed to create batches: {e}", exc_info=True)
        return jsonify({"error": "Failed to create batches"}), 500


@app.get("/api/projects/<int:project_id>/batches")
def get_project_batches_endpoint(project_id: int):
    """Get all batches for a project (public)"""
    try:
        batches = get_project_batches(DB_PATH, project_id)
        return jsonify({
            "ok": True,
            "batches": batches
        })
    except Exception as e:
        logger.error(f"Failed to get project batches: {e}", exc_info=True)
        return jsonify({"error": "Failed to get project batches"}), 500


@app.get("/api/projects/<int:project_id>/batches/<int:batch_id>/dois")
def get_batch_dois_endpoint(project_id: int, batch_id: int):
    """Get all DOIs in a specific batch with their status and PDF indicators (public)"""
    try:
        dois = get_batch_dois(DB_PATH, project_id, batch_id)
        
        # Add PDF indicators to each DOI
        from pdf_manager import get_project_pdf_dir
        project_dir = get_project_pdf_dir(project_id)
        
        for doi_info in dois:
            doi = doi_info['doi']
            doi_hash = generate_doi_hash(doi)
            pdf_path = os.path.join(project_dir, f"{doi_hash}.pdf")
            doi_info['has_pdf'] = os.path.exists(pdf_path)
        
        return jsonify({
            "ok": True,
            "dois": dois
        })
    except Exception as e:
        logger.error(f"Failed to get batch DOIs: {e}", exc_info=True)
        return jsonify({"error": "Failed to get batch DOIs"}), 500


@app.post("/api/projects/<int:project_id>/dois/<path:doi>/status")
def update_doi_status_endpoint(project_id: int, doi: str):
    """
    Update the annotation status of a DOI.
    Request body:
    {
        "status": "in_progress" | "completed",
        "annotator_email": "user@example.com"
    }
    """
    try:
        if not request.json:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        status = request.json.get("status")
        annotator_email = request.json.get("annotator_email")
        
        # Validate status
        if status not in ["unstarted", "in_progress", "completed"]:
            return jsonify({"error": "status must be 'unstarted', 'in_progress', or 'completed'"}), 400
        
        # Update status
        success = update_doi_status(DB_PATH, project_id, doi, status, annotator_email)
        
        if success:
            return jsonify({"ok": True})
        else:
            return jsonify({"error": "Failed to update DOI status"}), 500
            
    except Exception as e:
        logger.error(f"Failed to update DOI status: {e}", exc_info=True)
        return jsonify({"error": "Failed to update DOI status"}), 500


@app.get("/api/projects/<int:project_id>/doi-status")
def get_doi_status_summary_endpoint(project_id: int):
    """Get annotation status summary for all DOIs in project (public)"""
    try:
        summary = get_doi_status_summary(DB_PATH, project_id)
        return jsonify({
            "ok": True,
            **summary
        })
    except Exception as e:
        logger.error(f"Failed to get DOI status summary: {e}", exc_info=True)
        return jsonify({"error": "Failed to get DOI status summary"}), 500


@app.get("/api/projects/<int:project_id>/pdfs")
def list_project_pdfs_endpoint(project_id: int):
    """List all PDFs available for a project (public)"""
    try:
        from pdf_manager import get_project_pdf_dir, list_project_pdfs
        
        project_dir = get_project_pdf_dir(project_id)
        pdfs = list_project_pdfs(project_dir)
        
        return jsonify({
            "ok": True,
            "project_id": project_id,
            "pdf_count": len(pdfs),
            "pdfs": pdfs
        })
    except Exception as e:
        logger.error(f"Failed to list PDFs: {e}", exc_info=True)
        return jsonify({"error": "Failed to list PDFs"}), 500

@app.get("/api/projects/<int:project_id>/dois-with-pdfs")
def get_dois_with_pdf_indicators(project_id: int):
    """
    Get DOI list with indicators showing which have associated PDFs.
    Returns: {"ok": True, "dois": [{"doi": "10.1234/example", "has_pdf": true}, ...]}
    """
    try:
        # Get project DOI list
        project = get_project_by_id(DB_PATH, project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404
        
        doi_list = project.get("doi_list", [])
        
        # Get list of available PDFs
        from pdf_manager import get_project_pdf_dir
        project_dir = get_project_pdf_dir(project_id)
        
        # Check which DOIs have PDFs
        dois_with_indicators = []
        for doi in doi_list:
            doi_hash = generate_doi_hash(doi)
            pdf_path = os.path.join(project_dir, f"{doi_hash}.pdf")
            has_pdf = os.path.exists(pdf_path)
            dois_with_indicators.append({
                "doi": doi,
                "has_pdf": has_pdf
            })
        
        return jsonify({
            "ok": True,
            "project_id": project_id,
            "dois": dois_with_indicators
        })
    except Exception as e:
        logger.error(f"Failed to get DOIs with PDF indicators: {e}", exc_info=True)
        return jsonify({"error": "Failed to get DOI list"}), 500

@app.post("/api/admin/projects/<int:project_id>/upload-pdf")
def upload_project_pdf(project_id: int):
    """
    Upload a PDF file for a project (admin only).
    Expects multipart/form-data with:
    - email: admin email
    - password: admin password
    - file: PDF file
    - doi: DOI for the PDF
    """
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    doi = request.form.get("doi", "").strip()
    
    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401
    
    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403
    
    if not doi:
        return jsonify({"error": "DOI required"}), 400
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "File must be a PDF"}), 400
    
    try:
        from pdf_manager import get_project_pdf_dir, generate_doi_hash
        import os
        from pathlib import Path
        
        project_dir = get_project_pdf_dir(project_id)
        Path(project_dir).mkdir(parents=True, exist_ok=True)
        
        doi_hash = generate_doi_hash(doi)
        filename = f"{doi_hash}.pdf"
        filepath = os.path.join(project_dir, filename)
        
        file.save(filepath)
        file_size = os.path.getsize(filepath)
        
        return jsonify({
            "ok": True,
            "message": "PDF uploaded successfully",
            "doi": doi,
            "filename": filename,
            "size": file_size
        })
    except Exception as e:
        logger.error(f"PDF upload failed: {e}", exc_info=True)
        return jsonify({"error": "PDF upload failed"}), 500

@app.get("/api/projects/<int:project_id>/pdf/<filename>")
def serve_project_pdf(project_id: int, filename: str):
    """Serve a PDF file from a project directory"""
    try:
        from flask import send_file
        from pdf_manager import get_project_pdf_dir
        import os
        
        # Security: only allow .pdf files and no path traversal
        if not filename.endswith('.pdf') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        project_dir = get_project_pdf_dir(project_id)
        filepath = os.path.join(project_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "PDF not found"}), 404
        
        return send_file(filepath, mimetype='application/pdf')
    except Exception as e:
        logger.error(f"Failed to serve PDF: {e}", exc_info=True)
        return jsonify({"error": "Failed to serve PDF"}), 500

@app.post("/api/projects/<int:project_id>/pdf/<filename>/highlights")
def add_pdf_highlights(project_id: int, filename: str):
    """
    Add highlights to a PDF file.
    Expected JSON: {
        "highlights": [
            {
                "page": 0,
                "rects": [[x0, y0, x1, y1], ...],
                "color": "#FFFF00" or [1.0, 1.0, 0.0],
                "text": "optional highlighted text"
            }
        ]
    }
    """
    try:
        # Check if highlighting feature is enabled
        if not ENABLE_PDF_HIGHLIGHTING:
            return jsonify({"error": "PDF highlighting feature is disabled"}), 403
        
        from pdf_manager import get_project_pdf_dir
        from pdf_annotator import add_highlights_to_pdf
        import os
        
        # Security: only allow .pdf files and no path traversal
        if not filename.endswith('.pdf') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        # Get JSON payload
        try:
            payload = request.get_json(force=True, silent=False)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400
        
        if not payload or 'highlights' not in payload:
            return jsonify({"error": "Missing 'highlights' in request"}), 400
        
        highlights = payload['highlights']
        if not isinstance(highlights, list):
            return jsonify({"error": "'highlights' must be a list"}), 400
        
        # Get PDF path
        project_dir = get_project_pdf_dir(project_id)
        filepath = os.path.join(project_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "PDF not found"}), 404
        
        # Add highlights
        success, message = add_highlights_to_pdf(filepath, highlights)
        
        if success:
            # Count highlights for response (message is safe but use sanitized version)
            count = len(highlights)
            return jsonify({"success": True, "message": f"Added {count} highlight(s)"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to add highlights"}), 400
    
    except Exception as e:
        logger.error(f"Error in add_pdf_highlights: {e}", exc_info=True)
        return jsonify({"error": "Failed to add highlights"}), 500

@app.get("/api/projects/<int:project_id>/pdf/<filename>/highlights")
def get_pdf_highlights(project_id: int, filename: str):
    """Get all highlights from a PDF file"""
    try:
        # Check if highlighting feature is enabled
        if not ENABLE_PDF_HIGHLIGHTING:
            return jsonify({"error": "PDF highlighting feature is disabled"}), 403
        
        from pdf_manager import get_project_pdf_dir
        from pdf_annotator import get_highlights_from_pdf
        import os
        
        # Security: only allow .pdf files and no path traversal
        if not filename.endswith('.pdf') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        # Get PDF path
        project_dir = get_project_pdf_dir(project_id)
        filepath = os.path.join(project_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "PDF not found"}), 404
        
        # Get highlights
        success, highlights, message = get_highlights_from_pdf(filepath)
        
        if success:
            # Return highlights with sanitized message
            count = len(highlights) if highlights else 0
            return jsonify({
                "success": True,
                "highlights": highlights,
                "message": f"Found {count} highlight(s)"
            }), 200
        else:
            return jsonify({"success": False, "error": "Failed to get highlights"}), 400
    
    except Exception as e:
        logger.error(f"Error in get_pdf_highlights: {e}", exc_info=True)
        return jsonify({"error": "Failed to get highlights"}), 500

@app.delete("/api/projects/<int:project_id>/pdf/<filename>/highlights")
def delete_pdf_highlights(project_id: int, filename: str):
    """Remove all highlights from a PDF file"""
    try:
        # Check if highlighting feature is enabled
        if not ENABLE_PDF_HIGHLIGHTING:
            return jsonify({"error": "PDF highlighting feature is disabled"}), 403
        
        from pdf_manager import get_project_pdf_dir
        from pdf_annotator import clear_all_highlights
        import os
        
        # Security: only allow .pdf files and no path traversal
        if not filename.endswith('.pdf') or '/' in filename or '\\' in filename:
            return jsonify({"error": "Invalid filename"}), 400
        
        # Get PDF path
        project_dir = get_project_pdf_dir(project_id)
        filepath = os.path.join(project_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"error": "PDF not found"}), 404
        
        # Clear highlights
        success, message = clear_all_highlights(filepath)
        
        if success:
            # Use generic success message (actual count is logged but not exposed)
            return jsonify({"success": True, "message": "Highlights cleared successfully"}), 200
        else:
            return jsonify({"success": False, "error": "Failed to clear highlights"}), 400
    
    except Exception as e:
        logger.error(f"Error in delete_pdf_highlights: {e}", exc_info=True)
        return jsonify({"error": "Failed to clear highlights"}), 500

@app.get("/api/debug/pdf-highlighting")
def debug_pdf_highlighting():
    """
    Debug endpoint to check PDF highlighting dependencies and configuration.
    This helps diagnose issues with the PDF highlighting feature.
    """
    import sys
    import traceback
    
    debug_info = {
        "enabled": ENABLE_PDF_HIGHLIGHTING,
        "python_version": sys.version,
        "checks": {}
    }
    
    # Check PyMuPDF import
    try:
        import fitz
        debug_info["checks"]["pymupdf"] = {
            "status": "installed",
            "version": fitz.__version__
        }
    except ImportError as e:
        debug_info["checks"]["pymupdf"] = {
            "status": "missing",
            "error": str(e)
        }
    
    # Check pdf_annotator import
    try:
        from pdf_annotator import add_highlights_to_pdf, get_highlights_from_pdf, clear_all_highlights
        debug_info["checks"]["pdf_annotator"] = {
            "status": "ok",
            "functions": ["add_highlights_to_pdf", "get_highlights_from_pdf", "clear_all_highlights"]
        }
    except Exception as e:
        debug_info["checks"]["pdf_annotator"] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    # Check pdf_manager import
    try:
        from pdf_manager import get_project_pdf_dir
        debug_info["checks"]["pdf_manager"] = {
            "status": "ok",
            "functions": ["get_project_pdf_dir"]
        }
    except Exception as e:
        debug_info["checks"]["pdf_manager"] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    # Check if there are any test PDFs
    try:
        from pdf_manager import get_project_pdf_dir
        test_project_dir = get_project_pdf_dir(1)
        import os
        if os.path.exists(test_project_dir):
            pdf_files = [f for f in os.listdir(test_project_dir) if f.endswith('.pdf')]
            debug_info["checks"]["test_pdfs"] = {
                "directory": test_project_dir,
                "count": len(pdf_files),
                "files": pdf_files[:5]  # First 5 PDFs
            }
        else:
            debug_info["checks"]["test_pdfs"] = {
                "directory": test_project_dir,
                "exists": False
            }
    except Exception as e:
        debug_info["checks"]["test_pdfs"] = {
            "status": "error",
            "error": str(e)
        }
    
    return jsonify(debug_info), 200

@app.post("/api/admin/export/triples")
def export_triples_json():
    """
    Export all triples from the database as JSON (admin only).
    Expected JSON: { "email": "admin@example.com", "password": "secret" }
    Returns a JSON file with all triple data including sentences, metadata, and relationships.
    """
    try:
        # Get credentials from JSON body
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    
    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    
    try:
        # Verify admin status
        is_admin = check_admin_status(DB_PATH, email, password)
        if not is_admin:
            return jsonify({"error": "Unauthorized: Admin access required"}), 403
        
        import sqlite3
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Export structure
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat() + "Z",
            "database": DB_PATH,
            "schema_version": "v2",
            "triples": [],
            "sentences": [],
            "doi_metadata": [],
            "projects": [],
            "entity_types": [],
            "relation_types": []
        }
        
        # Get all triples
        cursor.execute("""
            SELECT id, sentence_id, source_entity_name, source_entity_attr, relation_type, 
                   sink_entity_name, sink_entity_attr, contributor_email, created_at, project_id
            FROM triples
            ORDER BY id
        """)
        for row in cursor.fetchall():
            export_data["triples"].append(dict(row))
        
        # Get all sentences
        cursor.execute("""
            SELECT id, text, literature_link, doi_hash, created_at
            FROM sentences
            ORDER BY id
        """)
        for row in cursor.fetchall():
            export_data["sentences"].append(dict(row))
        
        # Get all DOI metadata
        cursor.execute("""
            SELECT doi_hash, doi, created_at
            FROM doi_metadata
            ORDER BY doi_hash
        """)
        for row in cursor.fetchall():
            export_data["doi_metadata"].append(dict(row))
        
        # Get all projects
        cursor.execute("""
            SELECT id, name, description, doi_list, created_by, created_at
            FROM projects
            ORDER BY id
        """)
        for row in cursor.fetchall():
            export_data["projects"].append(dict(row))
        
        # Get all entity types
        cursor.execute("""
            SELECT name, value
            FROM entity_types
            ORDER BY name
        """)
        for row in cursor.fetchall():
            export_data["entity_types"].append(dict(row))
        
        # Get all relation types
        cursor.execute("""
            SELECT name
            FROM relation_types
            ORDER BY name
        """)
        for row in cursor.fetchall():
            export_data["relation_types"].append(dict(row))
        
        conn.close()
        
        # Add statistics
        export_data["statistics"] = {
            "total_triples": len(export_data["triples"]),
            "total_sentences": len(export_data["sentences"]),
            "total_dois": len(export_data["doi_metadata"]),
            "total_projects": len(export_data["projects"]),
            "entity_type_count": len(export_data["entity_types"]),
            "relation_type_count": len(export_data["relation_types"])
        }
        
        logger.info(f"Admin {email} exported triples database: {export_data['statistics']}")
        
        # Return JSON response in standard format
        return jsonify({
            "ok": True,
            "data": export_data
        })
    
    except Exception as e:
        logger.error(f"Error exporting triples: {e}", exc_info=True)
        return jsonify({"ok": False, "error": "Failed to export triples"}), 500



# =============================================================================
# Email Verification API Endpoints (OTP Authentication)
# =============================================================================

@app.post("/api/email-verification/request-code")
def request_verification_code():
    """
    Request OTP verification code for email.
    Sends verification code to the provided email address.
    """
    try:
        # Check if feature is enabled
        try:
            from config import ENABLE_OTP_VALIDATION
            if not ENABLE_OTP_VALIDATION:
                return jsonify({
                    "success": False,
                    "error": "Email verification feature is disabled"
                }), 503
        except ImportError:
            return jsonify({
                "success": False,
                "error": "Email verification configuration not found"
            }), 503
        
        # Import email verification modules
        try:
            from email_service import get_email_service, EmailService
            from email_verification_store import (
                check_rate_limit,
                record_code_request,
                store_verification_code
            )
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"Email verification modules not available: {str(e)}"
            }), 500
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        email = data.get("email", "").strip().lower()
        if not email:
            return jsonify({
                "success": False,
                "error": "Email is required"
            }), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                "success": False,
                "error": "Invalid email format"
            }), 400
        
        # Get IP address for rate limiting
        ip_address = request.remote_addr or ""
        
        # Check rate limit
        allowed, msg = check_rate_limit(DB_PATH, email, ip_address)
        if not allowed:
            return jsonify({
                "success": False,
                "error": msg
            }), 429
        
        # Record code request
        record_code_request(DB_PATH, email, ip_address)
        
        # Generate and send verification code
        try:
            email_service = get_email_service()
            success, message, code_hash = email_service.send_verification_email(email)
            
            if success and code_hash:
                # Store code in database
                store_verification_code(DB_PATH, email, code_hash, ip_address=ip_address)
                
                return jsonify({
                    "success": True,
                    "message": "Verification code sent to your email"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": message
                }), 500
                
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to send verification email: {str(e)}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in request_verification_code: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected server error occurred."
        }), 500


@app.post("/api/email-verification/verify-code")
def verify_verification_code():
    """
    Verify OTP code for email.
    Creates verified session if code is valid.
    """
    try:
        # Check if feature is enabled
        try:
            from config import ENABLE_OTP_VALIDATION
            if not ENABLE_OTP_VALIDATION:
                return jsonify({
                    "success": False,
                    "error": "Email verification feature is disabled"
                }), 503
        except ImportError:
            return jsonify({
                "success": False,
                "error": "Email verification configuration not found"
            }), 503
        
        # Import email verification modules
        try:
            from email_service import EmailService
            from email_verification_store import verify_code, create_verified_session
            import uuid
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"Email verification modules not available: {str(e)}"
            }), 500
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        email = data.get("email", "").strip().lower()
        code = data.get("code", "").strip()
        
        if not email or not code:
            return jsonify({
                "success": False,
                "error": "Email and code are required"
            }), 400
        
        # Verify code
        result = verify_code(DB_PATH, email, code, EmailService.verify_code)
        
        if result["valid"]:
            # Create verified session
            session_id = str(uuid.uuid4())
            ip_address = request.remote_addr or ""
            
            if create_verified_session(DB_PATH, session_id, email, ip_address=ip_address):
                return jsonify({
                    "success": True,
                    "message": "Email verified successfully",
                    "session_id": session_id,
                    "email": email
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to create verified session"
                }), 500
        else:
            status_code = 400
            if result.get("expired"):
                status_code = 410  # Gone
            elif result.get("attempts_exceeded"):
                status_code = 429  # Too Many Requests
            
            return jsonify({
                "success": False,
                "error": result["message"],
                "expired": result.get("expired", False),
                "attempts_exceeded": result.get("attempts_exceeded", False)
            }), status_code
            
    except Exception as e:
        logger.error(f"Error in verify_verification_code: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.post("/api/email-verification/check-session")
def check_verification_session():
    """
    Check if session is verified and not expired.
    Returns email if valid.
    """
    try:
        # Check if feature is enabled
        try:
            from config import ENABLE_OTP_VALIDATION
            if not ENABLE_OTP_VALIDATION:
                return jsonify({
                    "verified": False,
                    "error": "Email verification feature is disabled"
                }), 503
        except ImportError:
            return jsonify({
                "verified": False,
                "error": "Email verification configuration not found"
            }), 503
        
        # Import email verification modules
        try:
            from email_verification_store import check_verified_session
        except ImportError as e:
            return jsonify({
                "verified": False,
                "error": f"Email verification modules not available: {str(e)}"
            }), 500
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                "verified": False,
                "error": "No data provided"
            }), 400
        
        session_id = data.get("session_id", "").strip()
        if not session_id:
            return jsonify({
                "verified": False,
                "error": "Session ID is required"
            }), 400
        
        # Check session
        email = check_verified_session(DB_PATH, session_id)
        
        if email:
            return jsonify({
                "verified": True,
                "email": email
            })
        else:
            return jsonify({
                "verified": False,
                "error": "Session not found or expired"
            }), 404
            
    except Exception as e:
        logger.error(f"Error in check_verification_session: {e}")
        return jsonify({
            "verified": False,
            "error": str(e)
        }), 500


@app.get("/api/email-verification/config")
def get_verification_config():
    """
    Get email verification configuration (non-sensitive info).
    Returns whether feature is enabled and configuration details.
    """
    try:
        # Check if feature is enabled
        try:
            from config import ENABLE_OTP_VALIDATION
            from email_config import OTP_CONFIG, EMAIL_PROVIDER
            
            return jsonify({
                "enabled": ENABLE_OTP_VALIDATION,
                "provider": EMAIL_PROVIDER if ENABLE_OTP_VALIDATION else None,
                "code_length": OTP_CONFIG["code_length"] if ENABLE_OTP_VALIDATION else None,
                "code_expiry_minutes": OTP_CONFIG["code_expiry_seconds"] // 60 if ENABLE_OTP_VALIDATION else None,
                "session_expiry_hours": OTP_CONFIG["session_expiry_seconds"] // 3600 if ENABLE_OTP_VALIDATION else None,
                "max_attempts": OTP_CONFIG["max_attempts"] if ENABLE_OTP_VALIDATION else None
            })
        except ImportError:
            return jsonify({
                "enabled": False,
                "error": "Email verification not configured"
            })
            
    except Exception as e:
        logger.error(f"Error in get_verification_config: {e}")
        return jsonify({
            "enabled": False,
            "error": str(e)
        }), 500


# =============================================================================
# Literature Review API Endpoints (ASReview Integration)
# =============================================================================

@app.get("/api/literature-review/health")
def literature_review_health():
    """
    Check if Literature Review feature is available and configured.
    Returns health status of ASReview service integration.
    """
    try:
        # Check if feature is enabled
        try:
            from config import ENABLE_LITERATURE_REVIEW
            if not ENABLE_LITERATURE_REVIEW:
                return jsonify({
                    "ok": False,
                    "available": False,
                    "error": "Literature Review feature is disabled in config"
                })
        except ImportError:
            ENABLE_LITERATURE_REVIEW = True  # Default to enabled
        
        # Check ASReview service configuration
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        if not client.is_configured():
            return jsonify({
                "ok": True,
                "available": False,
                "configured": False,
                "error": "ASReview service URL not configured. Please set ASREVIEW_SERVICE_URL in config.py"
            })
        
        # Check ASReview service health
        health_status = client.check_health()
        
        return jsonify({
            "ok": True,
            "available": health_status.get('available', False),
            "configured": True,
            "service_url": client.service_url if client.service_url else None,
            "version": health_status.get('version'),
            "status": health_status.get('status'),
            "error": health_status.get('error')
        })
    
    except Exception as e:
        logger.error(f"Error checking literature review health: {e}", exc_info=True)
        return jsonify({
            "ok": False,
            "available": False,
            "error": str(e)
        }), 500


@app.post("/api/literature-review/projects")
def create_literature_review_project():
    """
    Create a new ASReview project for literature screening.
    Expected JSON: {
        "project_name": "My Review Project",
        "description": "Optional description",
        "model_type": "nb"  # Optional: nb (Naive Bayes), svm, rf
    }
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    payload = request.get_json()
    if payload is None:
        return jsonify({"error": "Invalid JSON or missing Content-Type: application/json header"}), 400
    
    project_name = payload.get('project_name', '').strip()
    if not project_name:
        return jsonify({"error": "project_name is required"}), 400
    
    description = payload.get('description', '').strip()
    model_type = payload.get('model_type', 'nb').strip()
    
    # Validate model type
    valid_models = ['nb', 'svm', 'rf', 'logistic']
    if model_type not in valid_models:
        return jsonify({"error": f"Invalid model_type. Must be one of: {', '.join(valid_models)}"}), 400
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.create_project(
            project_name=project_name,
            description=description,
            model_type=model_type
        )
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "project_id": result.get('project_id'),
                "project_name": result.get('project_name'),
                "message": "ASReview project created successfully"
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to create project')
            }), 500
    
    except Exception as e:
        logger.error(f"Error creating literature review project: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/literature-review/projects/<project_id>/upload")
def upload_papers_to_review(project_id):
    """
    Upload papers to an ASReview project for screening.
    Expected JSON: {
        "papers": [
            {
                "title": "Paper Title",
                "abstract": "Abstract text",
                "authors": ["Author 1", "Author 2"],
                "doi": "10.1234/example",
                "year": 2024
            },
            ...
        ]
    }
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    
    papers = payload.get('papers', [])
    if not papers:
        return jsonify({"error": "papers list is required"}), 400
    
    if not isinstance(papers, list):
        return jsonify({"error": "papers must be a list"}), 400
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.upload_papers(project_id=project_id, papers=papers)
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "uploaded_count": result.get('uploaded_count'),
                "message": result.get('message', 'Papers uploaded successfully')
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to upload papers')
            }), 500
    
    except Exception as e:
        logger.error(f"Error uploading papers to literature review: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/literature-review/projects/<project_id>/start")
def start_literature_review(project_id):
    """
    Start the active learning review process.
    Expected JSON: {
        "prior_relevant": ["doi1", "doi2"],  # Optional: papers known to be relevant
        "prior_irrelevant": ["doi3", "doi4"]  # Optional: papers known to be irrelevant
    }
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        payload = request.get_json(force=True, silent=True) or {}
    except Exception:
        payload = {}
    
    prior_relevant = payload.get('prior_relevant', [])
    prior_irrelevant = payload.get('prior_irrelevant', [])
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.start_review(
            project_id=project_id,
            prior_relevant=prior_relevant,
            prior_irrelevant=prior_irrelevant
        )
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "message": result.get('message', 'Review started successfully')
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to start review')
            }), 500
    
    except Exception as e:
        logger.error(f"Error starting literature review: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/literature-review/projects/<project_id>/next")
def get_next_paper_to_review(project_id):
    """
    Get the next paper to review based on active learning predictions.
    Returns the paper with the highest predicted relevance.
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.get_next_paper(project_id=project_id)
        
        if result.get('success'):
            paper = result.get('paper')
            if paper is None:
                return jsonify({
                    "ok": True,
                    "paper": None,
                    "message": result.get('message', 'Review complete - no more papers to screen')
                })
            else:
                return jsonify({
                    "ok": True,
                    "paper": paper,
                    "relevance_score": result.get('relevance_score'),
                    "progress": result.get('progress')
                })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to get next paper')
            }), 500
    
    except Exception as e:
        logger.error(f"Error getting next paper for literature review: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/api/literature-review/projects/<project_id>/record")
def record_review_decision(project_id):
    """
    Record a screening decision for a paper.
    Expected JSON: {
        "paper_id": "10.1234/example",
        "relevant": true,
        "note": "Optional note about decision"
    }
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    
    paper_id = payload.get('paper_id', '').strip()
    if not paper_id:
        return jsonify({"error": "paper_id is required"}), 400
    
    relevant = payload.get('relevant')
    if relevant is None:
        return jsonify({"error": "relevant field is required (true/false)"}), 400
    
    note = payload.get('note', '').strip()
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.record_decision(
            project_id=project_id,
            paper_id=paper_id,
            relevant=bool(relevant),
            note=note
        )
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "message": result.get('message', 'Decision recorded'),
                "model_updated": result.get('model_updated', True)
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to record decision')
            }), 500
    
    except Exception as e:
        logger.error(f"Error recording literature review decision: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/literature-review/projects/<project_id>/progress")
def get_review_progress(project_id):
    """
    Get review progress statistics.
    Returns total papers, reviewed count, relevant/irrelevant counts, etc.
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.get_progress(project_id=project_id)
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "total_papers": result.get('total_papers', 0),
                "reviewed_papers": result.get('reviewed_papers', 0),
                "relevant_papers": result.get('relevant_papers', 0),
                "irrelevant_papers": result.get('irrelevant_papers', 0),
                "progress_percent": result.get('progress_percent', 0),
                "estimated_remaining": result.get('estimated_remaining', 0)
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to get progress')
            }), 500
    
    except Exception as e:
        logger.error(f"Error getting literature review progress: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/literature-review/projects/<project_id>/export")
def export_review_results(project_id):
    """
    Export review results (relevant papers).
    Returns list of papers marked as relevant during screening.
    """
    # Check authentication
    if not check_admin_status(DB_PATH, request):
        return jsonify({"error": "Unauthorized. Admin authentication required."}), 401
    
    try:
        from asreview_client import get_asreview_client
        
        client = get_asreview_client()
        result = client.export_results(project_id=project_id)
        
        if result.get('success'):
            return jsonify({
                "ok": True,
                "relevant_papers": result.get('relevant_papers', []),
                "irrelevant_papers": result.get('irrelevant_papers', []),
                "export_format": result.get('export_format', 'json')
            })
        else:
            return jsonify({
                "ok": False,
                "error": result.get('error', 'Failed to export results')
            }), 500
    
    except Exception as e:
        logger.error(f"Error exporting literature review results: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    # Cleanup old progress entries on startup (older than 1 hour)
    print("[PDF Download] Cleaning up old progress entries...")
    deleted = cleanup_old_pdf_download_progress(DB_PATH, max_age_seconds=3600)
    if deleted > 0:
        print(f"[PDF Download] Cleaned up {deleted} old progress entries")
    
    # Start background cleanup task for email verification if enabled
    try:
        from config import ENABLE_OTP_VALIDATION
        if ENABLE_OTP_VALIDATION:
            from email_verification_store import cleanup_expired_records
            
            def cleanup_verification_task():
                """Background task to cleanup expired verification records."""
                while True:
                    time.sleep(3600)  # Run every hour
                    try:
                        deleted = cleanup_expired_records(DB_PATH)
                        if any(deleted.values()):
                            logger.info(f"[Email Verification] Cleaned up {deleted['verifications']} codes, "
                                      f"{deleted['sessions']} sessions, {deleted['rate_limits']} rate limits")
                    except Exception as e:
                        logger.error(f"[Email Verification] Cleanup task error: {e}")
            
            # Start cleanup thread
            cleanup_thread = threading.Thread(
                target=cleanup_verification_task,
                daemon=True,
                name="EmailVerificationCleanup"
            )
            cleanup_thread.start()
            logger.info("[Email Verification] Background cleanup task started")
    except ImportError:
        pass  # Feature not enabled or modules not available
    
    # Never run with debug=True in production - it allows arbitrary code execution
    app.run(host=HOST, port=PORT, debug=False)
