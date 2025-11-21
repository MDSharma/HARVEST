#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime
import json
import hashlib

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
    """Generate a hash from DOI for file naming (consistent with pdf_manager.py)."""
    if not doi:
        return ""
    return hashlib.sha256(doi.encode('utf-8')).hexdigest()[:16]

ADMIN_EMAILS = set(os.environ.get("HARVEST_ADMIN_EMAILS", "").split(","))

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
            print("WARNING: Database schema needs migration. Please run: python3 migrate_db_v2.py")
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
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_download_progress (
            project_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL,
            total INTEGER NOT NULL,
            current INTEGER NOT NULL,
            current_doi TEXT,
            downloaded TEXT,  -- JSON array of [doi, filename, msg, source]
            needs_upload TEXT,  -- JSON array of [doi, filename, reason]
            errors TEXT,  -- JSON array of [doi, error]
            project_dir TEXT,
            start_time REAL,
            end_time REAL,
            updated_at REAL NOT NULL
        );
    """)
    
    # Email verification tables for OTP authentication
    # These tables support the email verification feature (ENABLE_OTP_VALIDATION)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_verifications (
            email TEXT PRIMARY KEY,
            code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            last_attempt_at TEXT,
            ip_address_hash TEXT
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verified_sessions (
            session_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            verified_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address_hash TEXT
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_verification_rate_limit (
            email TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            ip_address_hash TEXT
        );
    """)
    
    # Indexes for email verification tables
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_email_verifications_expires 
        ON email_verifications(expires_at);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_verified_sessions_expires 
        ON verified_sessions(expires_at);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rate_limit_email_time
        ON email_verification_rate_limit(email, timestamp);
    """)
    
    # DOI Batch Management tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doi_batches (
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            batch_name TEXT NOT NULL,
            batch_number INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            UNIQUE(project_id, batch_number)
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doi_batch_assignments (
            assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            doi TEXT NOT NULL,
            batch_id INTEGER NOT NULL,
            assigned_at TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (batch_id) REFERENCES doi_batches(batch_id),
            UNIQUE(project_id, doi)
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS doi_annotation_status (
            status_id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            doi TEXT NOT NULL,
            annotator_email TEXT,
            status TEXT DEFAULT 'unstarted',
            last_updated TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            UNIQUE(project_id, doi)
        );
    """)
    
    # Indexes for batch management
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_doi_batches_project
        ON doi_batches(project_id);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_doi_batch_assignments_batch
        ON doi_batch_assignments(batch_id);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_doi_annotation_status_project_doi
        ON doi_annotation_status(project_id, doi);
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

# -----------------------------
# PDF Download Progress Management
# -----------------------------

def init_pdf_download_progress(db_path: str, project_id: int, total: int, project_dir: str) -> bool:
    """Initialize progress tracking for a PDF download job."""
    try:
        import time
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT OR REPLACE INTO pdf_download_progress 
            (project_id, status, total, current, current_doi, downloaded, needs_upload, 
             errors, project_dir, start_time, updated_at)
            VALUES (?, 'running', ?, 0, '', '[]', '[]', '[]', ?, ?, ?)
        """, (project_id, total, project_dir, time.time(), time.time()))
        
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to init PDF download progress: {e}")
        return False

def update_pdf_download_progress(db_path: str, project_id: int, updates: dict) -> bool:
    """Update progress for a PDF download job."""
    try:
        import time
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        # Build dynamic UPDATE query based on what fields are provided
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['status', 'total', 'current', 'current_doi', 'project_dir', 'end_time']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
            elif key in ['downloaded', 'needs_upload', 'errors']:
                # Convert lists to JSON strings
                set_clauses.append(f"{key} = ?")
                values.append(json.dumps(value))
        
        # Always update updated_at
        set_clauses.append("updated_at = ?")
        values.append(time.time())
        
        # Add project_id for WHERE clause
        values.append(project_id)
        
        query = f"UPDATE pdf_download_progress SET {', '.join(set_clauses)} WHERE project_id = ?"
        cur.execute(query, values)
        
        conn.close()
        return True
    except Exception as e:
        print(f"Failed to update PDF download progress: {e}")
        return False

def get_pdf_download_progress(db_path: str, project_id: int) -> dict:
    """Get current progress for a PDF download job."""
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT status, total, current, current_doi, downloaded, needs_upload, 
                   errors, project_dir, start_time, end_time, updated_at
            FROM pdf_download_progress
            WHERE project_id = ?
        """, (project_id,))
        
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "status": row[0],
            "total": row[1],
            "current": row[2],
            "current_doi": row[3],
            "downloaded": json.loads(row[4]) if row[4] else [],
            "needs_upload": json.loads(row[5]) if row[5] else [],
            "errors": json.loads(row[6]) if row[6] else [],
            "project_dir": row[7],
            "start_time": row[8],
            "end_time": row[9],
            "updated_at": row[10]
        }
    except Exception as e:
        print(f"Failed to get PDF download progress: {e}")
        return None

def cleanup_old_pdf_download_progress(db_path: str, max_age_seconds: int = 3600) -> int:
    """Clean up old completed/error progress entries. Returns number of entries deleted."""
    try:
        import time
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        cutoff_time = time.time() - max_age_seconds
        
        cur.execute("""
            DELETE FROM pdf_download_progress
            WHERE (status = 'completed' OR status = 'error')
            AND updated_at < ?
        """, (cutoff_time,))
        
        deleted = cur.rowcount
        conn.close()
        return deleted
    except Exception as e:
        print(f"Failed to cleanup PDF download progress: {e}")
        return 0


# ============================================================================
# DOI Batch Management Functions
# ============================================================================

def create_batches(db_path: str, project_id: int, batch_size: int = 20, strategy: str = "sequential") -> list:
    """
    Auto-create batches for a project's DOIs.
    
    Args:
        db_path: Path to database
        project_id: Project ID
        batch_size: Number of DOIs per batch
        strategy: 'sequential', 'random', or 'by_date'
    
    Returns:
        List of created batch dictionaries
    """
    import random
    from datetime import datetime
    
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        # Get project DOIs
        project = get_project_by_id(db_path, project_id)
        if not project:
            return []
        
        doi_list = project['doi_list']
        if not doi_list:
            return []
        
        # Delete existing batches for this project
        cur.execute("DELETE FROM doi_batch_assignments WHERE project_id = ?", (project_id,))
        cur.execute("DELETE FROM doi_batches WHERE project_id = ?", (project_id,))
        
        # Apply strategy
        if strategy == "random":
            random.shuffle(doi_list)
        # 'sequential' and 'by_date' use the existing order
        
        # Create batches
        created_batches = []
        batch_number = 1
        now = datetime.now().isoformat()
        
        for i in range(0, len(doi_list), batch_size):
            batch_dois = doi_list[i:i + batch_size]
            batch_name = f"Batch {batch_number} ({len(batch_dois)} papers)"
            
            # Insert batch
            cur.execute("""
                INSERT INTO doi_batches (project_id, batch_name, batch_number, created_at)
                VALUES (?, ?, ?, ?)
            """, (project_id, batch_name, batch_number, now))
            
            batch_id = cur.lastrowid
            
            # Insert DOI assignments
            for doi in batch_dois:
                cur.execute("""
                    INSERT INTO doi_batch_assignments (project_id, doi, batch_id, assigned_at)
                    VALUES (?, ?, ?, ?)
                """, (project_id, doi, batch_id, now))
            
            created_batches.append({
                'batch_id': batch_id,
                'project_id': project_id,
                'batch_name': batch_name,
                'batch_number': batch_number,
                'doi_count': len(batch_dois),
                'created_at': now
            })
            
            batch_number += 1
        
        conn.commit()
        conn.close()
        return created_batches
        
    except Exception as e:
        print(f"Failed to create batches: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_project_batches(db_path: str, project_id: int) -> list:
    """
    Get all batches for a project.
    
    Returns:
        List of batch dictionaries with metadata
    """
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                b.batch_id, 
                b.project_id, 
                b.batch_name, 
                b.batch_number, 
                b.created_at,
                COUNT(a.doi) as doi_count
            FROM doi_batches b
            LEFT JOIN doi_batch_assignments a ON b.batch_id = a.batch_id
            WHERE b.project_id = ?
            GROUP BY b.batch_id
            ORDER BY b.batch_number
        """, (project_id,))
        
        rows = cur.fetchall()
        conn.close()
        
        batches = []
        for row in rows:
            batches.append({
                'batch_id': row[0],
                'project_id': row[1],
                'batch_name': row[2],
                'batch_number': row[3],
                'created_at': row[4],
                'doi_count': row[5]
            })
        
        return batches
        
    except Exception as e:
        print(f"Failed to get project batches: {e}")
        return []


def get_batch_dois(db_path: str, project_id: int, batch_id: int) -> list:
    """
    Get all DOIs in a specific batch with their annotation status.
    
    Returns:
        List of DOI dictionaries with status information
    """
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                a.doi,
                s.status,
                s.annotator_email,
                s.last_updated,
                s.started_at,
                s.completed_at
            FROM doi_batch_assignments a
            LEFT JOIN doi_annotation_status s 
                ON a.project_id = s.project_id AND a.doi = s.doi
            WHERE a.batch_id = ? AND a.project_id = ?
            ORDER BY a.assigned_at
        """, (batch_id, project_id))
        
        rows = cur.fetchall()
        conn.close()
        
        dois = []
        for row in rows:
            dois.append({
                'doi': row[0],
                'status': row[1] if row[1] else 'unstarted',
                'annotator_email': row[2],
                'last_updated': row[3],
                'started_at': row[4],
                'completed_at': row[5]
            })
        
        return dois
        
    except Exception as e:
        print(f"Failed to get batch DOIs: {e}")
        return []


def update_doi_status(db_path: str, project_id: int, doi: str, status: str, annotator_email: str = None) -> bool:
    """
    Update the annotation status of a DOI.
    
    Args:
        db_path: Path to database
        project_id: Project ID
        doi: DOI string
        status: 'unstarted', 'in_progress', or 'completed'
        annotator_email: Email of annotator (optional)
    
    Returns:
        True if successful, False otherwise
    """
    from datetime import datetime
    
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Check if status record exists
        cur.execute("""
            SELECT status_id, status FROM doi_annotation_status 
            WHERE project_id = ? AND doi = ?
        """, (project_id, doi))
        
        existing = cur.fetchone()
        
        if existing:
            # Update existing record
            status_id = existing[0]
            old_status = existing[1]
            
            # Set started_at if transitioning to in_progress
            started_at_clause = ""
            if status == 'in_progress' and old_status == 'unstarted':
                started_at_clause = ", started_at = ?"
                cur.execute(f"""
                    UPDATE doi_annotation_status
                    SET status = ?, annotator_email = ?, last_updated = ?{started_at_clause}
                    WHERE status_id = ?
                """, (status, annotator_email, now, now, status_id))
            # Set completed_at if transitioning to completed
            elif status == 'completed' and old_status != 'completed':
                completed_at_clause = ", completed_at = ?"
                cur.execute(f"""
                    UPDATE doi_annotation_status
                    SET status = ?, annotator_email = ?, last_updated = ?{completed_at_clause}
                    WHERE status_id = ?
                """, (status, annotator_email, now, now, status_id))
            else:
                cur.execute("""
                    UPDATE doi_annotation_status
                    SET status = ?, annotator_email = ?, last_updated = ?
                    WHERE status_id = ?
                """, (status, annotator_email, now, status_id))
        else:
            # Insert new record
            started_at = now if status == 'in_progress' else None
            completed_at = now if status == 'completed' else None
            
            cur.execute("""
                INSERT INTO doi_annotation_status 
                (project_id, doi, annotator_email, status, last_updated, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, doi, annotator_email, status, now, started_at, completed_at))
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Failed to update DOI status: {e}")
        return False


def get_doi_status_summary(db_path: str, project_id: int) -> dict:
    """
    Get annotation status summary for all DOIs in a project.
    
    Returns:
        Dictionary with status counts and breakdown by batch
    """
    try:
        conn = get_conn(db_path)
        cur = conn.cursor()
        
        # Get total DOI count from project
        project = get_project_by_id(db_path, project_id)
        if not project:
            return {}
        
        total_dois = len(project['doi_list'])
        
        # Get status counts
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM doi_annotation_status
            WHERE project_id = ?
            GROUP BY status
        """, (project_id,))
        
        status_counts = {row[0]: row[1] for row in cur.fetchall()}
        
        unstarted = total_dois - sum(status_counts.values())
        in_progress = status_counts.get('in_progress', 0)
        completed = status_counts.get('completed', 0)
        
        # Get batch breakdown
        cur.execute("""
            SELECT 
                b.batch_id,
                b.batch_name,
                COUNT(DISTINCT a.doi) as total,
                COUNT(DISTINCT CASE WHEN s.status = 'completed' THEN s.doi END) as completed,
                COUNT(DISTINCT CASE WHEN s.status = 'in_progress' THEN s.doi END) as in_progress
            FROM doi_batches b
            LEFT JOIN doi_batch_assignments a ON b.batch_id = a.batch_id
            LEFT JOIN doi_annotation_status s ON a.project_id = s.project_id AND a.doi = s.doi
            WHERE b.project_id = ?
            GROUP BY b.batch_id
            ORDER BY b.batch_number
        """, (project_id,))
        
        batch_breakdown = []
        for row in cur.fetchall():
            batch_breakdown.append({
                'batch_id': row[0],
                'batch_name': row[1],
                'total': row[2],
                'completed': row[3],
                'in_progress': row[4],
                'unstarted': row[2] - row[3] - row[4]
            })
        
        conn.close()
        
        return {
            'total': total_dois,
            'unstarted': unstarted,
            'in_progress': in_progress,
            'completed': completed,
            'by_batch': batch_breakdown
        }
        
    except Exception as e:
        print(f"Failed to get DOI status summary: {e}")
        return {}
