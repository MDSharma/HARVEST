#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script to remove redundant fields.
Removes article_title, article_authors, article_year from doi_metadata
and contributor_email from sentences table.
"""

import sqlite3
import sys
import os
from datetime import datetime

DB_PATH = os.environ.get("T2T_DB", "t2t.db")

def migrate(db_path: str):
    """Migrate database to remove redundant fields."""
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        print("No migration needed - fresh database will use new schema.")
        return

    print(f"Migrating database: {db_path}")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Backup database
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup at: {backup_path}")
    backup_conn = sqlite3.connect(backup_path)
    conn.backup(backup_conn)
    backup_conn.close()
    print("✓ Backup created")

    try:
        # Check current schema
        cur.execute("PRAGMA table_info(doi_metadata);")
        doi_metadata_columns = {row[1] for row in cur.fetchall()}

        cur.execute("PRAGMA table_info(sentences);")
        sentences_columns = {row[1] for row in cur.fetchall()}

        print("\nCurrent schema:")
        print(f"  doi_metadata columns: {doi_metadata_columns}")
        print(f"  sentences columns: {sentences_columns}")

        # Migrate doi_metadata table if needed
        if 'article_title' in doi_metadata_columns or 'article_authors' in doi_metadata_columns:
            print("\n1. Migrating doi_metadata table...")
            print("   Removing: article_title, article_authors, article_year")

            # Create new table with correct schema
            cur.execute("""
                CREATE TABLE doi_metadata_new (
                    doi_hash TEXT PRIMARY KEY,
                    doi TEXT NOT NULL,
                    created_at TEXT
                );
            """)

            # Copy data (only relevant columns)
            cur.execute("""
                INSERT INTO doi_metadata_new (doi_hash, doi, created_at)
                SELECT doi_hash, doi, created_at
                FROM doi_metadata;
            """)

            # Replace old table
            cur.execute("DROP TABLE doi_metadata;")
            cur.execute("ALTER TABLE doi_metadata_new RENAME TO doi_metadata;")
            conn.commit()
            print("   ✓ doi_metadata migrated")
        else:
            print("\n1. doi_metadata table already clean")

        # Migrate sentences table if needed
        if 'contributor_email' in sentences_columns:
            print("\n2. Migrating sentences table...")
            print("   Removing: contributor_email")

            # Create new table with correct schema
            cur.execute("""
                CREATE TABLE sentences_new (
                    id INTEGER PRIMARY KEY,
                    text TEXT NOT NULL,
                    literature_link TEXT,
                    doi_hash TEXT,
                    created_at TEXT
                );
            """)

            # Copy data (only relevant columns)
            cur.execute("""
                INSERT INTO sentences_new (id, text, literature_link, doi_hash, created_at)
                SELECT id, text, literature_link, doi_hash, created_at
                FROM sentences;
            """)

            # Replace old table
            cur.execute("DROP TABLE sentences;")
            cur.execute("ALTER TABLE sentences_new RENAME TO sentences;")
            conn.commit()
            print("   ✓ sentences migrated")
        else:
            print("\n2. sentences table already clean")

        # Verify new schema
        print("\n" + "=" * 60)
        print("Migration complete!")
        print("\nNew schema:")

        cur.execute("PRAGMA table_info(doi_metadata);")
        print("  doi_metadata columns:", [row[1] for row in cur.fetchall()])

        cur.execute("PRAGMA table_info(sentences);")
        print("  sentences columns:", [row[1] for row in cur.fetchall()])

        # Count records
        cur.execute("SELECT COUNT(*) FROM doi_metadata;")
        doi_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sentences;")
        sentence_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM tuples;")
        tuple_count = cur.fetchone()[0]

        print(f"\nData preserved:")
        print(f"  DOIs: {doi_count}")
        print(f"  Sentences: {sentence_count}")
        print(f"  Tuples: {tuple_count}")
        print(f"\nBackup saved at: {backup_path}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        print(f"\nYour original database is safe. Backup at: {backup_path}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH

    print("Database Schema Cleanup Migration")
    print("=" * 60)
    print("This will remove redundant fields:")
    print("  - article_title, article_authors, article_year from doi_metadata")
    print("  - contributor_email from sentences")
    print("\nThese fields are redundant because:")
    print("  - Article metadata can be fetched from DOI when needed")
    print("  - contributor_email is tracked in tuples table")
    print("=" * 60)

    response = input(f"\nProceed with migration of {db_path}? [y/N]: ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)

    migrate(db_path)
