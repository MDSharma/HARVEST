#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script v2 to optimize schema:
1. Remove article_title, article_authors, article_year from doi_metadata (can be fetched on-demand)
2. Remove contributor_email from sentences table (tracked at tuple level)
3. Add projects table for project-based annotation
4. Add admin password hash table
"""

import sqlite3
import os
import sys
from datetime import datetime

# Import generate_doi_hash from t2t_store
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t2t_store import generate_doi_hash

# Import configuration
try:
    from config import DB_PATH
except ImportError:
    # Fallback to environment variable if config.py doesn't exist
    DB_PATH = os.environ.get("T2T_DB", "t2t_training.db")

def migrate_database_v2():
    print(f"Migrating database v2: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("Database does not exist yet. No migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # 1. Migrate doi_metadata table - remove article_title, article_authors, article_year
        print("\n1. Checking doi_metadata table...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='doi_metadata';")
        doi_metadata_exists = cur.fetchone() is not None
        
        if doi_metadata_exists:
            cur.execute("PRAGMA table_info(doi_metadata);")
            doi_metadata_columns = [row[1] for row in cur.fetchall()]
            
            if 'article_title' in doi_metadata_columns or 'article_authors' in doi_metadata_columns:
                print("   Removing article metadata columns from doi_metadata...")
                
                # Create new table without article metadata columns
                cur.execute("""
                    CREATE TABLE doi_metadata_new (
                        doi_hash TEXT PRIMARY KEY,
                        doi TEXT NOT NULL,
                        created_at TEXT
                    );
                """)
                
                # Copy data (only doi_hash, doi, created_at)
                cur.execute("""
                    INSERT INTO doi_metadata_new (doi_hash, doi, created_at)
                    SELECT doi_hash, doi, created_at FROM doi_metadata;
                """)
                
                # Drop old table and rename
                cur.execute("DROP TABLE doi_metadata;")
                cur.execute("ALTER TABLE doi_metadata_new RENAME TO doi_metadata;")
                print("   ✓ Removed article metadata columns from doi_metadata")
            else:
                print("   ✓ doi_metadata already optimized")
        else:
            print("   ✓ doi_metadata table doesn't exist yet (will be created)")

        # 2. Migrate sentences table - remove contributor_email and handle old schema
        print("\n2. Checking sentences table...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sentences';")
        sentences_exists = cur.fetchone() is not None
        
        if not sentences_exists:
            print("   ✓ sentences table doesn't exist yet (will be created)")
        else:
            cur.execute("PRAGMA table_info(sentences);")
            sentences_columns = [row[1] for row in cur.fetchall()]
            
            has_doi_hash = 'doi_hash' in sentences_columns
            has_contributor_email = 'contributor_email' in sentences_columns
            has_old_doi = 'doi' in sentences_columns
            
            if not has_doi_hash or has_contributor_email or has_old_doi:
                print("   Migrating sentences table...")
                
                # Create new table with optimized schema
                cur.execute("""
                    CREATE TABLE sentences_new (
                        id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        literature_link TEXT,
                        doi_hash TEXT,
                        created_at TEXT
                    );
                """)
                
                # Migrate data
                if has_old_doi and not has_doi_hash:
                    # Old schema with doi, article_title, etc.
                    print("   Converting old DOI format to doi_hash...")
                    
                    # Create doi_metadata table if it doesn't exist
                    if not doi_metadata_exists:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS doi_metadata (
                                doi_hash TEXT PRIMARY KEY,
                                doi TEXT NOT NULL,
                                created_at TEXT
                            );
                        """)
                    
                    cur.execute("SELECT id, text, literature_link, doi, created_at FROM sentences;")
                    rows = cur.fetchall()
                    
                    for row in rows:
                        sid, text, lit_link, doi, created = row
                        doi_hash = None
                        
                        if doi:
                            doi_hash = generate_doi_hash(doi)
                            cur.execute("""
                                INSERT OR IGNORE INTO doi_metadata(doi_hash, doi, created_at)
                                VALUES (?, ?, ?);
                            """, (doi_hash, doi, created))
                        
                        cur.execute("""
                            INSERT INTO sentences_new(id, text, literature_link, doi_hash, created_at)
                            VALUES (?, ?, ?, ?, ?);
                        """, (sid, text, lit_link, doi_hash, created))
                    
                    print(f"   Migrated {len(rows)} sentences from old schema")
                elif has_doi_hash and has_contributor_email:
                    # New schema but with contributor_email
                    cur.execute("""
                        INSERT INTO sentences_new (id, text, literature_link, doi_hash, created_at)
                        SELECT id, text, literature_link, doi_hash, created_at FROM sentences;
                    """)
                    print("   Removed contributor_email column")
                else:
                    # Already correct schema?
                    cur.execute("""
                        INSERT INTO sentences_new (id, text, literature_link, doi_hash, created_at)
                        SELECT id, text, literature_link, doi_hash, created_at FROM sentences;
                    """)
                
                # Drop old table and rename
                cur.execute("DROP TABLE sentences;")
                cur.execute("ALTER TABLE sentences_new RENAME TO sentences;")
                print("   ✓ Sentences table migrated")
            else:
                print("   ✓ sentences already optimized")

        # 3. Ensure tuples table has contributor_email and project_id
        print("\n3. Checking tuples table...")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tuples';")
        tuples_exists = cur.fetchone() is not None
        
        if not tuples_exists:
            print("   ✓ tuples table doesn't exist yet (will be created)")
        else:
            cur.execute("PRAGMA table_info(tuples);")
            tuple_columns = [row[1] for row in cur.fetchall()]
            
            if 'contributor_email' not in tuple_columns:
                print("   Adding contributor_email to tuples...")
                cur.execute("ALTER TABLE tuples ADD COLUMN contributor_email TEXT DEFAULT '';")
                print("   ✓ Added contributor_email column")
            else:
                print("   ✓ tuples already has contributor_email")
            
            if 'project_id' not in tuple_columns:
                print("   Adding project_id to tuples...")
                cur.execute("ALTER TABLE tuples ADD COLUMN project_id INTEGER;")
                print("   ✓ Added project_id column")
            else:
                print("   ✓ tuples already has project_id")

        # 4. Create projects table
        print("\n4. Creating projects table...")
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
        print("   ✓ Created projects table")

        # 5. Create admin_users table
        print("\n5. Creating admin_users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                email TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        print("   ✓ Created admin_users table")

        conn.commit()
        print("\n✅ Migration v2 completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration v2 failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database_v2()
