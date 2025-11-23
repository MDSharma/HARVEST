#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for HARVEST directory initialization.
Tests that required directories are created at application startup.
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from init_directories import (
    ensure_directory_exists,
    init_harvest_directories,
    check_directory_permissions
)


class TestDirectoryInitialization(unittest.TestCase):
    """Test directory initialization functions"""
    
    def setUp(self):
        """Create a temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp(prefix="harvest_test_")
    
    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_ensure_directory_exists_creates_new_directory(self):
        """Test that ensure_directory_exists creates a new directory"""
        test_path = os.path.join(self.test_dir, "new_dir")
        
        success, message = ensure_directory_exists(test_path, "test directory")
        
        self.assertTrue(success)
        self.assertTrue(os.path.isdir(test_path))
        self.assertIn("Created directory", message)
    
    def test_ensure_directory_exists_handles_existing_directory(self):
        """Test that ensure_directory_exists handles existing directories"""
        test_path = os.path.join(self.test_dir, "existing_dir")
        os.makedirs(test_path)
        
        success, message = ensure_directory_exists(test_path, "test directory")
        
        self.assertTrue(success)
        self.assertTrue(os.path.isdir(test_path))
        self.assertIn("already exists", message)
    
    def test_ensure_directory_exists_creates_nested_directories(self):
        """Test that ensure_directory_exists creates nested directories"""
        test_path = os.path.join(self.test_dir, "parent", "child", "grandchild")
        
        success, message = ensure_directory_exists(test_path, "nested directory")
        
        self.assertTrue(success)
        self.assertTrue(os.path.isdir(test_path))
        self.assertIn("Created directory", message)
    
    def test_ensure_directory_exists_handles_file_conflict(self):
        """Test that ensure_directory_exists handles existing file with same name"""
        test_path = os.path.join(self.test_dir, "conflict")
        # Create a file instead of directory
        with open(test_path, 'w') as f:
            f.write("test")
        
        success, message = ensure_directory_exists(test_path, "test directory")
        
        self.assertFalse(success)
        self.assertIn("not a directory", message)
    
    def test_init_harvest_directories_creates_all_required_dirs(self):
        """Test that init_harvest_directories creates all required directories"""
        success, messages = init_harvest_directories(base_dir=self.test_dir)
        
        self.assertTrue(success)
        self.assertEqual(len(messages), 2)  # .cache/huggingface and project_pdfs
        
        # Check that directories were created
        cache_dir = os.path.join(self.test_dir, ".cache", "huggingface")
        pdf_dir = os.path.join(self.test_dir, "project_pdfs")
        
        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(os.path.isdir(pdf_dir))
    
    def test_init_harvest_directories_handles_existing_dirs(self):
        """Test that init_harvest_directories handles existing directories gracefully"""
        # Pre-create directories
        cache_dir = os.path.join(self.test_dir, ".cache", "huggingface")
        pdf_dir = os.path.join(self.test_dir, "project_pdfs")
        os.makedirs(cache_dir)
        os.makedirs(pdf_dir)
        
        success, messages = init_harvest_directories(base_dir=self.test_dir)
        
        self.assertTrue(success)
        self.assertEqual(len(messages), 2)
        
        # Verify directories still exist
        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(os.path.isdir(pdf_dir))
    
    def test_check_directory_permissions_writable(self):
        """Test that check_directory_permissions correctly identifies writable directories"""
        test_path = os.path.join(self.test_dir, "writable")
        os.makedirs(test_path)
        
        is_writable, message = check_directory_permissions(test_path)
        
        self.assertTrue(is_writable)
        self.assertIn("writable", message.lower())
    
    def test_check_directory_permissions_nonexistent(self):
        """Test that check_directory_permissions handles non-existent directories"""
        test_path = os.path.join(self.test_dir, "nonexistent")
        
        is_writable, message = check_directory_permissions(test_path)
        
        self.assertFalse(is_writable)
        self.assertIn("does not exist", message)
    
    def test_check_directory_permissions_file_not_directory(self):
        """Test that check_directory_permissions rejects files"""
        test_path = os.path.join(self.test_dir, "file")
        with open(test_path, 'w') as f:
            f.write("test")
        
        is_writable, message = check_directory_permissions(test_path)
        
        self.assertFalse(is_writable)
        self.assertIn("not a directory", message)


class TestDirectoryInitializationIntegration(unittest.TestCase):
    """Integration tests for directory initialization with actual HARVEST directories"""
    
    def test_harvest_directories_exist_after_import(self):
        """Test that HARVEST directories exist after initialization"""
        # Get the repository root
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Expected directories
        cache_dir = os.path.join(repo_root, ".cache", "huggingface")
        pdf_dir = os.path.join(repo_root, "project_pdfs")
        
        # Run initialization
        success, messages = init_harvest_directories(base_dir=repo_root)
        
        # Verify success
        self.assertTrue(success, f"Initialization failed: {messages}")
        
        # Verify directories exist
        self.assertTrue(os.path.isdir(cache_dir), f"Cache directory not found: {cache_dir}")
        self.assertTrue(os.path.isdir(pdf_dir), f"PDF directory not found: {pdf_dir}")
        
        # Verify directories are writable
        cache_writable, cache_msg = check_directory_permissions(cache_dir)
        pdf_writable, pdf_msg = check_directory_permissions(pdf_dir)
        
        self.assertTrue(cache_writable, f"Cache directory not writable: {cache_msg}")
        self.assertTrue(pdf_writable, f"PDF directory not writable: {pdf_msg}")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryInitializationIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code based on results
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
