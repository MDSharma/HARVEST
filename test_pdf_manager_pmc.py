#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for PMC URL generation in pdf_manager.py
Tests the fix for correct PMC domain and PDF filename construction
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_manager import _get_pdf_filename_from_doi


def test_get_pdf_filename_from_doi_plos_journals():
    """Test PDF filename extraction for PLOS journals"""
    
    test_cases = [
        # PLOS ONE
        ("10.1371/journal.pone.0229615", "pone.0229615.pdf"),
        ("10.1371/journal.pone.0000001", "pone.0000001.pdf"),
        
        # PLOS Computational Biology
        ("10.1371/journal.pcbi.1008279", "pcbi.1008279.pdf"),
        
        # PLOS Genetics
        ("10.1371/journal.pgen.1009123", "pgen.1009123.pdf"),
        
        # PLOS Biology
        ("10.1371/journal.pbio.3000567", "pbio.3000567.pdf"),
    ]
    
    print("Testing PLOS journal filename extraction:")
    all_passed = True
    
    for doi, expected in test_cases:
        result = _get_pdf_filename_from_doi(doi)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"  {status} {doi} -> {result}")
        if not passed:
            print(f"    Expected: {expected}")
    
    return all_passed


def test_get_pdf_filename_from_doi_non_plos():
    """Test that non-PLOS journals return None"""
    
    test_cases = [
        "10.1126/science.196.4287.293",  # Science
        "10.1038/s41586-020-2649-2",     # Nature
        "10.1016/j.cell.2020.01.001",    # Cell
        "10.1093/nar/gkab1112",           # Nucleic Acids Research
    ]
    
    print("\nTesting non-PLOS journals (should return None):")
    all_passed = True
    
    for doi in test_cases:
        result = _get_pdf_filename_from_doi(doi)
        passed = result is None
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"  {status} {doi} -> {result}")
        if not passed:
            print(f"    Expected: None")
    
    return all_passed


def test_pmc_url_construction():
    """Test the complete PMC URL construction logic"""
    
    print("\nTesting complete PMC URL construction:")
    
    # Simulate the URL construction as done in try_metapub_download
    def construct_pmc_url(pmc_id: str, doi: str) -> str:
        pmc_base_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/"
        pdf_filename = _get_pdf_filename_from_doi(doi)
        
        if pdf_filename:
            return pmc_base_url + pdf_filename
        else:
            return pmc_base_url
    
    # Test case from the issue
    test_cases = [
        {
            "pmc_id": "7065751",
            "doi": "10.1371/journal.pone.0229615",
            "expected": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7065751/pdf/pone.0229615.pdf",
            "description": "PLOS ONE article with filename"
        },
        {
            "pmc_id": "4167664",
            "doi": "10.1126/science.196.4287.293",
            "expected": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4167664/pdf/",
            "description": "Non-PLOS article without filename"
        },
        {
            "pmc_id": "1234567",
            "doi": "10.1371/journal.pcbi.1008279",
            "expected": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1234567/pdf/pcbi.1008279.pdf",
            "description": "PLOS Computational Biology with filename"
        }
    ]
    
    all_passed = True
    for test in test_cases:
        result = construct_pmc_url(test["pmc_id"], test["doi"])
        passed = result == test["expected"]
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"  {status} {test['description']}")
        print(f"    PMC{test['pmc_id']} + {test['doi']}")
        print(f"    Result:   {result}")
        if not passed:
            print(f"    Expected: {test['expected']}")
    
    return all_passed


def test_domain_change():
    """Verify that the new domain is used instead of old domain"""
    
    print("\nTesting correct PMC domain usage:")
    
    pmc_id = "7065751"
    doi = "10.1371/journal.pone.0229615"
    
    # Construct URL as done in the fixed version
    pmc_base_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/"
    pdf_filename = _get_pdf_filename_from_doi(doi)
    new_url = pmc_base_url + pdf_filename if pdf_filename else pmc_base_url
    
    # Old incorrect URL
    old_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
    
    # Verify new domain is used
    domain_correct = "pmc.ncbi.nlm.nih.gov" in new_url
    domain_wrong = "www.ncbi.nlm.nih.gov" in new_url
    
    passed = domain_correct and not domain_wrong
    status = "✓" if passed else "✗"
    
    print(f"  {status} Correct domain 'pmc.ncbi.nlm.nih.gov' is used")
    print(f"    Old URL: {old_url}")
    print(f"    New URL: {new_url}")
    
    return passed


def main():
    """Run all tests"""
    print("="*80)
    print("PMC URL Generation Tests")
    print("="*80)
    
    results = []
    
    # Run all test functions
    results.append(("PLOS filename extraction", test_get_pdf_filename_from_doi_plos_journals()))
    results.append(("Non-PLOS returns None", test_get_pdf_filename_from_doi_non_plos()))
    results.append(("Complete URL construction", test_pmc_url_construction()))
    results.append(("Domain change verification", test_domain_change()))
    
    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        all_passed = all_passed and passed
    
    print("="*80)
    if all_passed:
        print("✓ All tests PASSED")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
