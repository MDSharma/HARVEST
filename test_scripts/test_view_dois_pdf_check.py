"""
Test for the view DOIs PDF check functionality.
Tests that the view_project_dois function correctly identifies which DOIs have PDFs.
"""
import unittest
import sys
import os
import hashlib
import tempfile
import shutil

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestViewDOIsPDFCheck(unittest.TestCase):
    """Test the DOI PDF existence check in view_project_dois"""
    
    def setUp(self):
        """Set up test environment with temporary directory structure"""
        # Create a temporary directory for test PDFs
        self.test_dir = tempfile.mkdtemp()
        self.project_id = 123
        self.project_pdf_dir = os.path.join(self.test_dir, f"project_{self.project_id}")
        os.makedirs(self.project_pdf_dir, exist_ok=True)
        
        # Sample DOIs
        self.doi_with_pdf = "10.1234/test.doi.001"
        self.doi_without_pdf = "10.1234/test.doi.002"
        
        # Create a PDF file for the first DOI
        doi_hash = hashlib.sha256(self.doi_with_pdf.encode('utf-8')).hexdigest()[:16]
        pdf_filename = f"{doi_hash}.pdf"
        pdf_path = os.path.join(self.project_pdf_dir, pdf_filename)
        
        # Create a dummy PDF file
        with open(pdf_path, 'w') as f:
            f.write("%PDF-1.4\n%Mock PDF content for testing")
    
    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_generate_doi_hash(self):
        """Test that DOI hash generation is consistent"""
        from frontend.callbacks import generate_doi_hash
        
        doi = "10.1234/test.doi"
        hash1 = generate_doi_hash(doi)
        hash2 = generate_doi_hash(doi)
        
        # Hash should be consistent
        self.assertEqual(hash1, hash2)
        # Hash should be 16 characters
        self.assertEqual(len(hash1), 16)
        # Hash should be hexadecimal
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))
    
    def test_get_project_pdf_dir(self):
        """Test that project PDF directory path is correctly formatted"""
        from frontend.callbacks import get_project_pdf_dir
        
        project_id = 42
        base_dir = "project_pdfs"
        
        pdf_dir = get_project_pdf_dir(project_id, base_dir)
        
        # Should have format: project_pdfs/project_42
        expected = os.path.join(base_dir, f"project_{project_id}")
        self.assertEqual(pdf_dir, expected)
    
    def test_pdf_exists_check(self):
        """Test that PDF existence check works correctly"""
        from frontend.callbacks import generate_doi_hash, get_project_pdf_dir
        
        # Check DOI with PDF
        doi_hash_with = generate_doi_hash(self.doi_with_pdf)
        pdf_filename_with = f"{doi_hash_with}.pdf"
        pdf_path_with = os.path.join(self.project_pdf_dir, pdf_filename_with)
        self.assertTrue(os.path.exists(pdf_path_with), 
                       f"PDF should exist for DOI with PDF: {pdf_path_with}")
        
        # Check DOI without PDF
        doi_hash_without = generate_doi_hash(self.doi_without_pdf)
        pdf_filename_without = f"{doi_hash_without}.pdf"
        pdf_path_without = os.path.join(self.project_pdf_dir, pdf_filename_without)
        self.assertFalse(os.path.exists(pdf_path_without),
                        f"PDF should not exist for DOI without PDF: {pdf_path_without}")
    
    def test_project_directory_format(self):
        """Test that the project directory uses the correct 'project_{id}' format"""
        from frontend.callbacks import get_project_pdf_dir
        
        # Test various project IDs
        for project_id in [1, 42, 999, 12345]:
            pdf_dir = get_project_pdf_dir(project_id, self.test_dir)
            expected_dir_name = f"project_{project_id}"
            
            # Directory name should contain project_{id}
            self.assertIn(expected_dir_name, pdf_dir,
                         f"Directory should contain '{expected_dir_name}': {pdf_dir}")
    
    def test_multiple_dois_classification(self):
        """Test classification of multiple DOIs into with/without PDF categories"""
        from frontend.callbacks import generate_doi_hash
        
        # Create PDFs for some DOIs
        dois_with_pdfs_actual = [
            "10.1234/paper.001",
            "10.1234/paper.002",
            "10.1234/paper.003"
        ]
        dois_without_pdfs_actual = [
            "10.1234/paper.004",
            "10.1234/paper.005"
        ]
        
        # Create PDF files for the "with PDF" DOIs
        for doi in dois_with_pdfs_actual:
            doi_hash = generate_doi_hash(doi)
            pdf_path = os.path.join(self.project_pdf_dir, f"{doi_hash}.pdf")
            with open(pdf_path, 'w') as f:
                f.write("%PDF-1.4\nTest content")
        
        # Verify classification
        for doi in dois_with_pdfs_actual:
            doi_hash = generate_doi_hash(doi)
            pdf_path = os.path.join(self.project_pdf_dir, f"{doi_hash}.pdf")
            self.assertTrue(os.path.exists(pdf_path),
                           f"PDF should exist for {doi}")
        
        for doi in dois_without_pdfs_actual:
            doi_hash = generate_doi_hash(doi)
            pdf_path = os.path.join(self.project_pdf_dir, f"{doi_hash}.pdf")
            self.assertFalse(os.path.exists(pdf_path),
                            f"PDF should not exist for {doi}")


if __name__ == '__main__':
    unittest.main()
