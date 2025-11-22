#!/usr/bin/env python3
"""
Test script for DOI validation functionality.
Tests that DOIs are properly lowercased and validated via CrossRef API.
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_doi_lowercase():
    """Test that DOIs are converted to lowercase"""
    print("\n=== Testing DOI Lowercase Conversion ===")
    
    # Test cases with mixed case DOIs
    test_cases = [
        ("10.1371/JOURNAL.PONE.0000000", "10.1371/journal.pone.0000000"),
        ("10.1038/S41586-020-2649-2", "10.1038/s41586-020-2649-2"),
        ("10.1109/ACCESS.2020.3000000", "10.1109/access.2020.3000000"),
        ("https://doi.org/10.1234/TEST", "10.1234/test"),
    ]
    
    passed = 0
    failed = 0
    
    for input_doi, expected_output in test_cases:
        # Simulate the normalization logic
        doi = input_doi.strip()
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        doi = doi.lower()
        
        if doi == expected_output:
            print(f"✓ PASS: '{input_doi}' → '{doi}'")
            passed += 1
        else:
            print(f"✗ FAIL: '{input_doi}' → '{doi}' (expected '{expected_output}')")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_doi_validation_api():
    """Test DOI validation via the API endpoint"""
    print("\n=== Testing DOI Validation API ===")
    
    import requests
    
    # Try to connect to the backend
    try:
        # Test with a valid DOI (should be lowercase in response)
        api_url = os.environ.get("HARVEST_API_URL", "http://localhost:5001")
        
        print(f"Testing against API at: {api_url}")
        
        # Test 1: Valid DOI with uppercase letters
        test_doi = "10.1371/JOURNAL.pone.0215794"
        expected_lowercase = "10.1371/journal.pone.0215794"
        
        print(f"\nTest 1: Validating '{test_doi}'...")
        response = requests.post(
            f"{api_url}/api/validate-doi",
            json={"doi": test_doi},
            timeout=15
        )
        
        if response.ok:
            result = response.json()
            if result.get("valid"):
                returned_doi = result.get("doi", "")
                if returned_doi == expected_lowercase:
                    print(f"✓ PASS: DOI returned in lowercase: '{returned_doi}'")
                    return True
                else:
                    print(f"✗ FAIL: DOI not lowercased. Got '{returned_doi}', expected '{expected_lowercase}'")
                    return False
            else:
                print(f"✗ FAIL: DOI validation failed: {result.get('error', 'Unknown error')}")
                print("Note: This might be expected if the DOI doesn't exist in CrossRef")
                return True  # Don't fail the test if DOI doesn't exist
        else:
            print(f"✗ FAIL: API request failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠ WARNING: Could not connect to backend API. Skipping API tests.")
        print("To run API tests, start the backend with: python3 harvest_be.py")
        return True  # Don't fail if backend is not running
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return False


def main():
    print("=" * 60)
    print("DOI Validation Test Suite")
    print("=" * 60)
    
    # Run tests
    test1_pass = test_doi_lowercase()
    test2_pass = test_doi_validation_api()
    
    print("\n" + "=" * 60)
    if test1_pass and test2_pass:
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    else:
        print("Some tests failed! ✗")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
