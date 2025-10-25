#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime
import json
import hashlib
import base64

# -----------------------------
# Seed schema from your JSON
# -----------------------------
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
        "Metabolite": "metabolite"
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
        "inhers_in": "inhers_in"
    }
}

def generate_doi_hash(doi: str) -> str:
    """Generate a reversible hash from a DOI using base64 encoding."""
    if not doi:
        return ""
    doi_bytes = doi.encode('utf-8')
    return base64.urlsafe_b64encode(doi_bytes).decode('utf-8').rstrip('=')

def decode_doi_hash(doi_hash: str) -> str:
    """Decode a DOI hash back to the original DOI."""
    if not doi_hash:
        return ""
    padding = 4 - (len(doi_hash) % 4)
    if padding != 4:
        doi_hash += '=' * padding
    try:
        doi_bytes = base64.urlsafe_b64decode(doi_hash.encode('utf-8'))
        return doi_bytes.decode('utf-8')
    except Exception:
        return ""

ADMIN_EMAILS = set(os.environ.get("T2T_ADMIN_EMAILS", "").split(","))

def is_admin_user(email: str) -> bool:
    """Check if an email is in the admin list."""
    return email.strip() in ADMIN_EMAILS

def check_admin_status(db_path: str, email: str, password: str = None) -> bool:
    """Check if user is admin (either in env or in database)."""
    # Check environment variable
    if is_admin_user(email):
        return True
    
    # Check database if password provided
    if password:
        return verify_admin_password(db_path, email, password)
    
    return False

def get_conn(db_path: str) -> sqlite3.Connection:
    # New connection per call; autocommit; FK on
    conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()

    # Check if database already exists with old schema
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentences';")
    sentences_exists = cur.fetchone() is not None

    if sentences_exists:
        # Check if migration is needed
        cur.execute("PRAGMA table_info(sentences);")
        columns = [row[1] for row in cur.fetchall()]

        if 'doi_hash' not in columns:
            print("WARNING: Database schema needs migration. Please run: python3 migrate_db.py")
            print("Attempting automatic migration...")

            # Try to add missing columns
            try:
                if 'doi_hash' not in columns:
                    cur.execute("ALTER TABLE sentences ADD COLUMN doi_hash TEXT;")
                    print("Added doi_hash column")

                # Check triples table
                cur.execute("PRAGMA table_info(triples);")
                triple_columns = [row[1] for row in cur.fetchall()]
                if 'contributor_email' not in triple_columns:
                    cur.execute("ALTER TABLE triples ADD COLUMN contributor_email TEXT DEFAULT '';")
                    print("Added contributor_email column to triples")
                if 'project_id' not in triple_columns:
                    cur.execute("ALTER TABLE triples ADD COLUMN project_id INTEGER;")
                    print("Added project_id column to triples")

                conn.commit()
            except Exception as e:
                print(f"Auto-migration failed: {e}")
                conn.rollback()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entity_types (
            name TEXT PRIMARY KEY,
            value TEXT UNIQUE NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS relation_types (
            name TEXT PRIMARY KEY
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            literature_link TEXT,
            doi_hash TEXT,
            created_at TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doi_metadata (
            doi_hash TEXT PRIMARY KEY,
            doi TEXT NOT NULL,
            created_at TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence_id INTEGER NOT NULL,
            source_entity_name TEXT NOT NULL,
            source_entity_attr TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            sink_entity_name TEXT NOT NULL,
            sink_entity_attr TEXT NOT NULL,
            contributor_email TEXT,
            project_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(sentence_id) REFERENCES sentences(id) ON DELETE CASCADE,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            session_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            doi_list TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)

    for name, value in SCHEMA_JSON["span-attribute"].items():
        cur.execute("INSERT OR IGNORE INTO entity_types(name, value) VALUES (?, ?);", (name, value))

    for name in SCHEMA_JSON["relation-type"].keys():
        cur.execute("INSERT OR IGNORE INTO relation_types(name) VALUES (?);", (name,))

    conn.commit()
    conn.close()

def fetch_entity_dropdown_options(db_path: str):
    conn = get_conn(db_path); cur = conn.cursor()
    cur.execute("SELECT name FROM entity_types ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    opts = [name for (name,) in rows]
    return opts

def fetch_relation_dropdown_options(db_path: str):
    conn = get_conn(db_path); cur = conn.cursor()
    cur.execute("SELECT name FROM relation_types ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    opts = [name for (name,) in rows]
    return opts

def upsert_doi_metadata(db_path: str, doi: str) -> str:
    """Store DOI and return the doi_hash."""
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    doi_hash = generate_doi_hash(doi)
    cur.execute("""INSERT OR REPLACE INTO doi_metadata(doi_hash, doi, created_at)
                   VALUES (?, ?, ?);""",
                (doi_hash, doi, now))
    conn.close()
    return doi_hash

def upsert_sentence(db_path: str, sid, text: str, link: str,
                    doi_hash: str = None) -> int:
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    if sid is None or str(sid).strip() == "":
        cur.execute("""INSERT INTO sentences(text, literature_link, doi_hash, created_at)
                       VALUES (?, ?, ?, ?);""",
                    (text, link, doi_hash, now))
        cur.execute("SELECT last_insert_rowid();")
        new_id = cur.fetchone()[0]
        conn.close()
        return new_id

    try:
        sid = int(sid)
    except Exception:
        cur.execute("""INSERT INTO sentences(text, literature_link, doi_hash, created_at)
                       VALUES (?, ?, ?, ?);""",
                    (text, link, doi_hash, now))
        cur.execute("SELECT last_insert_rowid();")
        new_id = cur.fetchone()[0]
        conn.close()
        return new_id

    cur.execute("SELECT COUNT(1) FROM sentences WHERE id=?;", (sid,))
    exists = cur.fetchone()[0] > 0
    if exists:
        cur.execute("""UPDATE sentences SET text=?, literature_link=?, doi_hash=?
                       WHERE id=?;""",
                    (text, link, doi_hash, sid))
        conn.close()
        return sid
    else:
        cur.execute("""INSERT INTO sentences(id, text, literature_link, doi_hash, created_at)
                       VALUES (?, ?, ?, ?, ?);""",
                    (sid, text, link, doi_hash, now))
        conn.close()
        return sid

def insert_triple_rows(db_path: str, sentence_id: int, rows: list[dict], contributor_email: str, project_id: int = None) -> None:
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    q = """INSERT INTO triples(
        sentence_id, source_entity_name, source_entity_attr,
        relation_type, sink_entity_name, sink_entity_attr, contributor_email, project_id, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    for r in rows:
        cur.execute(q, (
            sentence_id,
            r["source_entity_name"], r["source_entity_attr"],
            r["relation_type"], r["sink_entity_name"], r["sink_entity_attr"],
            contributor_email,
            project_id,
            now
        ))
    conn.close()

def add_relation_type(db_path: str, name: str) -> bool:
    if not name or not name.strip():
        return False
    conn = get_conn(db_path); cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO relation_types(name) VALUES (?);", (name.strip(),))
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def add_entity_type(db_path: str, display_name: str, value: str) -> bool:
    if not display_name or not value:
        return False
    conn = get_conn(db_path); cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO entity_types(name, value) VALUES (?, ?);",
                    (display_name.strip(), value.strip()))
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

# -----------------------------
# Admin authentication functions
# -----------------------------
def create_admin_user(db_path: str, email: str, password: str) -> bool:
    """Create an admin user with hashed password."""
    import bcrypt
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    try:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT OR REPLACE INTO admin_users(email, password_hash, created_at) VALUES (?, ?, ?);",
                    (email.strip(), password_hash, now))
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to create admin user: {e}")
        conn.close()
        return False

def verify_admin_password(db_path: str, email: str, password: str) -> bool:
    """Verify admin user password."""
    import bcrypt
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        cur.execute("SELECT password_hash FROM admin_users WHERE email = ?;", (email.strip(),))
        result = cur.fetchone()
        conn.close()
        
        if not result:
            return False
        
        stored_hash = result[0]
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception as e:
        print(f"Failed to verify admin password: {e}")
        conn.close()
        return False

# -----------------------------
# Project management functions
# -----------------------------
def create_project(db_path: str, name: str, description: str, doi_list: list, created_by: str) -> int:
    """Create a new project with a list of DOIs."""
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    try:
        doi_list_json = json.dumps(doi_list)
        cur.execute("""INSERT INTO projects(name, description, doi_list, created_by, created_at)
                       VALUES (?, ?, ?, ?, ?);""",
                    (name, description, doi_list_json, created_by, now))
        cur.execute("SELECT last_insert_rowid();")
        project_id = cur.fetchone()[0]
        conn.close()
        return project_id
    except Exception as e:
        print(f"Failed to create project: {e}")
        conn.close()
        return -1

def get_all_projects(db_path: str) -> list:
    """Get all projects."""
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        cur.execute("SELECT id, name, description, doi_list, created_by, created_at FROM projects ORDER BY created_at DESC;")
        rows = cur.fetchall()
        conn.close()
        
        projects = []
        for row in rows:
            projects.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "doi_list": json.loads(row[3]),
                "created_by": row[4],
                "created_at": row[5]
            })
        return projects
    except Exception as e:
        print(f"Failed to get projects: {e}")
        conn.close()
        return []

def get_project_by_id(db_path: str, project_id: int) -> dict:
    """Get a specific project by ID."""
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        cur.execute("SELECT id, name, description, doi_list, created_by, created_at FROM projects WHERE id = ?;", (project_id,))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "doi_list": json.loads(row[3]),
            "created_by": row[4],
            "created_at": row[5]
        }
    except Exception as e:
        print(f"Failed to get project: {e}")
        conn.close()
        return None

def update_project(db_path: str, project_id: int, name: str = None, description: str = None, doi_list: list = None) -> bool:
    """Update a project."""
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        # Get current project
        cur.execute("SELECT name, description, doi_list FROM projects WHERE id = ?;", (project_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        
        current_name, current_desc, current_dois = row
        
        # Use provided values or keep current ones
        new_name = name if name is not None else current_name
        new_desc = description if description is not None else current_desc
        new_dois = json.dumps(doi_list) if doi_list is not None else current_dois
        
        cur.execute("""UPDATE projects SET name = ?, description = ?, doi_list = ? WHERE id = ?;""",
                    (new_name, new_desc, new_dois, project_id))
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to update project: {e}")
        conn.close()
        return False

def delete_project(db_path: str, project_id: int) -> bool:
    """Delete a project."""
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        cur.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to delete project: {e}")
        conn.close()
        return False

def update_triple(db_path: str, triple_id: int, source_entity_name: str = None, 
                source_entity_attr: str = None, relation_type: str = None,
                sink_entity_name: str = None, sink_entity_attr: str = None) -> bool:
    """Update a triple's fields."""
    conn = get_conn(db_path); cur = conn.cursor()
    
    try:
        # Get current triple
        cur.execute("""SELECT source_entity_name, source_entity_attr, relation_type, 
                       sink_entity_name, sink_entity_attr FROM triples WHERE id = ?;""", (triple_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return False
        
        # Use provided values or keep current ones
        new_src_name = source_entity_name if source_entity_name is not None else row[0]
        new_src_attr = source_entity_attr if source_entity_attr is not None else row[1]
        new_rel_type = relation_type if relation_type is not None else row[2]
        new_sink_name = sink_entity_name if sink_entity_name is not None else row[3]
        new_sink_attr = sink_entity_attr if sink_entity_attr is not None else row[4]
        
        cur.execute("""UPDATE triples SET source_entity_name = ?, source_entity_attr = ?,
                       relation_type = ?, sink_entity_name = ?, sink_entity_attr = ?
                       WHERE id = ?;""",
                    (new_src_name, new_src_attr, new_rel_type, new_sink_name, new_sink_attr, triple_id))
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to update triple: {e}")
        conn.close()
        return False
