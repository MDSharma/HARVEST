#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify that update_schema_types.py correctly updates
an old database with new schema types.
"""

import os
import sys
import sqlite3
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from harvest_store import SCHEMA_JSON, init_db, fetch_entity_dropdown_options, fetch_relation_dropdown_options


def test_schema_update():
    """Test that update_schema_types.py correctly updates old databases."""
    print("=" * 70)
    print("Testing Schema Update Script")
    print("=" * 70)
    
    test_db = "test_update_schema.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Test 1: Create a new database with full schema
    print("\n1. Creating fresh database with full schema...")
    init_db(test_db)
    
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    
    # Get current counts
    cur.execute("SELECT COUNT(*) FROM entity_types;")
    original_entity_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM relation_types;")
    original_relation_count = cur.fetchone()[0]
    
    print(f"   Initial entity types: {original_entity_count}")
    print(f"   Initial relation types: {original_relation_count}")
    
    # Test 2: Simulate an old database by removing some types
    print("\n2. Simulating old database by removing some types...")
    
    # Remove some entity types
    cur.execute('DELETE FROM entity_types WHERE name IN ("Metabolite", "Coordinates", "Pathway", "Process", "Factor");')
    removed_entities = cur.rowcount
    
    # Remove some relation types
    cur.execute('DELETE FROM relation_types WHERE name IN ("may_influence", "may_not_influence", "contributes_to", "inhers_in", "encodes", "binds_to", "phosphorylates");')
    removed_relations = cur.rowcount
    
    conn.commit()
    
    # Get counts after removal
    cur.execute("SELECT COUNT(*) FROM entity_types;")
    old_entity_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM relation_types;")
    old_relation_count = cur.fetchone()[0]
    
    conn.close()
    
    print(f"   Removed {removed_entities} entity types")
    print(f"   Removed {removed_relations} relation types")
    print(f"   Old database entity types: {old_entity_count}")
    print(f"   Old database relation types: {old_relation_count}")
    
    # Test 3: Run the update script
    print("\n3. Running update_schema_types.py script...")
    
    # Run the update script
    env = os.environ.copy()
    env['HARVEST_DB'] = test_db
    
    result = subprocess.run(
        [sys.executable, 'update_schema_types.py'],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    )
    
    if result.returncode != 0:
        print(f"   ❌ Update script failed!")
        print(f"   stdout: {result.stdout}")
        print(f"   stderr: {result.stderr}")
        return False
    
    print("   ✅ Update script ran successfully")
    
    # Test 4: Verify the database is now up to date
    print("\n4. Verifying updated database...")
    
    conn = sqlite3.connect(test_db)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM entity_types;")
    updated_entity_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM relation_types;")
    updated_relation_count = cur.fetchone()[0]
    
    conn.close()
    
    print(f"   Updated entity types: {updated_entity_count}")
    print(f"   Updated relation types: {updated_relation_count}")
    
    # Verify counts match original
    entities_restored = (updated_entity_count == original_entity_count)
    relations_restored = (updated_relation_count == original_relation_count)
    
    if entities_restored:
        print(f"   ✅ All entity types restored ({updated_entity_count}/{original_entity_count})")
    else:
        print(f"   ❌ Entity types not fully restored ({updated_entity_count}/{original_entity_count})")
    
    if relations_restored:
        print(f"   ✅ All relation types restored ({updated_relation_count}/{original_relation_count})")
    else:
        print(f"   ❌ Relation types not fully restored ({updated_relation_count}/{original_relation_count})")
    
    # Test 5: Verify specific types were added back
    print("\n5. Verifying specific types were added back...")
    
    entity_opts = set(fetch_entity_dropdown_options(test_db))
    relation_opts = set(fetch_relation_dropdown_options(test_db))
    
    expected_entities = {"Metabolite", "Coordinates", "Pathway", "Process", "Factor"}
    expected_relations = {"may_influence", "may_not_influence", "contributes_to", "inhers_in", "encodes", "binds_to", "phosphorylates"}
    
    entities_present = expected_entities.issubset(entity_opts)
    relations_present = expected_relations.issubset(relation_opts)
    
    if entities_present:
        print(f"   ✅ All expected entity types present")
    else:
        missing = expected_entities - entity_opts
        print(f"   ❌ Missing entity types: {missing}")
    
    if relations_present:
        print(f"   ✅ All expected relation types present")
    else:
        missing = expected_relations - relation_opts
        print(f"   ❌ Missing relation types: {missing}")
    
    # Clean up test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Summary
    print("\n" + "=" * 70)
    success = entities_restored and relations_restored and entities_present and relations_present
    if success:
        print("✅ ALL TESTS PASSED - Update script works correctly!")
    else:
        print("❌ SOME TESTS FAILED - Update script has issues")
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    success = test_schema_update()
    sys.exit(0 if success else 1)
