"""
Test for PDF download stale detection and recovery.
Tests the new is_download_stale and reset_stale_download functions.
"""
import unittest
import sys
import os
import tempfile
import time

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from harvest_store import (
    init_pdf_download_progress,
    get_pdf_download_progress,
    update_pdf_download_progress,
    is_download_stale,
    reset_stale_download
)


class TestPDFDownloadStaleDetection(unittest.TestCase):
    """Test PDF download stale detection and recovery"""
    
    def setUp(self):
        """Set up test environment with temporary database"""
        # Create a temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        # Initialize database schema
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Create the pdf_download_progress table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pdf_download_progress (
                project_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                total INTEGER NOT NULL,
                current INTEGER DEFAULT 0,
                current_doi TEXT DEFAULT '',
                downloaded TEXT DEFAULT '[]',
                needs_upload TEXT DEFAULT '[]',
                errors TEXT DEFAULT '[]',
                project_dir TEXT,
                start_time REAL,
                end_time REAL,
                updated_at REAL
            )
        """)
        
        conn.commit()
        conn.close()
        
        self.project_id = 123
        self.project_dir = "/tmp/test_project"
    
    def tearDown(self):
        """Clean up temporary database"""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_init_download_progress(self):
        """Test initializing download progress"""
        success = init_pdf_download_progress(
            self.db_path, self.project_id, 10, self.project_dir
        )
        self.assertTrue(success)
        
        # Verify the progress was initialized
        progress = get_pdf_download_progress(self.db_path, self.project_id)
        self.assertIsNotNone(progress)
        self.assertEqual(progress['status'], 'running')
        self.assertEqual(progress['total'], 10)
        self.assertEqual(progress['current'], 0)
    
    def test_not_stale_when_recently_updated(self):
        """Test that recently updated downloads are not considered stale"""
        # Initialize a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        
        # Check immediately - should not be stale
        is_stale = is_download_stale(self.db_path, self.project_id, stale_threshold_seconds=300)
        self.assertFalse(is_stale, "Recently started download should not be stale")
    
    def test_stale_when_not_updated(self):
        """Test that downloads without recent updates are considered stale"""
        # Initialize a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        
        # Manually set updated_at to 10 minutes ago
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        old_time = time.time() - 600  # 10 minutes ago
        cur.execute(
            "UPDATE pdf_download_progress SET updated_at = ? WHERE project_id = ?",
            (old_time, self.project_id)
        )
        conn.commit()
        conn.close()
        
        # Check with 5 minute threshold - should be stale
        is_stale = is_download_stale(self.db_path, self.project_id, stale_threshold_seconds=300)
        self.assertTrue(is_stale, "Download not updated for 10 minutes should be stale")
    
    def test_not_stale_when_completed(self):
        """Test that completed downloads are not considered stale"""
        # Initialize and complete a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        update_pdf_download_progress(self.db_path, self.project_id, {'status': 'completed'})
        
        # Set old updated_at
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        old_time = time.time() - 600
        cur.execute(
            "UPDATE pdf_download_progress SET updated_at = ? WHERE project_id = ?",
            (old_time, self.project_id)
        )
        conn.commit()
        conn.close()
        
        # Should not be stale because status is not 'running'
        is_stale = is_download_stale(self.db_path, self.project_id, stale_threshold_seconds=300)
        self.assertFalse(is_stale, "Completed download should not be stale")
    
    def test_reset_stale_download(self):
        """Test resetting a stale download"""
        # Initialize a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        
        # Verify it's running
        progress = get_pdf_download_progress(self.db_path, self.project_id)
        self.assertEqual(progress['status'], 'running')
        
        # Reset it
        success = reset_stale_download(self.db_path, self.project_id)
        self.assertTrue(success)
        
        # Verify status changed to 'interrupted'
        progress = get_pdf_download_progress(self.db_path, self.project_id)
        self.assertEqual(progress['status'], 'interrupted')
    
    def test_reset_nonexistent_download(self):
        """Test resetting a download that doesn't exist"""
        # Try to reset a download that was never started
        success = reset_stale_download(self.db_path, 999)
        self.assertFalse(success, "Resetting non-existent download should return False")
    
    def test_update_progress_updates_timestamp(self):
        """Test that updating progress updates the timestamp"""
        # Initialize a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        
        # Get initial timestamp
        progress1 = get_pdf_download_progress(self.db_path, self.project_id)
        time1 = progress1['updated_at']
        
        # Wait a bit
        time.sleep(0.1)
        
        # Update progress
        update_pdf_download_progress(self.db_path, self.project_id, {'current': 1})
        
        # Get new timestamp
        progress2 = get_pdf_download_progress(self.db_path, self.project_id)
        time2 = progress2['updated_at']
        
        # Timestamp should have increased
        self.assertGreater(time2, time1, "Updated timestamp should be more recent")
    
    def test_stale_threshold_configurable(self):
        """Test that stale threshold is configurable"""
        # Initialize a download
        init_pdf_download_progress(self.db_path, self.project_id, 10, self.project_dir)
        
        # Set updated_at to 2 minutes ago
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        old_time = time.time() - 120  # 2 minutes ago
        cur.execute(
            "UPDATE pdf_download_progress SET updated_at = ? WHERE project_id = ?",
            (old_time, self.project_id)
        )
        conn.commit()
        conn.close()
        
        # With 5 minute threshold - should not be stale
        is_stale_5min = is_download_stale(self.db_path, self.project_id, stale_threshold_seconds=300)
        self.assertFalse(is_stale_5min, "2 minutes old should not be stale with 5 minute threshold")
        
        # With 1 minute threshold - should be stale
        is_stale_1min = is_download_stale(self.db_path, self.project_id, stale_threshold_seconds=60)
        self.assertTrue(is_stale_1min, "2 minutes old should be stale with 1 minute threshold")
    
    def test_multiple_projects(self):
        """Test stale detection works correctly with multiple projects"""
        project1 = 101
        project2 = 102
        
        # Initialize two downloads
        init_pdf_download_progress(self.db_path, project1, 10, "/tmp/p1")
        init_pdf_download_progress(self.db_path, project2, 10, "/tmp/p2")
        
        # Make project1 stale
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        old_time = time.time() - 600
        cur.execute(
            "UPDATE pdf_download_progress SET updated_at = ? WHERE project_id = ?",
            (old_time, project1)
        )
        conn.commit()
        conn.close()
        
        # Check both
        is_stale_1 = is_download_stale(self.db_path, project1, stale_threshold_seconds=300)
        is_stale_2 = is_download_stale(self.db_path, project2, stale_threshold_seconds=300)
        
        self.assertTrue(is_stale_1, "Project 1 should be stale")
        self.assertFalse(is_stale_2, "Project 2 should not be stale")


if __name__ == '__main__':
    unittest.main()
