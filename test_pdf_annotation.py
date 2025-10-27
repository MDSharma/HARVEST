#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for PDF annotation functionality
Tests the pdf_annotator module functions
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Import the PDF annotator module
try:
    from pdf_annotator import (
        add_highlights_to_pdf,
        get_highlights_from_pdf,
        clear_all_highlights,
        validate_highlight_data,
        hex_to_rgb
    )
except ImportError as e:
    print(f"Error importing pdf_annotator: {e}")
    sys.exit(1)

# Try to import fitz to create a test PDF
try:
    import fitz
except ImportError:
    print("Error: PyMuPDF (fitz) not installed")
    sys.exit(1)


def create_test_pdf(filepath: str) -> bool:
    """Create a simple test PDF file"""
    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4 size
        
        # Add some text
        text = "This is a test PDF document for testing the highlighting feature."
        page.insert_text((50, 50), text, fontsize=14)
        
        text2 = "You can highlight any part of this text."
        page.insert_text((50, 100), text2, fontsize=14)
        
        text3 = "Highlights are saved directly into the PDF file."
        page.insert_text((50, 150), text3, fontsize=14)
        
        # Add a second page
        page2 = doc.new_page(width=595, height=842)
        page2.insert_text((50, 50), "This is page 2 of the test document.", fontsize=14)
        
        doc.save(filepath)
        doc.close()
        return True
    except Exception as e:
        print(f"Error creating test PDF: {e}")
        return False


def test_validation():
    """Test highlight validation"""
    print("\n" + "="*80)
    print("TEST: Highlight Validation")
    print("="*80)
    
    # Valid highlight
    valid_highlight = {
        'page': 0,
        'rects': [[100, 100, 200, 120]],
        'color': '#FFFF00'
    }
    is_valid, error = validate_highlight_data(valid_highlight)
    print(f"Valid highlight: {is_valid} (expected: True)")
    assert is_valid, f"Expected valid highlight to pass: {error}"
    
    # Invalid - missing field
    invalid_highlight = {
        'page': 0,
        'rects': [[100, 100, 200, 120]]
        # Missing 'color'
    }
    is_valid, error = validate_highlight_data(invalid_highlight)
    print(f"Missing field: {is_valid} (expected: False) - {error}")
    assert not is_valid, "Expected invalid highlight to fail"
    
    # Invalid - bad page number
    invalid_highlight = {
        'page': -1,
        'rects': [[100, 100, 200, 120]],
        'color': '#FFFF00'
    }
    is_valid, error = validate_highlight_data(invalid_highlight)
    print(f"Invalid page: {is_valid} (expected: False) - {error}")
    assert not is_valid, "Expected invalid page to fail"
    
    # Invalid - bad color
    invalid_highlight = {
        'page': 0,
        'rects': [[100, 100, 200, 120]],
        'color': 'not-a-color'
    }
    is_valid, error = validate_highlight_data(invalid_highlight)
    print(f"Invalid color: {is_valid} (expected: False) - {error}")
    assert not is_valid, "Expected invalid color to fail"
    
    print("✓ All validation tests passed")


def test_color_conversion():
    """Test hex to RGB conversion"""
    print("\n" + "="*80)
    print("TEST: Color Conversion")
    print("="*80)
    
    # Test full hex
    rgb = hex_to_rgb("#FFFF00")
    print(f"#FFFF00 -> {rgb} (expected: (1.0, 1.0, 0.0))")
    assert rgb == (1.0, 1.0, 0.0), f"Expected (1.0, 1.0, 0.0), got {rgb}"
    
    # Test shorthand hex
    rgb = hex_to_rgb("#F00")
    print(f"#F00 -> {rgb} (expected: (1.0, 0.0, 0.0))")
    assert rgb == (1.0, 0.0, 0.0), f"Expected (1.0, 0.0, 0.0), got {rgb}"
    
    # Test blue
    rgb = hex_to_rgb("#0000FF")
    print(f"#0000FF -> {rgb} (expected: (0.0, 0.0, 1.0))")
    assert rgb == (0.0, 0.0, 1.0), f"Expected (0.0, 0.0, 1.0), got {rgb}"
    
    print("✓ All color conversion tests passed")


def test_add_and_retrieve_highlights():
    """Test adding and retrieving highlights"""
    print("\n" + "="*80)
    print("TEST: Add and Retrieve Highlights")
    print("="*80)
    
    # Create temporary directory and test PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test.pdf")
        
        print(f"Creating test PDF: {pdf_path}")
        if not create_test_pdf(pdf_path):
            print("✗ Failed to create test PDF")
            return False
        
        # Define test highlights
        highlights = [
            {
                'page': 0,
                'rects': [[100, 40, 300, 60]],
                'color': '#FFFF00',
                'text': 'Yellow highlight on page 1'
            },
            {
                'page': 0,
                'rects': [[100, 90, 400, 110]],
                'color': '#00FF00',
                'text': 'Green highlight on page 1'
            },
            {
                'page': 1,
                'rects': [[100, 40, 350, 60]],
                'color': '#FF00FF',
                'text': 'Purple highlight on page 2'
            }
        ]
        
        # Add highlights
        print(f"\nAdding {len(highlights)} highlights...")
        success, message = add_highlights_to_pdf(pdf_path, highlights)
        print(f"Add result: {success} - {message}")
        assert success, f"Failed to add highlights: {message}"
        
        # Retrieve highlights
        print("\nRetrieving highlights...")
        success, retrieved_highlights, message = get_highlights_from_pdf(pdf_path)
        print(f"Retrieve result: {success} - {message}")
        assert success, f"Failed to retrieve highlights: {message}"
        
        print(f"Retrieved {len(retrieved_highlights)} highlights")
        print(f"Expected {len(highlights)} highlights")
        
        # Verify count
        assert len(retrieved_highlights) == len(highlights), \
            f"Expected {len(highlights)} highlights, got {len(retrieved_highlights)}"
        
        # Verify each highlight
        for i, highlight in enumerate(retrieved_highlights):
            print(f"\nHighlight {i+1}:")
            print(f"  Page: {highlight['page']}")
            print(f"  Rects: {highlight['rects']}")
            print(f"  Color: {highlight['color']}")
            if 'text' in highlight:
                print(f"  Text: {highlight['text']}")
        
        print("\n✓ Add and retrieve tests passed")
        return True


def test_clear_highlights():
    """Test clearing all highlights"""
    print("\n" + "="*80)
    print("TEST: Clear All Highlights")
    print("="*80)
    
    # Create temporary directory and test PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test.pdf")
        
        print(f"Creating test PDF: {pdf_path}")
        if not create_test_pdf(pdf_path):
            print("✗ Failed to create test PDF")
            return False
        
        # Add some highlights
        highlights = [
            {
                'page': 0,
                'rects': [[100, 40, 300, 60]],
                'color': '#FFFF00'
            },
            {
                'page': 0,
                'rects': [[100, 90, 400, 110]],
                'color': '#00FF00'
            }
        ]
        
        print(f"\nAdding {len(highlights)} highlights...")
        success, message = add_highlights_to_pdf(pdf_path, highlights)
        assert success, f"Failed to add highlights: {message}"
        
        # Verify they exist
        success, retrieved, message = get_highlights_from_pdf(pdf_path)
        assert success and len(retrieved) == len(highlights), \
            f"Expected {len(highlights)} highlights, got {len(retrieved)}"
        
        # Clear all highlights
        print("\nClearing all highlights...")
        success, message = clear_all_highlights(pdf_path)
        print(f"Clear result: {success} - {message}")
        assert success, f"Failed to clear highlights: {message}"
        
        # Verify they're gone
        success, retrieved, message = get_highlights_from_pdf(pdf_path)
        print(f"After clear: {len(retrieved)} highlights (expected: 0)")
        assert success and len(retrieved) == 0, \
            f"Expected 0 highlights after clear, got {len(retrieved)}"
        
        print("✓ Clear highlights test passed")
        return True


def test_security_limits():
    """Test security limits"""
    print("\n" + "="*80)
    print("TEST: Security Limits")
    print("="*80)
    
    # Create temporary directory and test PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "test.pdf")
        
        if not create_test_pdf(pdf_path):
            print("✗ Failed to create test PDF")
            return False
        
        # Test: Too many highlights
        print("\nTesting highlight limit...")
        too_many_highlights = [
            {
                'page': 0,
                'rects': [[100, 40 + i*20, 300, 60 + i*20]],
                'color': '#FFFF00'
            }
            for i in range(51)  # More than MAX_HIGHLIGHTS_PER_REQUEST (50)
        ]
        
        success, message = add_highlights_to_pdf(pdf_path, too_many_highlights)
        print(f"Too many highlights: {success} (expected: False) - {message}")
        assert not success, "Expected failure for too many highlights"
        assert "Too many highlights" in message, f"Expected 'Too many highlights' error, got: {message}"
        
        # Test: Invalid page number
        print("\nTesting invalid page number...")
        invalid_highlights = [
            {
                'page': 999,  # Beyond PDF page count
                'rects': [[100, 40, 300, 60]],
                'color': '#FFFF00'
            }
        ]
        
        # This should succeed but skip the invalid page
        success, message = add_highlights_to_pdf(pdf_path, invalid_highlights)
        print(f"Invalid page: {success} - {message}")
        # The function should succeed but log a warning for the invalid page
        
        print("✓ Security limit tests passed")
        return True


def main():
    """Run all tests"""
    print("="*80)
    print("PDF ANNOTATOR TEST SUITE")
    print("="*80)
    print(f"PyMuPDF version: {fitz.__version__}")
    
    try:
        test_validation()
        test_color_conversion()
        test_add_and_retrieve_highlights()
        test_clear_highlights()
        test_security_limits()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED ✓")
        print("="*80)
        return 0
    
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
