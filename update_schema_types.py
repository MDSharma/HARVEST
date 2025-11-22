#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database schema update script to ensure all entity types and relation types
from SCHEMA_JSON are present in the database.

This script should be run when new entity types or relation types are added
to SCHEMA_JSON in harvest_store.py.
"""

import sqlite3
import os
import sys

# Import configuration and schema
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_store import SCHEMA_JSON

# Allow override via environment variable
DB_PATH = os.environ.get("HARVEST_DB", None)

if DB_PATH is None:
    try:
        from config import DB_PATH
    except ImportError:
        # Final fallback to default
        DB_PATH = "harvest.db"


def update_schema_types():
    """Update entity_types and relation_types tables with latest SCHEMA_JSON values."""
    print(f"Updating schema types in database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("Database does not exist yet. Run the application first to create it.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Ensure tables exist
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
        
        # Get current entity types from database
        cur.execute("SELECT name FROM entity_types;")
        existing_entities = set(row[0] for row in cur.fetchall())
        
        # Get current relation types from database
        cur.execute("SELECT name FROM relation_types;")
        existing_relations = set(row[0] for row in cur.fetchall())
        
        # Update entity types
        print("\nUpdating entity types...")
        added_entities = 0
        for name, value in SCHEMA_JSON["span-attribute"].items():
            if name not in existing_entities:
                cur.execute("INSERT INTO entity_types(name, value) VALUES (?, ?);", (name, value))
                print(f"  + Added entity type: {name}")
                added_entities += 1
            else:
                # Verify the value is correct
                cur.execute("SELECT value FROM entity_types WHERE name = ?;", (name,))
                current_value = cur.fetchone()[0]
                if current_value != value:
                    cur.execute("UPDATE entity_types SET value = ? WHERE name = ?;", (value, name))
                    print(f"  ~ Updated entity type value: {name} ({current_value} -> {value})")
        
        if added_entities == 0:
            print("  ✓ All entity types already present")
        else:
            print(f"  ✓ Added {added_entities} new entity types")
        
        # Update relation types
        print("\nUpdating relation types...")
        added_relations = 0
        for name in SCHEMA_JSON["relation-type"].keys():
            if name not in existing_relations:
                cur.execute("INSERT INTO relation_types(name) VALUES (?);", (name,))
                print(f"  + Added relation type: {name}")
                added_relations += 1
        
        if added_relations == 0:
            print("  ✓ All relation types already present")
        else:
            print(f"  ✓ Added {added_relations} new relation types")
        
        # Show summary
        print("\n" + "="*60)
        print("Summary:")
        cur.execute("SELECT COUNT(*) FROM entity_types;")
        entity_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM relation_types;")
        relation_count = cur.fetchone()[0]
        print(f"  Total entity types in database: {entity_count}")
        print(f"  Total relation types in database: {relation_count}")
        print("="*60)
        
        conn.commit()
        print("\n✅ Schema types update completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Schema types update failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    update_schema_types()
