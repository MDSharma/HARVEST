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
    insert_tuple_rows,
    add_relation_type,
    add_entity_type,
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
    sentence_id = payload.get("sentence_id")  # may be None
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

    # Upsert the sentence, then insert tuples
    try:
        sid = upsert_sentence(DB_PATH, sentence_id, sentence, literature_link, contributor_email,
                             doi, article_title, article_authors, article_year)
        insert_tuple_rows(DB_PATH, sid, tuples)
        return jsonify({"ok": True, "sentence_id": sid})
    except Exception as e:
        return jsonify({"error": f"Save failed: {e}"}), 500

@app.get("/api/rows")
def rows():
    """
    Optional helper endpoint to list recent rows for debugging.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.text, s.literature_link, s.doi, s.article_title, s.article_authors,
                   s.article_year, s.contributor_email, t.id, t.source_entity_name,
                   t.source_entity_attr, t.relation_type, t.sink_entity_name, t.sink_entity_attr
            FROM sentences s
            LEFT JOIN tuples t ON s.id = t.sentence_id
            ORDER BY s.id DESC, t.id ASC
            LIMIT 200;
        """)
        data = cur.fetchall()
        conn.close()
        cols = ["sentence_id", "sentence", "literature_link", "doi", "article_title",
                "article_authors", "article_year", "contributor_email", "tuple_id",
                "source_entity_name", "source_entity_attr", "relation_type",
                "sink_entity_name", "sink_entity_attr"]
        out = [dict(zip(cols, row)) for row in data]
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"rows failed: {e}"}), 500

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
