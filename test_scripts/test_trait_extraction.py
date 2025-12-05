#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Basic tests for trait extraction functionality

Run with: python test_scripts/test_trait_extraction.py
"""

import os
import sys
import tempfile
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_migration():
    """Test that migration creates required tables"""
    print("Testing database migration...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    try:
        # Initialize base database
        from harvest_store import init_db
        init_db(test_db)
        
        # Run migration
        from migrate_trait_extraction import migrate_trait_extraction
        migrate_trait_extraction(test_db)
        
        # Check tables exist
        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trait_documents';")
        assert cur.fetchone() is not None, "trait_documents table not created"
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trait_extraction_jobs';")
        assert cur.fetchone() is not None, "trait_extraction_jobs table not created"
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trait_model_configs';")
        assert cur.fetchone() is not None, "trait_model_configs table not created"
        
        # Check triples table has new columns
        cur.execute("PRAGMA table_info(triples);")
        columns = {row[1] for row in cur.fetchall()}
        
        required_columns = ['model_profile', 'confidence', 'status', 'trait_name', 
                          'trait_value', 'unit', 'job_id', 'document_id']
        for col in required_columns:
            assert col in columns, f"Column {col} not added to triples table"
        
        conn.close()
        print("✓ Database migration test passed")
        
    finally:
        if os.path.exists(test_db):
            os.unlink(test_db)


def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    from trait_extraction.config import TraitExtractionConfig
    
    config = TraitExtractionConfig()
    
    # Check defaults
    assert config.local_mode == True, "Default local_mode should be True"
    assert len(config.model_profiles) >= 4, "Should have at least 4 model profiles"
    
    # Check model profiles
    profiles = config.list_model_profiles()
    assert len(profiles) >= 4, "Should list at least 4 profiles"
    
    profile_ids = [p['id'] for p in profiles]
    assert 'spacy_bio' in profile_ids, "Should have spacy_bio profile"
    assert 'huggingface_ner' in profile_ids, "Should have huggingface_ner profile"
    assert 'lasuie' in profile_ids, "Should have lasuie profile"
    assert 'allennlp_srl' in profile_ids, "Should have allennlp_srl profile"
    
    print("✓ Configuration loading test passed")


def test_adapter_factory():
    """Test adapter factory"""
    print("Testing adapter factory...")
    
    from trait_extraction.adapters.factory import AdapterFactory
    from trait_extraction.config import TraitExtractionConfig
    
    config = TraitExtractionConfig()
    
    # Test creating spaCy adapter (doesn't require external models to import)
    spacy_config = config.get_model_profile('spacy_bio')
    adapter = AdapterFactory.create_adapter('spacy', spacy_config)
    
    assert adapter is not None, "Adapter creation failed"
    assert not adapter.is_loaded, "Adapter should not be loaded initially"
    
    # Check list_backends
    backends = AdapterFactory.list_backends()
    assert 'spacy' in backends, "spacy backend not listed"
    assert 'huggingface' in backends, "huggingface backend not listed"
    
    print("✓ Adapter factory test passed")


def test_store_operations():
    """Test database store operations"""
    print("Testing store operations...")
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        test_db = f.name
    
    try:
        # Initialize and migrate
        from harvest_store import init_db
        from migrate_trait_extraction import migrate_trait_extraction
        from trait_extraction.store import (
            create_document, get_document, list_documents,
            create_extraction_job, get_extraction_job, list_extraction_jobs
        )
        
        init_db(test_db)
        migrate_trait_extraction(test_db)
        
        # Test document operations
        doc_id = create_document(
            test_db,
            project_id=None,
            file_path="/tmp/test.pdf",
            text_content="This is a test document about genes and proteins."
        )
        
        assert doc_id > 0, "Document creation failed"
        
        doc = get_document(test_db, doc_id)
        assert doc is not None, "Document retrieval failed"
        assert doc['file_path'] == "/tmp/test.pdf", "Document path mismatch"
        
        docs, total = list_documents(test_db)
        assert total == 1, "Document listing failed"
        assert len(docs) == 1, "Document listing count mismatch"
        
        # Test job operations
        job_id = create_extraction_job(
            test_db,
            project_id=None,
            document_ids=[doc_id],
            model_profile="spacy_bio",
            mode="no_training"
        )
        
        assert job_id > 0, "Job creation failed"
        
        job = get_extraction_job(test_db, job_id)
        assert job is not None, "Job retrieval failed"
        assert job['model_profile'] == "spacy_bio", "Job profile mismatch"
        assert job['status'] == "pending", "Job status should be pending"
        
        jobs, total = list_extraction_jobs(test_db)
        assert total == 1, "Job listing failed"
        
        print("✓ Store operations test passed")
        
    finally:
        if os.path.exists(test_db):
            os.unlink(test_db)


def test_models():
    """Test data models"""
    print("Testing data models...")
    
    from trait_extraction.models import (
        Document, ExtractionJob, ExtractedTriple,
        JobStatus, ExtractionMode, TripleStatus
    )
    
    # Test Document
    doc = Document(
        id=1,
        file_path="/tmp/test.pdf",
        text_content="Test content"
    )
    doc_dict = doc.to_dict()
    assert doc_dict['id'] == 1, "Document dict conversion failed"
    
    # Test ExtractionJob
    job = ExtractionJob(
        id=1,
        document_ids=[1, 2],
        model_profile="spacy_bio",
        status=JobStatus.PENDING.value
    )
    job_dict = job.to_dict()
    assert job_dict['status'] == "pending", "Job dict conversion failed"
    
    # Test ExtractedTriple
    triple = ExtractedTriple(
        source_entity_name="Gene1",
        source_entity_attr="Gene",
        relation_type="encodes",
        sink_entity_name="Protein1",
        sink_entity_attr="Protein",
        confidence=0.9
    )
    triple_dict = triple.to_dict()
    assert triple_dict['confidence'] == 0.9, "Triple dict conversion failed"
    
    print("✓ Data models test passed")


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running trait extraction tests")
    print("=" * 60)
    print()
    
    tests = [
        test_config_loading,
        test_models,
        test_database_migration,
        test_store_operations,
        test_adapter_factory,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
            print()
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            print()
            failed += 1
    
    print("=" * 60)
    if failed == 0:
        print(f"All {len(tests)} tests passed! ✓")
    else:
        print(f"{failed}/{len(tests)} tests failed ✗")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
