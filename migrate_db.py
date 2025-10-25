#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script to update schema to new version with doi_hash.
This preserves existing data while adding new columns and tables.
"""

import sqlite3
import os
import sys
from t2t_store import generate_doi_hash

DB_PATH = os.environ.get("T2T_DB", "t2t.db")

def migrate_database():
    print(f"Migrating database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("Database does not exist yet. No migration needed.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Check if doi_hash column exists in sentences table
        cur.execute("PRAGMA table_info(sentences);")
        columns = [row[1] for row in cur.fetchall()]

        # Migrate sentences table if needed
        if 'doi_hash' not in columns:
            print("Migrating sentences table...")

            # Check if old columns exist
            has_doi = 'doi' in columns
            has_article_title = 'article_title' in columns
            has_article_authors = 'article_authors' in columns
            has_article_year = 'article_year' in columns

            # Create doi_metadata table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS doi_metadata (
                    doi_hash TEXT PRIMARY KEY,
                    doi TEXT NOT NULL,
                    article_title TEXT,
                    article_authors TEXT,
                    article_year TEXT,
                    created_at TEXT
                );
            """)
            print("Created doi_metadata table")

            # If old columns exist, migrate the data
            if has_doi:
                # Create new sentences table with updated schema
                cur.execute("""
                    CREATE TABLE sentences_new (
                        id INTEGER PRIMARY KEY,
                        text TEXT NOT NULL,
                        literature_link TEXT,
                        doi_hash TEXT,
                        contributor_email TEXT,
                        created_at TEXT
                    );
                """)
                print("Created new sentences table")

                # Get all existing sentences with DOI data
                cur.execute("SELECT id, text, literature_link, doi, article_title, article_authors, article_year, contributor_email, created_at FROM sentences;")
                rows = cur.fetchall()

                # Migrate data
                for row in rows:
                    sid, text, lit_link, doi, title, authors, year, email, created = row

                    doi_hash = None
                    if doi:
                        # Generate doi_hash and insert metadata
                        doi_hash = generate_doi_hash(doi)
                        cur.execute("""
                            INSERT OR IGNORE INTO doi_metadata(doi_hash, doi, article_title, article_authors, article_year, created_at)
                            VALUES (?, ?, ?, ?, ?, ?);
                        """, (doi_hash, doi, title, authors, year, created))

                    # Insert into new sentences table
                    cur.execute("""
                        INSERT INTO sentences_new(id, text, literature_link, doi_hash, contributor_email, created_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                    """, (sid, text, lit_link, doi_hash, email, created))

                print(f"Migrated {len(rows)} sentences")

                # Drop old table and rename new one
                cur.execute("DROP TABLE sentences;")
                cur.execute("ALTER TABLE sentences_new RENAME TO sentences;")
                print("Replaced old sentences table with new schema")
            else:
                # No old DOI data, just add the column
                cur.execute("ALTER TABLE sentences ADD COLUMN doi_hash TEXT;")
                print("Added doi_hash column to sentences table")

        # Check if triples table has contributor_email column
        cur.execute("PRAGMA table_info(triples);")
        triple_columns = [row[1] for row in cur.fetchall()]

        if 'contributor_email' not in triple_columns:
            print("Adding contributor_email to triples table...")
            cur.execute("ALTER TABLE triples ADD COLUMN contributor_email TEXT DEFAULT '';")
            print("Added contributor_email column to triples table")

        # Create user_sessions table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        print("Ensured user_sessions table exists")

        conn.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
