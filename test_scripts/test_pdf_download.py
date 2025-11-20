#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for PDF download workflow
Tests unpaywall, metapub, and habanero sources with a list of DOIs
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Import PDF manager functions
try:
    from pdf_manager import (
        check_open_access,
        try_metapub_download,
        download_pdf_multi_source,
        validate_doi,
        METAPUB_AVAILABLE,
        HABANERO_AVAILABLE,
        UNPYWALL_AVAILABLE,
        UNPAYWALL_EMAIL
    )
except ImportError as e:
    print(f"Error importing pdf_manager: {e}")
    sys.exit(1)

def sanitize_doi_input(doi: str) -> str:
    """
    Sanitize and validate DOI input from command line.
    Returns cleaned DOI or empty string if invalid.
    Uses the same validation as pdf_manager.validate_doi for consistency.
    """
    if not doi or not isinstance(doi, str):
        return ""
    
    # Strip whitespace
    doi = doi.strip()
    
    # Remove common URL prefixes
    doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
    
    # Validate using the same function from pdf_manager
    if not validate_doi(doi):
        print(f"Warning: Invalid DOI format, will be skipped: {doi}")
        return ""
    
    return doi

def test_unpaywall(doi: str) -> Dict:
    """Test Unpaywall API for a DOI"""
    print(f"\n  Testing Unpaywall...")
    try:
        is_oa, result = check_open_access(doi, UNPAYWALL_EMAIL)
        
        if is_oa:
            # Check if we got a PDF URL or just a page URL
            has_pdf_url = "pdf" in result.lower() or result.endswith('.pdf')
            return {
                "available": True,
                "is_open_access": True,
                "url": result,
                "has_pdf_url": has_pdf_url,
                "message": f"Open access PDF URL found" if has_pdf_url else f"Open access but no direct PDF URL"
            }
        else:
            return {
                "available": False,
                "is_open_access": False,
                "message": result
            }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "message": f"Error: {str(e)}"
        }

def test_metapub(doi: str) -> Dict:
    """Test Metapub (PubMed Central, arXiv) for a DOI"""
    print(f"  Testing Metapub...")
    
    if not METAPUB_AVAILABLE:
        return {
            "available": False,
            "message": "Metapub not installed or not available"
        }
    
    try:
        success, result = try_metapub_download(doi)
        
        if success:
            return {
                "available": True,
                "url": result,
                "message": f"Found via Metapub: {result}"
            }
        else:
            return {
                "available": False,
                "message": result
            }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "message": f"Error: {str(e)}"
        }

def test_habanero(doi: str) -> Dict:
    """Test Habanero (Crossref institutional access) for a DOI"""
    print(f"  Testing Habanero...")
    
    if not HABANERO_AVAILABLE:
        return {
            "available": False,
            "message": "Habanero not installed or not available"
        }
    
    # Note: Habanero is used in download_pdf_multi_source
    # We'll just check if it's available
    return {
        "available": True,
        "message": "Habanero is available (tested in multi-source download)"
    }

def test_doi(doi: str, test_dir: str) -> Dict:
    """Test all sources for a single DOI"""
    # Validate DOI first
    if not validate_doi(doi):
        print(f"\n{'='*80}")
        print(f"Skipping invalid DOI: {doi}")
        print(f"{'='*80}")
        return {
            "doi": doi,
            "unpaywall": {"available": False, "message": "Invalid DOI format"},
            "metapub": {"available": False, "message": "Invalid DOI format"},
            "habanero": {"available": False, "message": "Invalid DOI format"},
            "download": {"success": False, "message": "Invalid DOI format", "source": "none"}
        }
    
    print(f"\n{'='*80}")
    print(f"Testing DOI: {doi}")
    print(f"{'='*80}")
    
    results = {
        "doi": doi,
        "unpaywall": test_unpaywall(doi),
        "metapub": test_metapub(doi),
        "habanero": test_habanero(doi)
    }
    
    # Test actual download with multi-source
    print(f"  Testing multi-source download...")
    try:
        success, message, source = download_pdf_multi_source(doi, test_dir)
        results["download"] = {
            "success": success,
            "message": message,
            "source": source
        }
    except Exception as e:
        results["download"] = {
            "success": False,
            "error": str(e),
            "message": f"Error: {str(e)}"
        }
    
    return results

def print_summary(all_results: List[Dict]):
    """Print summary of all tests"""
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total = len(all_results)
    if total == 0:
        print("\nNo DOIs were tested.")
        return
    
    unpaywall_success = sum(1 for r in all_results if r["unpaywall"].get("available", False))
    metapub_success = sum(1 for r in all_results if r["metapub"].get("available", False))
    download_success = sum(1 for r in all_results if r["download"].get("success", False))
    
    print(f"\nTotal DOIs tested: {total}")
    print(f"Unpaywall found: {unpaywall_success}/{total} ({unpaywall_success*100//total if total else 0}%)")
    print(f"Metapub found: {metapub_success}/{total} ({metapub_success*100//total if total else 0}%)")
    print(f"Successfully downloaded: {download_success}/{total} ({download_success*100//total if total else 0}%)")
    
    print("\n" + "-"*80)
    print("Details by DOI:")
    print("-"*80)
    
    for result in all_results:
        doi = result["doi"]
        print(f"\n{doi}:")
        
        # Unpaywall
        uw = result["unpaywall"]
        if uw.get("available"):
            has_pdf = " (PDF URL)" if uw.get("has_pdf_url") else " (Page URL)"
            print(f"  ✓ Unpaywall: Open Access{has_pdf}")
            if not uw.get("has_pdf_url"):
                print(f"    ⚠ Warning: is_oa=True but no direct PDF URL")
        else:
            print(f"  ✗ Unpaywall: {uw.get('message', 'Not available')}")
        
        # Metapub
        mp = result["metapub"]
        if mp.get("available"):
            print(f"  ✓ Metapub: {mp.get('url', 'Available')}")
        else:
            print(f"  ✗ Metapub: {mp.get('message', 'Not available')}")
        
        # Habanero
        hb = result["habanero"]
        if hb.get("available"):
            print(f"  ✓ Habanero: {hb.get('message', 'Available')}")
        else:
            print(f"  ✗ Habanero: {hb.get('message', 'Not available')}")
        
        # Download result
        dl = result["download"]
        if dl.get("success"):
            print(f"  ✓ Download: SUCCESS via {dl.get('source', 'unknown')}")
        else:
            print(f"  ✗ Download: FAILED - {dl.get('message', 'Unknown error')}")

def main():
    """Main test function"""
    
    # Check configuration
    print("="*80)
    print("PDF DOWNLOAD WORKFLOW TEST")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Unpaywall Email: {UNPAYWALL_EMAIL}")
    print(f"  Unpywall Library Available: {UNPYWALL_AVAILABLE}")
    print(f"  Metapub Available: {METAPUB_AVAILABLE}")
    print(f"  Habanero Available: {HABANERO_AVAILABLE}")
    
    # Test DOIs - mix of open access and subscription
    test_dois = [
        # Open access examples
        "10.1371/journal.pone.0000000",  # PLOS (should be OA)
        "10.1038/s41586-020-2649-2",      # Nature (may be OA)
        "10.1093/nar/gkab1112",           # Nucleic Acids Research (often OA)
        "10.48550/arXiv.2103.00020",      # arXiv (should be OA)
        
        # Common journals (may or may not be OA)
        "10.1126/science.abc1234",        # Science
        "10.1016/j.cell.2020.01.001",     # Cell
    ]
    
    # Allow user to provide DOIs as arguments
    if len(sys.argv) > 1:
        # Sanitize command-line inputs
        raw_dois = sys.argv[1:]
        test_dois = []
        for doi in raw_dois:
            sanitized = sanitize_doi_input(doi)
            if sanitized:
                test_dois.append(sanitized)
        
        if not test_dois:
            print("\nError: No valid DOIs provided in command line arguments")
            sys.exit(1)
        
        print(f"\nUsing {len(test_dois)} valid DOI(s) from command line arguments")
    else:
        print(f"\nUsing {len(test_dois)} default test DOIs")
        print("(You can provide DOIs as command line arguments)")
    
    # Create test directory
    test_dir = "/tmp/pdf_test"
    try:
        Path(test_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"\nError: Failed to create test directory: {e}")
        sys.exit(1)
    print(f"\nTest download directory: {test_dir}")
    
    # Test each DOI
    all_results = []
    for doi in test_dois:
        result = test_doi(doi.strip(), test_dir)
        all_results.append(result)
    
    # Print summary
    print_summary(all_results)
    
    # List downloaded files
    downloaded_files = list(Path(test_dir).glob("*.pdf"))
    if downloaded_files:
        print(f"\n" + "-"*80)
        print(f"Downloaded files in {test_dir}:")
        print("-"*80)
        for f in downloaded_files:
            size_kb = f.stat().st_size / 1024
            print(f"  {f.name} ({size_kb:.1f} KB)")
    else:
        print(f"\nNo PDFs were downloaded to {test_dir}")
    
    print("\n" + "="*80)
    print("Test complete!")
    print("="*80)

if __name__ == "__main__":
    main()
