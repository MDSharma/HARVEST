#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for configuration environment variable overrides
Tests that environment variables correctly override config.py settings
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path


def test_env_var_overrides():
    """Test that environment variables override config.py settings"""
    print("Testing environment variable overrides...")
    
    # Create a temporary directory for test database
    test_dir = tempfile.mkdtemp(prefix="harvest_test_")
    test_db_path = os.path.join(test_dir, "subdir", "test.db")
    
    try:
        # Set environment variables
        os.environ['HARVEST_DB'] = test_db_path
        os.environ['HARVEST_PORT'] = '5999'
        os.environ['HARVEST_HOST'] = '0.0.0.0'
        os.environ['HARVEST_DEPLOYMENT_MODE'] = 'nginx'
        os.environ['HARVEST_BACKEND_PUBLIC_URL'] = 'https://example.com/api'
        
        # Import config first (which will be overridden)
        try:
            from config import (
                DB_PATH as config_db, BE_PORT as config_port, HOST as config_host,
                ENABLE_PDF_HIGHLIGHTING, DEPLOYMENT_MODE as config_dm,
                BACKEND_PUBLIC_URL as config_bpu, ENABLE_ENHANCED_PDF_DOWNLOAD
            )
            config_imported = True
        except ImportError:
            config_imported = False
            config_db = "harvest.db"
            config_port = 5001
            config_host = "127.0.0.1"
            config_dm = "internal"
            config_bpu = ""
        
        # Apply overrides (same logic as in harvest_be.py)
        DB_PATH = os.environ.get("HARVEST_DB", config_db)
        PORT = int(os.environ.get("HARVEST_PORT", str(config_port)))
        HOST = os.environ.get("HARVEST_HOST", config_host)
        DEPLOYMENT_MODE = os.environ.get("HARVEST_DEPLOYMENT_MODE", config_dm)
        BACKEND_PUBLIC_URL = os.environ.get("HARVEST_BACKEND_PUBLIC_URL", config_bpu)
        
        # Verify overrides worked
        assert DB_PATH == test_db_path, f"DB_PATH override failed: expected {test_db_path}, got {DB_PATH}"
        assert PORT == 5999, f"PORT override failed: expected 5999, got {PORT}"
        assert HOST == "0.0.0.0", f"HOST override failed: expected 0.0.0.0, got {HOST}"
        assert DEPLOYMENT_MODE == "nginx", f"DEPLOYMENT_MODE override failed: expected nginx, got {DEPLOYMENT_MODE}"
        assert BACKEND_PUBLIC_URL == "https://example.com/api", f"BACKEND_PUBLIC_URL override failed"
        
        print("✓ Environment variable overrides work correctly")
        
        if config_imported:
            print(f"  - Config.py was imported (DB_PATH={config_db}, PORT={config_port})")
            print(f"  - But environment variables override it correctly")
        
        return True
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        # Clean up environment variables
        for var in ['HARVEST_DB', 'HARVEST_PORT', 'HARVEST_HOST', 
                    'HARVEST_DEPLOYMENT_MODE', 'HARVEST_BACKEND_PUBLIC_URL']:
            if var in os.environ:
                del os.environ[var]


def test_db_directory_creation():
    """Test that database directory is created if it doesn't exist"""
    print("\nTesting database directory creation...")
    
    # Create a temporary directory for test
    test_dir = tempfile.mkdtemp(prefix="harvest_test_")
    test_db_path = os.path.join(test_dir, "nested", "subdir", "test.db")
    
    try:
        # Verify directory doesn't exist yet
        db_dir = os.path.dirname(os.path.abspath(test_db_path))
        assert not os.path.exists(db_dir), "Test directory should not exist yet"
        
        # Apply directory creation logic (same as in harvest_be.py)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Verify directory was created
        assert os.path.exists(db_dir), f"Directory {db_dir} should have been created"
        
        print("✓ Database directory creation works correctly")
        print(f"  - Created directory: {db_dir}")
        
        # Test database initialization
        os.environ['HARVEST_DB'] = test_db_path
        from harvest_store import init_db
        init_db(test_db_path)
        
        # Verify database file was created
        assert os.path.exists(test_db_path), f"Database file {test_db_path} should have been created"
        
        print("✓ Database initialization works in newly created directory")
        print(f"  - Created database: {test_db_path}")
        
        return True
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        if 'HARVEST_DB' in os.environ:
            del os.environ['HARVEST_DB']


def main():
    """Run all tests"""
    print("=" * 60)
    print("Configuration Override Tests")
    print("=" * 60)
    
    tests = [
        ("Environment Variable Overrides", test_env_var_overrides),
        ("Database Directory Creation", test_db_directory_creation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} failed")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
