#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify that schema types are properly synchronized between
backend code, database, and frontend.
"""

import os
import sys
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from harvest_store import SCHEMA_JSON, init_db, fetch_entity_dropdown_options, fetch_relation_dropdown_options

# Frontend schema for comparison
FRONTEND_SCHEMA_JSON = {
    "span-attribute": {
        "Gene": "gene",
        "Regulator": "regulator",
        "Variant": "variant",
        "Protein": "protein",
        "Trait": "phenotype",
        "Enzyme": "enzyme",
        "QTL": "qtl",
        "Coordinates": "coordinates",
        "Metabolite": "metabolite",
        "Pathway": "pathway",
        "Process": "process",
        "Factor": "factor",
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
        "inhers_in": "inhers_in",
        "encodes": "encodes",
        "binds_to": "binds_to",
        "phosphorylates": "phosphorylates",
        "methylates": "methylates",
        "acetylates": "acetylates",
        "activates": "activates",
        "inhibits": "inhibits",
        "represses": "represses",
        "interacts_with": "interacts_with",
        "localizes_to": "localizes_to",
        "expressed_in": "expressed_in",
        "associated_with": "associated_with",
        "causes": "causes",
        "prevents": "prevents",
        "co_occurs_with": "co_occurs_with",
        "precedes": "precedes",
        "follows": "follows",
    },
}


def test_schema_sync():
    """Test that backend and frontend schemas are synchronized."""
    print("=" * 70)
    print("Testing Schema Synchronization")
    print("=" * 70)
    
    # Test 1: Backend schema matches frontend schema
    print("\n1. Comparing backend and frontend SCHEMA_JSON...")
    
    backend_entities = set(SCHEMA_JSON["span-attribute"].keys())
    frontend_entities = set(FRONTEND_SCHEMA_JSON["span-attribute"].keys())
    
    backend_relations = set(SCHEMA_JSON["relation-type"].keys())
    frontend_relations = set(FRONTEND_SCHEMA_JSON["relation-type"].keys())
    
    entities_match = backend_entities == frontend_entities
    relations_match = backend_relations == frontend_relations
    
    if entities_match:
        print(f"   ✅ Entity types match ({len(backend_entities)} types)")
    else:
        print(f"   ❌ Entity types mismatch!")
        missing_in_backend = frontend_entities - backend_entities
        extra_in_backend = backend_entities - frontend_entities
        if missing_in_backend:
            print(f"      Missing in backend: {missing_in_backend}")
        if extra_in_backend:
            print(f"      Extra in backend: {extra_in_backend}")
    
    if relations_match:
        print(f"   ✅ Relation types match ({len(backend_relations)} types)")
    else:
        print(f"   ❌ Relation types mismatch!")
        missing_in_backend = frontend_relations - backend_relations
        extra_in_backend = backend_relations - frontend_relations
        if missing_in_backend:
            print(f"      Missing in backend: {missing_in_backend}")
        if extra_in_backend:
            print(f"      Extra in backend: {extra_in_backend}")
    
    # Test 2: Database initialization populates all types
    print("\n2. Testing database initialization...")
    test_db = "test_schema_sync.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Initialize database
    init_db(test_db)
    
    # Fetch from database
    db_entities = set(fetch_entity_dropdown_options(test_db))
    db_relations = set(fetch_relation_dropdown_options(test_db))
    
    db_entities_match = db_entities == backend_entities
    db_relations_match = db_relations == backend_relations
    
    if db_entities_match:
        print(f"   ✅ Database has all entity types ({len(db_entities)} types)")
    else:
        print(f"   ❌ Database entity types mismatch!")
        missing_in_db = backend_entities - db_entities
        extra_in_db = db_entities - backend_entities
        if missing_in_db:
            print(f"      Missing in database: {missing_in_db}")
        if extra_in_db:
            print(f"      Extra in database: {extra_in_db}")
    
    if db_relations_match:
        print(f"   ✅ Database has all relation types ({len(db_relations)} types)")
    else:
        print(f"   ❌ Database relation types mismatch!")
        missing_in_db = backend_relations - db_relations
        extra_in_db = db_relations - backend_relations
        if missing_in_db:
            print(f"      Missing in database: {missing_in_db}")
        if extra_in_db:
            print(f"      Extra in database: {extra_in_db}")
    
    # Clean up test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Test 3: Print complete schema
    print("\n3. Complete Schema:")
    print(f"\n   Entity Types ({len(backend_entities)}):")
    for entity in sorted(backend_entities):
        print(f"      - {entity}")
    
    print(f"\n   Relation Types ({len(backend_relations)}):")
    for relation in sorted(backend_relations):
        print(f"      - {relation}")
    
    # Summary
    print("\n" + "=" * 70)
    if entities_match and relations_match and db_entities_match and db_relations_match:
        print("✅ ALL TESTS PASSED - Schema is properly synchronized!")
    else:
        print("❌ SOME TESTS FAILED - Schema synchronization issues detected")
    print("=" * 70)
    
    return entities_match and relations_match and db_entities_match and db_relations_match


if __name__ == "__main__":
    success = test_schema_sync()
    sys.exit(0 if success else 1)
