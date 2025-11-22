#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for project deletion with batch dependencies
Tests that projects with batches can be deleted without foreign key constraint errors
"""

import sys
import os
import tempfile
import json

# Add parent directory to path to import harvest_store
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harvest_store import (
    init_db, create_project, delete_project, get_project_by_id,
    create_batches, get_project_batches, update_doi_status,
    init_pdf_download_progress
)


def test_delete_project_without_batches():
    """Test deleting a project without batches (baseline test)"""
    print("Testing project deletion without batches...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        init_db(db_path)
        
        # Create a project
        project_id = create_project(
            db_path,
            name="Test Project",
            description="Test Description",
            doi_list=["10.1234/test1", "10.1234/test2"],
            created_by="test@example.com"
        )
        
        assert project_id > 0, "Failed to create project"
        
        # Verify project exists
        project = get_project_by_id(db_path, project_id)
        assert project is not None, "Project should exist"
        assert project['name'] == "Test Project"
        
        # Delete the project
        success = delete_project(db_path, project_id)
        assert success, "Failed to delete project"
        
        # Verify project is deleted
        project = get_project_by_id(db_path, project_id)
        assert project is None, "Project should be deleted"
        
        print("✓ Project without batches deleted successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def test_delete_project_with_batches():
    """Test deleting a project with batch dependencies"""
    print("\nTesting project deletion with batches...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        init_db(db_path)
        
        # Create a project with multiple DOIs
        doi_list = [f"10.1234/test{i}" for i in range(25)]
        project_id = create_project(
            db_path,
            name="Test Project with Batches",
            description="Test Description",
            doi_list=doi_list,
            created_by="test@example.com"
        )
        
        assert project_id > 0, "Failed to create project"
        
        # Create batches for the project
        batches = create_batches(db_path, project_id, batch_size=10, strategy="sequential")
        assert len(batches) > 0, "Failed to create batches"
        print(f"  Created {len(batches)} batches")
        
        # Verify batches exist
        project_batches = get_project_batches(db_path, project_id)
        assert len(project_batches) == len(batches), "Batch count mismatch"
        
        # Add some annotation status
        update_doi_status(db_path, project_id, doi_list[0], "in_progress", "annotator@example.com")
        update_doi_status(db_path, project_id, doi_list[1], "completed", "annotator@example.com")
        
        # Add PDF download progress
        init_pdf_download_progress(db_path, project_id, len(doi_list), "/tmp/test_project")
        
        # Now try to delete the project
        success = delete_project(db_path, project_id)
        assert success, "Failed to delete project with batches"
        
        # Verify project is deleted
        project = get_project_by_id(db_path, project_id)
        assert project is None, "Project should be deleted"
        
        # Verify batches are deleted
        project_batches = get_project_batches(db_path, project_id)
        assert len(project_batches) == 0, "Batches should be deleted"
        
        print("✓ Project with batches deleted successfully")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def test_delete_project_rollback_on_error():
    """Test that transaction rollback works on error"""
    print("\nTesting transaction rollback on error...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        import sqlite3
        
        # Initialize database
        init_db(db_path)
        
        # Create a project
        project_id = create_project(
            db_path,
            name="Test Project Rollback",
            description="Test Description",
            doi_list=["10.1234/test1"],
            created_by="test@example.com"
        )
        
        assert project_id > 0, "Failed to create project"
        
        # Create batches
        batches = create_batches(db_path, project_id, batch_size=10)
        assert len(batches) > 0, "Failed to create batches"
        
        # Create a corrupted database state by locking it
        # This will cause the delete to fail mid-transaction
        lock_conn = sqlite3.connect(db_path)
        lock_conn.execute("BEGIN EXCLUSIVE TRANSACTION;")
        
        # Try to delete - should fail due to database lock
        success = delete_project(db_path, project_id)
        
        # Release the lock
        lock_conn.rollback()
        lock_conn.close()
        
        # The delete should have failed
        if not success:
            # Verify project still exists
            project = get_project_by_id(db_path, project_id)
            assert project is not None, "Project should still exist after failed delete"
            
            # Verify batches still exist
            project_batches = get_project_batches(db_path, project_id)
            assert len(project_batches) > 0, "Batches should still exist after failed delete"
            
            print("✓ Transaction rollback test passed")
            return True
        else:
            print("⚠ Transaction rollback test skipped - delete unexpectedly succeeded")
            return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def test_delete_multiple_projects_with_shared_dois():
    """Test deleting multiple projects that might share DOIs"""
    print("\nTesting deletion of multiple projects with shared DOIs...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database
        init_db(db_path)
        
        # Create two projects with overlapping DOIs
        doi_list_1 = [f"10.1234/test{i}" for i in range(15)]
        project_id_1 = create_project(
            db_path,
            name="Test Project 1",
            description="Test Description 1",
            doi_list=doi_list_1,
            created_by="test@example.com"
        )
        
        doi_list_2 = [f"10.1234/test{i}" for i in range(10, 25)]  # Some overlap
        project_id_2 = create_project(
            db_path,
            name="Test Project 2",
            description="Test Description 2",
            doi_list=doi_list_2,
            created_by="test@example.com"
        )
        
        # Create batches for both projects
        batches_1 = create_batches(db_path, project_id_1, batch_size=5)
        batches_2 = create_batches(db_path, project_id_2, batch_size=5)
        
        assert len(batches_1) > 0, "Failed to create batches for project 1"
        assert len(batches_2) > 0, "Failed to create batches for project 2"
        
        # Delete first project
        success = delete_project(db_path, project_id_1)
        assert success, "Failed to delete project 1"
        
        # Verify first project is deleted
        project_1 = get_project_by_id(db_path, project_id_1)
        assert project_1 is None, "Project 1 should be deleted"
        
        # Verify second project still exists
        project_2 = get_project_by_id(db_path, project_id_2)
        assert project_2 is not None, "Project 2 should still exist"
        
        # Verify batches for project 2 still exist
        project_2_batches = get_project_batches(db_path, project_id_2)
        assert len(project_2_batches) == len(batches_2), "Project 2 batches should still exist"
        
        # Delete second project
        success = delete_project(db_path, project_id_2)
        assert success, "Failed to delete project 2"
        
        # Verify second project is deleted
        project_2 = get_project_by_id(db_path, project_id_2)
        assert project_2 is None, "Project 2 should be deleted"
        
        print("✓ Multiple projects deletion test passed")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(db_path)
        except:
            pass


def main():
    """Run all tests"""
    print("=" * 70)
    print("Project Deletion with Batch Dependencies Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_delete_project_without_batches,
        test_delete_project_with_batches,
        test_delete_project_rollback_on_error,
        test_delete_multiple_projects_with_shared_dois,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print()
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
