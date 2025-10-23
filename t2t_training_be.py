#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import requests
import tempfile
from typing import Dict, Any, List
from io import BytesIO

from flask import Flask, request, jsonify, send_file
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
)

# -----------------------------
# Config
# -----------------------------
DB_PATH = os.environ.get("T2T_DB", "t2t.db")
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

@app.get("/api/fetch-pdf/<doi_param>")
def fetch_pdf(doi_param: str):
    """
    Fetch PDF from unpaywall.org or sci-hub based on DOI.
    """
    try:
        doi = doi_param.replace("_SLASH_", "/")

        pdf_url = None

        try:
            unpaywall_url = f"https://api.unpaywall.org/v2/{doi}?email=support@example.com"
            resp = requests.get(unpaywall_url, timeout=10)
            if resp.ok:
                data = resp.json()
                if data.get("best_oa_location") and data["best_oa_location"].get("url_for_pdf"):
                    pdf_url = data["best_oa_location"]["url_for_pdf"]
        except Exception as e:
            print(f"Unpaywall lookup failed: {e}")

        if not pdf_url:
            try:
                crossref_url = f"https://api.crossref.org/works/{doi}"
                resp = requests.get(crossref_url, timeout=10)
                if resp.ok:
                    data = resp.json()
                    links = data.get("message", {}).get("link", [])
                    for link in links:
                        if link.get("content-type") == "application/pdf":
                            pdf_url = link.get("URL")
                            break
            except Exception as e:
                print(f"Crossref lookup failed: {e}")

        if not pdf_url:
            return jsonify({"error": "PDF not available for this DOI"}), 404

        print(f"Fetching PDF from: {pdf_url}")
        pdf_resp = requests.get(pdf_url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        if pdf_resp.status_code == 200 and pdf_resp.headers.get("content-type", "").startswith("application/pdf"):
            return send_file(
                BytesIO(pdf_resp.content),
                mimetype="application/pdf",
                as_attachment=False,
                download_name=f"{doi.replace('/', '_')}.pdf"
            )
        else:
            return jsonify({"error": "Failed to download PDF"}), 500

    except Exception as e:
        print(f"PDF fetch error: {e}")
        return jsonify({"error": str(e)}), 500

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
    article_title = (payload.get("article_title") or "").strip() or None
    article_authors = (payload.get("article_authors") or "").strip() or None
    article_year = (payload.get("article_year") or "").strip() or None
    sentence_id = payload.get("sentence_id")
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
            doi_hash = upsert_doi_metadata(DB_PATH, doi, article_title, article_authors, article_year)
        except Exception as e:
            return jsonify({"error": f"Failed to save DOI metadata: {e}"}), 500

    # Upsert the sentence, then insert tuples
    try:
        sid = upsert_sentence(DB_PATH, sentence_id, sentence, literature_link, contributor_email, doi_hash)
        insert_tuple_rows(DB_PATH, sid, tuples, contributor_email)
        return jsonify({"ok": True, "sentence_id": sid, "doi_hash": doi_hash})
    except Exception as e:
        return jsonify({"error": f"Save failed: {e}"}), 500

@app.delete("/api/tuple/<int:tuple_id>")
def delete_tuple(tuple_id: int):
    """
    Delete a tuple. Only the original contributor or admin can delete.
    Expected JSON: { "email": "user@example.com", "is_admin": false }
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    requester_email = (payload.get("email") or "").strip()

    if not requester_email:
        return jsonify({"error": "Missing 'email'"}), 400

    is_admin = is_admin_user(requester_email)

    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT contributor_email FROM tuples WHERE id = ?;", (tuple_id,))
        result = cur.fetchone()

        if not result:
            conn.close()
            return jsonify({"error": "Tuple not found"}), 404

        tuple_owner = result[0]

        if not is_admin and tuple_owner != requester_email:
            conn.close()
            return jsonify({"error": "Permission denied. Only the creator or admin can delete this tuple."}), 403

        cur.execute("DELETE FROM tuples WHERE id = ?;", (tuple_id,))
        conn.close()

        return jsonify({"ok": True, "message": "Tuple deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Delete failed: {e}"}), 500

@app.get("/api/rows")
@app.get("/api/recent")
def rows():
    """
    List recent rows with DOI metadata joined.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.text, s.literature_link, s.doi_hash,
                   dm.doi, dm.article_title, dm.article_authors, dm.article_year,
                   s.contributor_email, t.id, t.source_entity_name,
                   t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr,
                   t.contributor_email as tuple_contributor
            FROM sentences s
            LEFT JOIN doi_metadata dm ON s.doi_hash = dm.doi_hash
            LEFT JOIN tuples t ON s.id = t.sentence_id
            ORDER BY s.id DESC, t.id ASC
            LIMIT 200;
        """)
        data = cur.fetchall()
        conn.close()
        cols = ["sentence_id", "sentence", "literature_link", "doi_hash",
                "doi", "article_title", "article_authors", "article_year",
                "contributor_email", "tuple_id",
                "source_entity_name", "source_entity_attr", "relation_type",
                "sink_entity_name", "sink_entity_attr", "tuple_contributor"]
        out = [dict(zip(cols, row)) for row in data]
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"rows failed: {e}"}), 500

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
