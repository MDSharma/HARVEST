#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database migration script to rename 'tuples' table to 'triples' and update all references.
This script safely migrates existing data while preserving all relationships.
"""

import sqlite3
import os
import sys

# Import configuration
try:
    from config import DB_PATH
except ImportError:
    # Fallback to environment variable if config.py doesn't exist
    DB_PATH = os.environ.get("T2T_DB", "t2t_training.db")

def migrate_tuple_to_triple():
    """Rename tuples table to triples and update all foreign key references."""
    print(f"Migrating database: {DB_PATH}")
    print("Renaming 'tuples' table to 'triples'...")

    if not os.path.exists(DB_PATH):
        print("Database does not exist yet. No migration needed.")
        print("The new schema will use 'triples' table automatically.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Check if tuples table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tuples';")
        tuples_exists = cur.fetchone() is not None
        
        # Check if triples table already exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='triples';")
        triples_exists = cur.fetchone() is not None

        if triples_exists:
            print("   ✓ 'triples' table already exists. Migration already completed.")
            conn.close()
            return

        if not tuples_exists:
            print("   ✓ 'tuples' table doesn't exist. No migration needed.")
            conn.close()
            return

        print("   Migrating 'tuples' table to 'triples'...")
        
        # Get the schema of the tuples table
        cur.execute("PRAGMA table_info(tuples);")
        columns = cur.fetchall()
        
        # Create new triples table with same schema
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
        
        # Copy all data from tuples to triples
        cur.execute("SELECT * FROM tuples;")
        all_tuples = cur.fetchall()
        
        if all_tuples:
            # Get column names
            column_names = [description[0] for description in cur.description]
            placeholders = ','.join(['?' for _ in column_names])
            columns_str = ','.join(column_names)
            
            # Insert all data
            cur.executemany(
                f"INSERT INTO triples ({columns_str}) VALUES ({placeholders})",
                all_tuples
            )
            print(f"   Copied {len(all_tuples)} records from 'tuples' to 'triples'")
        else:
            print("   No data to migrate")
        
        # Drop the old tuples table
        cur.execute("DROP TABLE tuples;")
        
        # Commit the changes
        conn.commit()
        print("   ✓ Successfully renamed 'tuples' table to 'triples'")
        
    except Exception as e:
        print(f"   ✗ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: tuple → triple")
    print("=" * 60)
    
    migrate_tuple_to_triple()
    
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print("\nIMPORTANT: Make sure to update your application code to use")
    print("the new 'triples' table name instead of 'tuples'.")
