#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup script to remove orphaned sentences (sentences without any associated triples).
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

def cleanup_orphaned_sentences(dry_run=True):
    """
    Remove sentences that have no associated triples.
    
    Args:
        dry_run: If True, only report what would be deleted without actually deleting.
    """
    print(f"{'DRY RUN: ' if dry_run else ''}Cleaning up orphaned sentences in {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database does not exist.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Find sentences without triples
        cur.execute("""
            SELECT s.id, s.text, s.literature_link, s.created_at
            FROM sentences s
            LEFT JOIN triples t ON s.id = t.sentence_id
            WHERE t.id IS NULL;
        """)
        
        orphaned = cur.fetchall()
        
        if not orphaned:
            print("✓ No orphaned sentences found.")
            return
        
        print(f"\nFound {len(orphaned)} orphaned sentence(s):")
        for row in orphaned:
            sid, text, lit_link, created = row
            text_preview = text[:80] + "..." if len(text) > 80 else text
            print(f"  ID {sid}: {text_preview}")
            if lit_link:
                print(f"          Literature: {lit_link}")
        
        if not dry_run:
            # Delete orphaned sentences
            cur.execute("""
                DELETE FROM sentences
                WHERE id IN (
                    SELECT s.id
                    FROM sentences s
                    LEFT JOIN triples t ON s.id = t.sentence_id
                    WHERE t.id IS NULL
                );
            """)
            conn.commit()
            print(f"\n✅ Deleted {len(orphaned)} orphaned sentence(s).")
        else:
            print(f"\nDRY RUN: Would delete {len(orphaned)} sentence(s).")
            print("Run with --execute flag to actually delete.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def add_default_project_to_null_triples(project_name="Uncategorized", dry_run=True):
    """
    Create a default project and assign all triples with NULL project_id to it.
    
    Args:
        project_name: Name for the default project
        dry_run: If True, only report what would be changed without actually changing.
    """
    print(f"\n{'DRY RUN: ' if dry_run else ''}Adding default project to triples with NULL project_id")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Count triples with NULL project_id
        cur.execute("SELECT COUNT(*) FROM triples WHERE project_id IS NULL;")
        null_count = cur.fetchone()[0]
        
        if null_count == 0:
            print("✓ All triples already have a project_id.")
            return
        
        print(f"Found {null_count} triple(s) without a project_id.")
        
        if not dry_run:
            # Check if default project exists
            cur.execute("SELECT id FROM projects WHERE name = ?;", (project_name,))
            result = cur.fetchone()
            
            if result:
                default_project_id = result[0]
                print(f"Using existing default project (ID: {default_project_id})")
            else:
                # Create default project
                from datetime import datetime
                cur.execute("""
                    INSERT INTO projects (name, description, doi_list, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?);
                """, (
                    project_name,
                    "Default project for uncategorized annotations",
                    "[]",  # Empty DOI list
                    "system",
                    datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat()
                ))
                default_project_id = cur.lastrowid
                print(f"Created default project (ID: {default_project_id})")
            
            # Update triples
            cur.execute("""
                UPDATE triples
                SET project_id = ?
                WHERE project_id IS NULL;
            """, (default_project_id,))
            
            conn.commit()
            print(f"✅ Updated {null_count} triple(s) with default project.")
        else:
            print(f"DRY RUN: Would assign {null_count} triple(s) to default project '{project_name}'.")
            print("Run with --execute flag to actually update.")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up orphaned sentences and assign default project")
    parser.add_argument("--execute", action="store_true", help="Actually perform the cleanup (default is dry-run)")
    parser.add_argument("--default-project", default="Uncategorized", help="Name for default project")
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    print("=" * 70)
    print("Text2Trait Database Cleanup Utility")
    print("=" * 70)
    
    # Step 1: Clean up orphaned sentences
    cleanup_orphaned_sentences(dry_run=dry_run)
    
    # Step 2: Add default project to triples with NULL project_id
    add_default_project_to_null_triples(project_name=args.default_project, dry_run=dry_run)
    
    print("\n" + "=" * 70)
    if dry_run:
        print("This was a DRY RUN. No changes were made.")
        print("Use --execute flag to apply changes.")
    else:
        print("Cleanup complete!")
    print("=" * 70)
