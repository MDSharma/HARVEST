#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Admin backend endpoints for project management, PDF fetching, and tuple editing.
"""

import os
import json
import requests
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client, Client

from t2t_store import is_admin_user, decode_doi_hash

# -----------------------------
# Config
# -----------------------------
DB_PATH = os.environ.get("T2T_DB", "t2t.db")
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("VITE_SUPABASE_SUPABASE_ANON_KEY")
PDF_STORAGE_PATH = os.environ.get("T2T_PDF_STORAGE", "pdfs")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Ensure PDF storage directory exists
Path(PDF_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

# CORS configuration
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": False
    }
})

# -----------------------------
# Helper Functions
# -----------------------------

def fetch_doi_metadata_from_api(doi: str) -> Dict[str, str]:
    """Fetch article metadata from CrossRef API."""
    try:
        crossref_url = f"https://api.crossref.org/works/{doi}"
        resp = requests.get(crossref_url, timeout=10)
        if resp.ok:
            data = resp.json()
            message = data.get("message", {})

            # Extract title
            title_list = message.get("title", [])
            title = title_list[0] if title_list else "N/A"

            # Extract authors
            authors_list = message.get("author", [])
            if authors_list:
                author_names = []
                for author in authors_list[:5]:
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if family:
                        author_names.append(f"{given} {family}".strip())
                authors = ", ".join(author_names)
                if len(authors_list) > 5:
                    authors += " et al."
            else:
                authors = "N/A"

            # Extract year
            published = message.get("published", {}) or message.get("published-print", {}) or message.get("published-online", {})
            date_parts = published.get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else "N/A"

            return {
                "title": title,
                "authors": authors,
                "year": year
            }
    except Exception as e:
        print(f"Error fetching metadata for {doi}: {e}")

    return {"title": "N/A", "authors": "N/A", "year": "N/A"}

def fetch_pdf_from_doi2pdf(doi: str) -> Optional[bytes]:
    """Attempt to fetch PDF using doi2pdf service."""
    try:
        doi2pdf_url = f"https://doi2pdf.com/api/v1/pdf/{doi}"
        resp = requests.get(doi2pdf_url, timeout=30)
        if resp.status_code == 200 and resp.headers.get('content-type') == 'application/pdf':
            return resp.content
    except Exception as e:
        print(f"doi2pdf fetch failed for {doi}: {e}")
    return None

def fetch_pdf_from_unpaywall(doi: str) -> Optional[bytes]:
    """Attempt to fetch PDF using Unpaywall API."""
    try:
        email = "support@example.com"  # Required by Unpaywall API
        unpaywall_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        resp = requests.get(unpaywall_url, timeout=10)

        if resp.ok:
            data = resp.json()
            best_oa_location = data.get("best_oa_location")

            if best_oa_location and best_oa_location.get("url_for_pdf"):
                pdf_url = best_oa_location["url_for_pdf"]
                pdf_resp = requests.get(pdf_url, timeout=30)

                if pdf_resp.status_code == 200:
                    return pdf_resp.content
    except Exception as e:
        print(f"Unpaywall fetch failed for {doi}: {e}")
    return None

def download_pdf_for_paper(doi: str, project_id: str, paper_id: str) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Download PDF for a paper using doi2pdf then unpaywall fallback.
    Returns: (success, pdf_path, error_message)
    """
    # Try doi2pdf first
    pdf_content = fetch_pdf_from_doi2pdf(doi)
    source = "doi2pdf"

    # Fallback to unpaywall
    if not pdf_content:
        pdf_content = fetch_pdf_from_unpaywall(doi)
        source = "unpaywall"

    if not pdf_content:
        return False, None, "PDF not available from doi2pdf or Unpaywall"

    # Save PDF to disk
    try:
        project_dir = Path(PDF_STORAGE_PATH) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        pdf_filename = f"{paper_id}.pdf"
        pdf_path = project_dir / pdf_filename

        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)

        relative_path = f"{project_id}/{pdf_filename}"
        print(f"Successfully downloaded PDF from {source} for {doi} -> {relative_path}")
        return True, relative_path, None
    except Exception as e:
        return False, None, f"Failed to save PDF: {str(e)}"

# -----------------------------
# Admin Check Decorator
# -----------------------------

def admin_required(f):
    """Decorator to require admin privileges."""
    def wrapper(*args, **kwargs):
        try:
            payload = request.get_json(force=True, silent=False)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

        email = (payload.get("email") or "").strip()
        if not email:
            return jsonify({"error": "Missing 'email' field"}), 400

        if not is_admin_user(email):
            return jsonify({"error": "Admin privileges required"}), 403

        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper

# -----------------------------
# Project Management Endpoints
# -----------------------------

@app.get("/api/admin/projects")
def list_projects():
    """List all projects."""
    try:
        response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": f"Failed to list projects: {e}"}), 500

@app.post("/api/admin/projects")
@admin_required
def create_project():
    """Create a new project. Requires admin."""
    payload = request.get_json()
    name = payload.get("name", "").strip()
    description = payload.get("description", "").strip()
    email = payload.get("email", "").strip()

    if not name:
        return jsonify({"error": "Project name is required"}), 400

    try:
        response = supabase.table("projects").insert({
            "name": name,
            "description": description,
            "created_by": email
        }).execute()

        return jsonify(response.data[0])
    except Exception as e:
        return jsonify({"error": f"Failed to create project: {e}"}), 500

@app.get("/api/admin/projects/<project_id>/papers")
def list_project_papers(project_id: str):
    """List all papers in a project."""
    try:
        response = supabase.table("project_papers") \
            .select("*") \
            .eq("project_id", project_id) \
            .order("created_at", desc=False) \
            .execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": f"Failed to list papers: {e}"}), 500

@app.post("/api/admin/projects/<project_id>/papers")
@admin_required
def add_papers_to_project(project_id: str):
    """
    Add DOIs to a project. Accepts a list of DOIs.
    Expected JSON: { "email": "...", "dois": ["10.1234/abc", "10.5678/def"] }
    """
    payload = request.get_json()
    dois = payload.get("dois", [])

    if not dois or not isinstance(dois, list):
        return jsonify({"error": "Must provide 'dois' as an array"}), 400

    added = []
    errors = []

    for doi in dois:
        doi = doi.strip()
        if not doi:
            continue

        try:
            # Fetch metadata
            metadata = fetch_doi_metadata_from_api(doi)

            # Insert paper
            response = supabase.table("project_papers").insert({
                "project_id": project_id,
                "doi": doi,
                "title": metadata["title"],
                "authors": metadata["authors"],
                "year": metadata["year"],
                "fetch_status": "pending"
            }).execute()

            added.append(response.data[0])
        except Exception as e:
            errors.append({"doi": doi, "error": str(e)})

    return jsonify({
        "added": added,
        "errors": errors
    })

@app.post("/api/admin/projects/<project_id>/fetch")
@admin_required
def fetch_project_pdfs(project_id: str):
    """
    Fetch PDFs for all pending papers in a project.
    Expected JSON: { "email": "..." }
    """
    try:
        # Get all pending papers
        response = supabase.table("project_papers") \
            .select("*") \
            .eq("project_id", project_id) \
            .eq("fetch_status", "pending") \
            .execute()

        papers = response.data
        results = []

        for paper in papers:
            paper_id = paper["id"]
            doi = paper["doi"]

            # Update status to fetching
            supabase.table("project_papers") \
                .update({"fetch_status": "fetching"}) \
                .eq("id", paper_id) \
                .execute()

            # Attempt download
            success, pdf_path, error_msg = download_pdf_for_paper(doi, project_id, paper_id)

            if success:
                supabase.table("project_papers") \
                    .update({
                        "fetch_status": "success",
                        "pdf_path": pdf_path,
                        "fetched_at": datetime.utcnow().isoformat(),
                        "error_message": None
                    }) \
                    .eq("id", paper_id) \
                    .execute()

                results.append({"paper_id": paper_id, "doi": doi, "status": "success"})
            else:
                supabase.table("project_papers") \
                    .update({
                        "fetch_status": "failed",
                        "error_message": error_msg
                    }) \
                    .eq("id", paper_id) \
                    .execute()

                results.append({"paper_id": paper_id, "doi": doi, "status": "failed", "error": error_msg})

        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch PDFs: {e}"}), 500

@app.get("/api/pdfs/<project_id>/<paper_id>")
def serve_pdf(project_id: str, paper_id: str):
    """Serve a PDF file."""
    try:
        # Extract paper_id without .pdf extension if present
        if paper_id.endswith('.pdf'):
            paper_id = paper_id[:-4]

        pdf_path = Path(PDF_STORAGE_PATH) / project_id / f"{paper_id}.pdf"

        if not pdf_path.exists():
            return jsonify({"error": "PDF not found"}), 404

        return send_file(str(pdf_path), mimetype='application/pdf')
    except Exception as e:
        return jsonify({"error": f"Failed to serve PDF: {e}"}), 500

# -----------------------------
# Tuple Admin Endpoints
# -----------------------------

@app.get("/api/admin/tuples")
def list_all_tuples():
    """List all tuples from all users with pagination."""
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            SELECT t.id, t.sentence_id, t.source_entity_name, t.source_entity_attr,
                   t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                   t.contributor_email, t.created_at,
                   s.text as sentence_text, s.literature_link, s.doi_hash
            FROM tuples t
            JOIN sentences s ON t.sentence_id = s.id
            ORDER BY t.created_at DESC
            LIMIT ? OFFSET ?;
        """, (limit, offset))

        rows = cur.fetchall()
        conn.close()

        tuples = []
        for row in rows:
            tuples.append({
                "id": row[0],
                "sentence_id": row[1],
                "source_entity_name": row[2],
                "source_entity_attr": row[3],
                "relation_type": row[4],
                "sink_entity_name": row[5],
                "sink_entity_attr": row[6],
                "contributor_email": row[7],
                "created_at": row[8],
                "sentence_text": row[9],
                "literature_link": row[10],
                "doi_hash": row[11]
            })

        return jsonify(tuples)
    except Exception as e:
        return jsonify({"error": f"Failed to list tuples: {e}"}), 500

@app.put("/api/admin/tuples/<int:tuple_id>")
@admin_required
def update_tuple(tuple_id: int):
    """
    Update a tuple. Only admins can update any tuple.
    Expected JSON: {
        "email": "...",
        "source_entity_name": "...",
        "source_entity_attr": "...",
        "relation_type": "...",
        "sink_entity_name": "...",
        "sink_entity_attr": "..."
    }
    """
    payload = request.get_json()

    required_fields = ["source_entity_name", "source_entity_attr", "relation_type",
                      "sink_entity_name", "sink_entity_attr"]

    for field in required_fields:
        if field not in payload:
            return jsonify({"error": f"Missing field: {field}"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Check if tuple exists
        cur.execute("SELECT id FROM tuples WHERE id = ?;", (tuple_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "Tuple not found"}), 404

        # Update tuple
        cur.execute("""
            UPDATE tuples
            SET source_entity_name = ?,
                source_entity_attr = ?,
                relation_type = ?,
                sink_entity_name = ?,
                sink_entity_attr = ?
            WHERE id = ?;
        """, (
            payload["source_entity_name"],
            payload["source_entity_attr"],
            payload["relation_type"],
            payload["sink_entity_name"],
            payload["sink_entity_attr"],
            tuple_id
        ))

        conn.commit()
        conn.close()

        return jsonify({"ok": True, "message": "Tuple updated successfully"})
    except Exception as e:
        return jsonify({"error": f"Update failed: {e}"}), 500

if __name__ == "__main__":
    PORT = int(os.environ.get("T2T_ADMIN_PORT", "5002"))
    HOST = os.environ.get("T2T_HOST", "0.0.0.0")
    app.run(host=HOST, port=PORT, debug=True)
