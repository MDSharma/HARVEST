#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests
from typing import Dict, Any, List

from flask import Flask, request, jsonify
from flask_cors import CORS

from t2t_store import (
    init_db,
    fetch_entity_dropdown_options,
    fetch_relation_dropdown_options,
    upsert_sentence,
    upsert_doi_metadata,
    insert_tuple_rows,
    add_relation_type,
    add_entity_type,
    generate_doi_hash,
    decode_doi_hash,
    is_admin_user,
    verify_admin_password,
    create_admin_user,
    create_project,
    get_all_projects,
    get_project_by_id,
    update_project,
    delete_project,
    update_tuple,
    check_admin_status,
)

# Import configuration
try:
    from config import DB_PATH, BE_PORT as PORT, HOST
except ImportError:
    # Fallback to environment variables if config.py doesn't exist
    DB_PATH = os.environ.get("T2T_DB", "t2t_training.db")
    PORT = int(os.environ.get("T2T_PORT", "5001"))
    HOST = os.environ.get("T2T_HOST", "0.0.0.0")

# Initialize DB on startup
init_db(DB_PATH)

app = Flask(__name__)
CORS(app)  # allow cross-origin requests from your Dash UI

def slugify(s: str) -> str:
    """Simple slug for entity type 'value' column (lowercase, underscores)."""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "db": DB_PATH})

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
      "tuples": [
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
    tuples: List[Dict[str, Any]] = payload.get("tuples") or []

    if not sentence:
        return jsonify({"error": "Missing 'sentence'"}), 400
    if not contributor_email:
        return jsonify({"error": "Missing 'contributor_email'"}), 400
    if not tuples:
        return jsonify({"error": "Missing 'tuples' array"}), 400

    # Handle any "other" entries (add new entity or relation types)
    try:
        for t in tuples:
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

    # Upsert the sentence, then insert tuples
    try:
        sid = upsert_sentence(DB_PATH, sentence_id, sentence, literature_link, doi_hash)
        insert_tuple_rows(DB_PATH, sid, tuples, contributor_email, project_id)
        return jsonify({"ok": True, "sentence_id": sid, "doi_hash": doi_hash})
    except Exception as e:
        return jsonify({"error": f"Save failed: {e}"}), 500

@app.delete("/api/tuple/<int:tuple_id>")
def delete_tuple(tuple_id: int):
    """
    Delete a tuple. Only the original contributor or admin can delete.
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

        # Get tuple info before deletion
        cur.execute("SELECT contributor_email, sentence_id FROM tuples WHERE id = ?;", (tuple_id,))
        result = cur.fetchone()

        if not result:
            conn.close()
            return jsonify({"error": "Tuple not found"}), 404

        tuple_owner, sentence_id = result[0], result[1]

        if not is_admin and tuple_owner != requester_email:
            conn.close()
            return jsonify({"error": "Permission denied. Only the creator or admin can delete this tuple."}), 403

        # Delete the tuple
        cur.execute("DELETE FROM tuples WHERE id = ?;", (tuple_id,))
        
        # Check if sentence has any remaining tuples
        cur.execute("SELECT COUNT(*) FROM tuples WHERE sentence_id = ?;", (sentence_id,))
        remaining_tuples = cur.fetchone()[0]
        
        # If no tuples remain, delete the orphaned sentence
        if remaining_tuples == 0:
            cur.execute("DELETE FROM sentences WHERE id = ?;", (sentence_id,))
            conn.commit()
            conn.close()
            return jsonify({"ok": True, "message": "Tuple and associated sentence deleted (no other tuples remained)"})
        
        conn.commit()
        conn.close()

        return jsonify({"ok": True, "message": "Tuple deleted successfully"})
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
                       t.contributor_email as tuple_contributor, t.project_id
                FROM sentences s
                LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
                LEFT JOIN tuples t ON s.id = t.sentence_id
                WHERE t.project_id = ?
                ORDER BY s.id DESC, t.id ASC
                LIMIT 200;
            """, (project_id,))
        else:
            cur.execute("""
                SELECT s.id, s.text, s.literature_link, s.doi_hash,
                       dm.doi, t.id, t.source_entity_name,
                       t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                       t.contributor_email as tuple_contributor, t.project_id
                FROM sentences s
                LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
                LEFT JOIN tuples t ON s.id = t.sentence_id
                ORDER BY s.id DESC, t.id ASC
                LIMIT 200;
            """)
        
        data = cur.fetchall()
        conn.close()
        cols = ["sentence_id", "sentence", "literature_link", "doi_hash",
                "doi", "tuple_id",
                "source_entity_name", "source_entity_attr", "relation_type",
                "sink_entity_name", "sink_entity_attr", "tuple_contributor", "project_id"]
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

@app.put("/api/admin/tuple/<int:tuple_id>")
def admin_update_tuple(tuple_id: int):
    """
    Update a tuple (admin only).
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

    success = update_tuple(DB_PATH, tuple_id, source_entity_name, source_entity_attr,
                          relation_type, sink_entity_name, sink_entity_attr)
    
    if success:
        return jsonify({"ok": True, "message": "Tuple updated successfully"})
    else:
        return jsonify({"error": "Failed to update tuple or tuple not found"}), 404

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
        "handle_tuples": "delete" | "reassign" | "keep"  (optional, default: "keep")
        "target_project_id": <id>  (required if handle_tuples is "reassign")
    }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    handle_tuples = payload.get("handle_tuples", "keep")  # Default: keep tuples (set project_id to NULL)
    target_project_id = payload.get("target_project_id")

    if not email or not password:
        return jsonify({"error": "Admin authentication required"}), 401

    # Verify admin credentials
    if not (verify_admin_password(DB_PATH, email, password) or is_admin_user(email)):
        return jsonify({"error": "Invalid admin credentials"}), 403
    
    # Validate handle_tuples option
    if handle_tuples not in ["delete", "reassign", "keep"]:
        return jsonify({"error": "Invalid handle_tuples option. Must be 'delete', 'reassign', or 'keep'"}), 400
    
    if handle_tuples == "reassign" and not target_project_id:
        return jsonify({"error": "target_project_id required when handle_tuples is 'reassign'"}), 400

    try:
        from t2t_store import get_conn
        conn = get_conn(DB_PATH)
        cur = conn.cursor()
        
        # Check how many tuples are associated with this project
        cur.execute("SELECT COUNT(*) FROM tuples WHERE project_id = ?;", (project_id,))
        tuple_count = cur.fetchone()[0]
        
        orphaned_count = 0
        # Handle tuples based on option
        if handle_tuples == "delete":
            # Get all sentence_ids for tuples we're about to delete
            cur.execute("SELECT DISTINCT sentence_id FROM tuples WHERE project_id = ?;", (project_id,))
            sentence_ids = [row[0] for row in cur.fetchall()]
            
            # Delete all tuples associated with this project
            cur.execute("DELETE FROM tuples WHERE project_id = ?;", (project_id,))
            
            # Now check for orphaned sentences and delete them
            for sentence_id in sentence_ids:
                cur.execute("SELECT COUNT(*) FROM tuples WHERE sentence_id = ?;", (sentence_id,))
                remaining_tuples = cur.fetchone()[0]
                if remaining_tuples == 0:
                    # This sentence has no more tuples, delete it
                    cur.execute("DELETE FROM sentences WHERE id = ?;", (sentence_id,))
                    orphaned_count += 1
            
            conn.commit()
        elif handle_tuples == "reassign":
            # Reassign tuples to target project
            cur.execute("UPDATE tuples SET project_id = ? WHERE project_id = ?;", (target_project_id, project_id))
            conn.commit()
        elif handle_tuples == "keep":
            # Set project_id to NULL (uncategorized)
            cur.execute("UPDATE tuples SET project_id = NULL WHERE project_id = ?;", (project_id,))
            conn.commit()
        
        # Now delete the project
        success = delete_project(DB_PATH, project_id)
        
        conn.close()
        
        if success:
            message = f"Project deleted successfully. {tuple_count} tuple(s) "
            if handle_tuples == "delete":
                message += f"and {orphaned_count} orphaned sentence(s) were also deleted."
            elif handle_tuples == "reassign":
                message += f"were reassigned to project {target_project_id}."
            else:
                message += "were set to uncategorized."
            return jsonify({"ok": True, "message": message, "tuples_affected": tuple_count})
        else:
            return jsonify({"error": "Failed to delete project"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to delete project: {str(e)}"}), 500

# PDF Management Endpoints
@app.post("/api/admin/projects/<int:project_id>/download-pdfs")
def download_project_pdfs(project_id: int):
    """
    Download PDFs for all DOIs in a project (admin only).
    Expected JSON: { "email": "admin@example.com", "password": "secret" }
    Returns: Status of downloads and list of DOIs requiring manual upload
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
    
    # Get project
    project = get_project_by_id(DB_PATH, project_id)
    if not project:
        print(f"[PDF Download] Project {project_id} not found")
        return jsonify({"error": "Project not found"}), 404
    
    try:
        import json
        from pdf_manager import process_project_dois, get_project_pdf_dir
        
        doi_list = json.loads(project["doi_list"]) if isinstance(project["doi_list"], str) else project["doi_list"]
        project_dir = get_project_pdf_dir(project_id)
        
        print(f"[PDF Download] Starting download for project {project_id} with {len(doi_list)} DOIs")
        print(f"[PDF Download] Target directory: {project_dir}")
        
        results = process_project_dois(doi_list, project_dir)
        
        print(f"[PDF Download] Completed - Downloaded: {len(results['downloaded'])}, Needs upload: {len(results['needs_upload'])}, Errors: {len(results['errors'])}")
        
        return jsonify({
            "ok": True,
            "project_dir": project_dir,
            "downloaded": results["downloaded"],
            "needs_upload": results["needs_upload"],
            "errors": results["errors"],
            "summary": {
                "total_dois": len(doi_list),
                "downloaded": len(results["downloaded"]),
                "needs_upload": len(results["needs_upload"]),
                "errors": len(results["errors"])
            }
        })
    except Exception as e:
        import traceback
        print(f"[PDF Download] Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Download failed: {str(e)}"}), 500

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

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
