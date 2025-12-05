#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema migration for Trait Extraction feature

This script adds the necessary tables for trait extraction:
- documents: Tracks documents for extraction
- extraction_jobs: Tracks extraction job status
- Extends triples table with extraction metadata
"""

import sqlite3
import os
import sys
from datetime import datetime

def get_conn(db_path: str) -> sqlite3.Connection:
    """Get database connection with foreign keys enabled"""
    conn = sqlite3.Connection(db_path, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def migrate_trait_extraction(db_path: str) -> None:
    """Add trait extraction tables to the database"""
    
    print(f"Starting trait extraction migration on {db_path}")
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    try:
        # Create documents table for tracking PDFs/texts for extraction
        print("Creating documents table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trait_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                file_path TEXT NOT NULL,
                text_content TEXT,
                doi TEXT,
                doi_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)
        
        # Index for fast lookups
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_trait_documents_project
            ON trait_documents(project_id);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_trait_documents_doi_hash
            ON trait_documents(doi_hash);
        """)
        
        # Create extraction jobs table
        print("Creating extraction_jobs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trait_extraction_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                document_ids TEXT NOT NULL,
                model_profile TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                error_message TEXT,
                results TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)
        
        # Index for job status queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_jobs_status
            ON trait_extraction_jobs(status);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extraction_jobs_project
            ON trait_extraction_jobs(project_id);
        """)
        
        # Check if triples table needs additional columns for trait extraction
        print("Checking triples table for extraction columns...")
        cur.execute("PRAGMA table_info(triples);")
        columns = {row[1] for row in cur.fetchall()}
        
        # Add extraction-specific columns to triples if they don't exist
        if 'model_profile' not in columns:
            print("Adding model_profile column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN model_profile TEXT;")
        
        if 'confidence' not in columns:
            print("Adding confidence column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN confidence REAL;")
        
        if 'status' not in columns:
            print("Adding status column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN status TEXT DEFAULT 'accepted';")
        
        if 'trait_name' not in columns:
            print("Adding trait_name column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN trait_name TEXT;")
        
        if 'trait_value' not in columns:
            print("Adding trait_value column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN trait_value TEXT;")
        
        if 'unit' not in columns:
            print("Adding unit column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN unit TEXT;")
        
        if 'job_id' not in columns:
            print("Adding job_id column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN job_id INTEGER;")
        
        if 'document_id' not in columns:
            print("Adding document_id column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN document_id INTEGER;")
        
        if 'updated_at' not in columns:
            print("Adding updated_at column to triples...")
            cur.execute("ALTER TABLE triples ADD COLUMN updated_at TEXT;")
        
        # Create model configs table for storing model profiles
        print("Creating model_configs table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trait_model_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                backend TEXT NOT NULL,
                params TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback_migration(db_path: str) -> None:
    """Rollback trait extraction migration (for testing)"""
    print(f"Rolling back trait extraction migration on {db_path}")
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    try:
        # Drop tables in reverse order
        cur.execute("DROP TABLE IF EXISTS trait_model_configs;")
        cur.execute("DROP INDEX IF EXISTS idx_extraction_jobs_project;")
        cur.execute("DROP INDEX IF EXISTS idx_extraction_jobs_status;")
        cur.execute("DROP TABLE IF EXISTS trait_extraction_jobs;")
        cur.execute("DROP INDEX IF EXISTS idx_trait_documents_doi_hash;")
        cur.execute("DROP INDEX IF EXISTS idx_trait_documents_project;")
        cur.execute("DROP TABLE IF EXISTS trait_documents;")
        
        # Note: We don't remove columns from triples as SQLite doesn't support DROP COLUMN easily
        # They will just remain unused if trait extraction is disabled
        
        conn.commit()
        print("Rollback completed successfully!")
        
    except Exception as e:
        print(f"Error during rollback: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    # Get database path from config or environment
    try:
        from config import DB_PATH
    except ImportError:
        DB_PATH = os.environ.get("HARVEST_DB", "harvest.db")
    
    # Check if rollback is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback_migration(DB_PATH)
    else:
        migrate_trait_extraction(DB_PATH)
