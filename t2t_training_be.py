#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import requests
import logging
from typing import Dict, Any, List
import threading
import time
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

from t2t_store import (
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
)

# Import configuration
try:
    from config import (
        DB_PATH, BE_PORT as PORT, HOST, ENABLE_PDF_HIGHLIGHTING,
        DEPLOYMENT_MODE, BACKEND_PUBLIC_URL, ENABLE_ENHANCED_PDF_DOWNLOAD
    )
except ImportError:
    # Fallback to environment variables if config.py doesn't exist
    DB_PATH = os.environ.get("T2T_DB", "t2t_training.db")
    PORT = int(os.environ.get("T2T_PORT", "5001"))
    HOST = os.environ.get("T2T_HOST", "0.0.0.0")
    ENABLE_PDF_HIGHLIGHTING = True  # Default to enabled
    DEPLOYMENT_MODE = os.environ.get("T2T_DEPLOYMENT_MODE", "internal")
    BACKEND_PUBLIC_URL = os.environ.get("T2T_BACKEND_PUBLIC_URL", "")
    ENABLE_ENHANCED_PDF_DOWNLOAD = False  # Default to standard PDF download

# Override config with environment variables if present
DEPLOYMENT_MODE = os.environ.get("T2T_DEPLOYMENT_MODE", DEPLOYMENT_MODE)
BACKEND_PUBLIC_URL = os.environ.get("T2T_BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)

# Validate deployment mode
if DEPLOYMENT_MODE not in ["internal", "nginx"]:
    raise ValueError(f"Invalid DEPLOYMENT_MODE: {DEPLOYMENT_MODE}. Must be 'internal' or 'nginx'")

# Initialize DB on startup
init_db(DB_PATH)

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
        return jsonify({"error": f"choices failed: {e}"}), 500

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

    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

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
        return jsonify({"valid": False, "error": f"Failed to fetch DOI metadata: {str(e)}"}), 200

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
        return jsonify({"error": f"Failed to register new types: {e}"}), 500

    # Upsert DOI metadata if present and get doi_hash
    doi_hash = None
    if doi:
        try:
            doi_hash = upsert_doi_metadata(DB_PATH, doi)
        except Exception as e:
            return jsonify({"error": f"Failed to save DOI metadata: {e}"}), 500

    # Upsert the sentence, then insert triples
    try:
        sid = upsert_sentence(DB_PATH, sentence_id, sentence, literature_link, doi_hash)
        insert_triple_rows(DB_PATH, sid, triples, contributor_email, project_id)
        return jsonify({"ok": True, "sentence_id": sid, "doi_hash": doi_hash})
    except Exception as e:
        return jsonify({"error": f"Save failed: {e}"}), 500

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

    from t2t_store import get_conn
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
        return jsonify({"error": f"Delete failed: {e}"}), 500

@app.get("/api/rows")
@app.get("/api/recent")
def rows():
    """
    List recent rows with DOI information.
    Note: Article metadata (title, authors, year) are not stored and would need to be fetched on-demand from CrossRef.
    Supports filtering by project_id via query parameter: /api/rows?project_id=1
    """
    from t2t_store import get_conn
    try:
        project_id = request.args.get('project_id', type=int)
        
        conn = get_conn(DB_PATH)
        cur = conn.cursor()
        
        if project_id:
            cur.execute("""
                SELECT s.id, s.text, s.literature_link, s.doi_hash,
                       dm.doi, t.id, t.source_entity_name,
                       t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                       t.contributor_email as triple_contributor, t.project_id
                FROM sentences s
                LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
                LEFT JOIN triples t ON s.id = t.sentence_id
                WHERE t.project_id = ?
                ORDER BY s.id DESC, t.id ASC
                LIMIT 200;
            """, (project_id,))
        else:
            cur.execute("""
                SELECT s.id, s.text, s.literature_link, s.doi_hash,
                       dm.doi, t.id, t.source_entity_name,
                       t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                       t.contributor_email as triple_contributor, t.project_id
                FROM sentences s
                LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
                LEFT JOIN triples t ON s.id = t.sentence_id
                ORDER BY s.id DESC, t.id ASC
                LIMIT 200;
            """)
        
        data = cur.fetchall()
        conn.close()
        cols = ["sentence_id", "sentence", "literature_link", "doi_hash",
                "doi", "triple_id",
                "source_entity_name", "source_entity_attr", "relation_type",
                "sink_entity_name", "sink_entity_attr", "triple_contributor", "project_id"]
        out = [dict(zip(cols, row)) for row in data]
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"rows failed: {e}"}), 500

# -----------------------------
# Admin endpoints
# -----------------------------
@app.post("/api/admin/auth")
def admin_auth():
    """
    Authenticate admin user.
    Expected JSON: { "email": "admin@example.com", "password": "secret" }
    Returns: { "authenticated": true/false, "is_admin": true/false }
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

    return jsonify({
        "authenticated": authenticated or is_env_admin,
        "is_admin": authenticated or is_env_admin
    })

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
    Expected JSON: { "email": "admin@example.com", "password": "secret",
                     "name": "Project Name", "description": "...", "doi_list": ["10.1234/...", ...] }
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

    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    doi_list = payload.get("doi_list") or []

    if not name:
        return jsonify({"error": "Project name is required"}), 400
    if not doi_list or not isinstance(doi_list, list):
        return jsonify({"error": "DOI list is required and must be an array"}), 400

    project_id = create_project(DB_PATH, name, description, doi_list, email)
    
    if project_id > 0:
        return jsonify({"ok": True, "project_id": project_id, "message": "Project created successfully"})
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
    Expected JSON: { "email": "admin@example.com", "password": "secret",
                     "name": "...", "description": "...", "doi_list": [...] }
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

    name = payload.get("name")
    description = payload.get("description")
    doi_list = payload.get("doi_list")

    success = update_project(DB_PATH, project_id, name, description, doi_list)
    
    if success:
        return jsonify({"ok": True, "message": "Project updated successfully"})
    else:
        return jsonify({"error": "Failed to update project or project not found"}), 404

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
        from t2t_store import get_conn
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
            message = f"Project deleted successfully. {triple_count} triple(s) "
            if handle_triples == "delete":
                message += f"and {orphaned_count} orphaned sentence(s) were also deleted."
            elif handle_triples == "reassign":
                message += f"were reassigned to project {target_project_id}."
            else:
                message += "were set to uncategorized."
            return jsonify({"ok": True, "message": message, "triples_affected": triple_count})
        else:
            return jsonify({"error": "Failed to delete project"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to delete project: {str(e)}"}), 500

# PDF Management Endpoints
def _run_pdf_download_task(project_id: int, doi_list: List[str], project_dir: str):
    """Background task to download PDFs and update progress in database"""
    import json
    
    # Use enhanced or standard PDF manager based on config
    if ENABLE_ENHANCED_PDF_DOWNLOAD:
        try:
            from pdf_manager_enhanced import process_dois_smart as process_function
            from pdf_manager import get_project_pdf_dir, generate_doi_hash
            print(f"[PDF Download Task] Using ENHANCED PDF download system")
        except ImportError as e:
            print(f"[PDF Download Task] Warning: Enhanced PDF manager not available, falling back to standard: {e}")
            from pdf_manager import process_project_dois_with_progress as process_function
            from pdf_manager import get_project_pdf_dir, generate_doi_hash
    else:
        from pdf_manager import process_project_dois_with_progress as process_function
        from pdf_manager import get_project_pdf_dir, generate_doi_hash
        print(f"[PDF Download Task] Using STANDARD PDF download system")
    
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
        
        # Initialize the database if using enhanced mode
        if ENABLE_ENHANCED_PDF_DOWNLOAD:
            try:
                from pdf_download_db import init_pdf_download_db
                init_pdf_download_db()
                # Enhanced version needs project_id parameter
                results = process_function(doi_list, project_id, project_dir, progress_callback)
            except Exception as e:
                print(f"[PDF Download Task] Warning: Could not initialize enhanced PDF download database: {e}")
                # Fallback to standard if enhanced fails
                from pdf_manager import process_project_dois_with_progress
                results = process_project_dois_with_progress(doi_list, project_dir, progress_callback)
        else:
            # Standard version doesn't need project_id
            results = process_function(doi_list, project_dir, progress_callback)
        
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
    Expected JSON: { "email": "admin@example.com", "password": "secret" }
    Returns: Immediate response, use /download-pdfs/status to check progress
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception as e:
        print(f"[PDF Download] Invalid JSON: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""

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
        print(f"[PDF Download] Download already in progress for project {project_id}")
        return jsonify({"error": "Download already in progress for this project"}), 409
    
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
    """
    print(f"[PDF Download Status] Checking status for project {project_id}")
    
    progress = get_pdf_download_progress(DB_PATH, project_id)
    
    if not progress:
        return jsonify({"status": "not_started"}), 404
    
    print(f"[PDF Download Status] Project {project_id}: status={progress.get('status')}, "
          f"current={progress.get('current')}/{progress.get('total')}")
    
    # Return current progress
    return jsonify({
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
        # Include full results when completed
        "full_results": {
            "downloaded": progress.get("downloaded", []),
            "needs_upload": progress.get("needs_upload", []),
            "errors": progress.get("errors", [])
        } if progress.get("status") == "completed" else None
    })

@app.get("/api/pdf-download-config")
def get_pdf_download_config():
    """Get PDF download configuration and available sources (public endpoint)"""
    try:
        from pdf_manager import (
            UNPAYWALL_EMAIL,
            UNPYWALL_AVAILABLE,
            METAPUB_AVAILABLE,
            HABANERO_AVAILABLE,
            ENABLE_METAPUB_FALLBACK,
            ENABLE_HABANERO_DOWNLOAD
        )
        
        sources = []
        
        # Unpaywall (REST API) - always attempted first
        sources.append({
            "name": "Unpaywall (REST API)",
            "enabled": True,
            "available": True,
            "order": 1,
            "description": "Open access repository via REST API"
        })
        
        # Unpywall library - optional enhancement to Unpaywall
        if UNPYWALL_AVAILABLE:
            sources.append({
                "name": "Unpywall Library",
                "enabled": True,
                "available": True,
                "order": 2,
                "description": "Python library for enhanced Unpaywall access"
            })
        
        # Metapub - PubMed Central, arXiv, etc.
        sources.append({
            "name": "Metapub",
            "enabled": ENABLE_METAPUB_FALLBACK,
            "available": METAPUB_AVAILABLE,
            "order": 3,
            "description": "PubMed Central, arXiv, and other sources"
        })
        
        # Habanero - Crossref with optional institutional access
        sources.append({
            "name": "Habanero",
            "enabled": ENABLE_HABANERO_DOWNLOAD,
            "available": HABANERO_AVAILABLE,
            "order": 4,
            "description": "Crossref API with institutional access"
        })
        
        # Count enabled sources
        enabled_count = sum(1 for s in sources if s["enabled"] and s["available"])
        
        return jsonify({
            "ok": True,
            "sources": sources,
            "enabled_count": enabled_count,
            "email_configured": UNPAYWALL_EMAIL and UNPAYWALL_EMAIL != "research@example.com"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get configuration: {str(e)}"}), 500

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
        return jsonify({"error": f"Failed to list PDFs: {str(e)}"}), 500

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
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

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
        return jsonify({"error": f"Failed to serve PDF: {str(e)}"}), 500

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

if __name__ == "__main__":
    # Cleanup old progress entries on startup (older than 1 hour)
    print("[PDF Download] Cleaning up old progress entries...")
    deleted = cleanup_old_pdf_download_progress(DB_PATH, max_age_seconds=3600)
    if deleted > 0:
        print(f"[PDF Download] Cleaned up {deleted} old progress entries")
    
    app.run(host=HOST, port=PORT, debug=True)
