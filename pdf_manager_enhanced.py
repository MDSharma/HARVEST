#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced PDF Manager with Smart Multi-Source Download
Integrates all PDF sources with database-driven source selection and performance tracking
"""

import os
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from pdf_manager import (
    download_pdf, validate_doi, generate_doi_hash, sanitize_filename,
    check_open_access, try_metapub_download, try_habanero_download,
    METAPUB_AVAILABLE, HABANERO_AVAILABLE
)
from pdf_download_db import (
    init_pdf_download_db, log_download_attempt, get_source_rankings,
    get_best_source_for_publisher, record_publisher_success,
    add_to_retry_queue, remove_from_retry_queue, get_config_value
)
from pdf_sources import (
    try_europe_pmc, try_core, try_semantic_scholar, try_scihub,
    try_publisher_direct, classify_failure, is_temporary_failure,
    get_retry_delay_seconds, extract_doi_prefix, get_publisher_name,
    try_biorxiv_medrxiv, try_arxiv_enhanced, try_pmc_enhanced,
    try_zenodo, try_doaj
)

try:
    from config import UNPAYWALL_EMAIL
except ImportError:
    UNPAYWALL_EMAIL = "research@example.com"


def check_library_available(library_name: Optional[str]) -> bool:
    """Check if an optional library is available"""
    if library_name is None:
        return True

    if library_name == 'metapub':
        return METAPUB_AVAILABLE
    elif library_name == 'habanero':
        return HABANERO_AVAILABLE
    elif library_name == 'unpywall':
        try:
            import unpywall
            return True
        except ImportError:
            return False

    return True


def try_source(source_name: str, doi: str, config: Dict) -> Tuple[bool, str, Optional[int]]:
    """
    Try a single source to get PDF URL.
    Returns: (success, pdf_url_or_error, response_time_ms)
    """
    start_time = time.time()

    try:
        if source_name == 'unpaywall':
            is_oa, result = check_open_access(doi, UNPAYWALL_EMAIL)
            response_time = int((time.time() - start_time) * 1000)
            return is_oa, result, response_time

        elif source_name == 'unpywall':
            try:
                from unpywall import Unpywall
                pdf_link = Unpywall.get_pdf_link(doi=doi)
                response_time = int((time.time() - start_time) * 1000)
                if pdf_link:
                    return True, pdf_link, response_time
                return False, "Unpywall library returned no PDF link", response_time
            except Exception as e:
                response_time = int((time.time() - start_time) * 1000)
                return False, f"Unpywall library error: {str(e)}", response_time

        elif source_name == 'biorxiv_medrxiv':
            timeout = config.get('timeout', 15)
            success, result = try_biorxiv_medrxiv(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'europe_pmc':
            timeout = config.get('timeout', 15)
            success, result = try_europe_pmc(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'pmc_enhanced':
            timeout = config.get('timeout', 15)
            success, result = try_pmc_enhanced(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'arxiv_enhanced':
            timeout = config.get('timeout', 15)
            success, result = try_arxiv_enhanced(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'core':
            timeout = config.get('timeout', 15)
            api_key = config.get('core_api_key')
            success, result = try_core(doi, api_key, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'zenodo':
            timeout = config.get('timeout', 15)
            success, result = try_zenodo(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'semantic_scholar':
            timeout = config.get('timeout', 15)
            success, result = try_semantic_scholar(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'doaj':
            timeout = config.get('timeout', 15)
            success, result = try_doaj(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'scihub':
            timeout = config.get('timeout', 20)
            success, result = try_scihub(doi, timeout=timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'publisher_direct':
            timeout = config.get('timeout', 15)
            success, result = try_publisher_direct(doi, timeout)
            response_time = int((time.time() - start_time) * 1000)
            return success, result, response_time

        elif source_name == 'metapub':
            if METAPUB_AVAILABLE:
                success, result = try_metapub_download(doi)
                response_time = int((time.time() - start_time) * 1000)
                return success, result, response_time
            return False, "Metapub not available", 0

        elif source_name == 'habanero':
            if HABANERO_AVAILABLE:
                success, result = try_habanero_download(doi)
                response_time = int((time.time() - start_time) * 1000)
                return success, result, response_time
            return False, "Habanero not available", 0

        else:
            return False, f"Unknown source: {source_name}", 0

    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        return False, f"Exception: {str(e)}", response_time


def download_pdf_smart(
    doi: str,
    project_id: int,
    save_dir: str,
    progress_callback=None
) -> Tuple[bool, str, str]:
    """
    Smart PDF download using database-driven source selection.

    Strategy:
    1. Check if file already exists
    2. Check publisher-specific successful source from history
    3. Get sources ranked by overall performance
    4. Try sources in optimized order
    5. Log all attempts to database
    6. Record successful patterns for future use
    7. Add to retry queue if temporary failure

    Returns: (success, message, source_used)
    """
    # Initialize database if needed
    init_pdf_download_db()

    # Validate DOI
    if not validate_doi(doi):
        return False, f"Invalid DOI format: {doi}", "none"

    # Check if file already exists
    doi_hash = generate_doi_hash(doi)
    filename = sanitize_filename(f"{doi_hash}.pdf")
    filepath = os.path.join(save_dir, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return True, f"File already exists: {filename}", "cached"

    # Get configuration
    rate_limit_delay = int(get_config_value('rate_limit_delay_seconds', '1'))

    # Extract publisher info
    doi_prefix = extract_doi_prefix(doi)
    publisher_name = get_publisher_name(doi)

    print(f"[PDF Smart] Processing {doi} (Publisher: {publisher_name})")

    # Step 1: Try publisher-specific best source first
    best_for_publisher = get_best_source_for_publisher(doi_prefix)
    tried_sources = set()

    if best_for_publisher:
        print(f"[PDF Smart] Trying publisher-optimized source: {best_for_publisher}")
        tried_sources.add(best_for_publisher)

        success, result, response_time = try_source(best_for_publisher, doi, {})

        # Log attempt
        log_download_attempt(
            project_id=project_id,
            doi=doi,
            source_name=best_for_publisher,
            success=success,
            failure_reason=None if success else result,
            failure_category=None if success else classify_failure(result),
            response_time_ms=response_time,
            pdf_url=result if success else None
        )

        if success:
            # Try to download the PDF
            dl_success, dl_message = download_pdf(doi, result, save_dir)
            if dl_success:
                # Update publisher pattern
                record_publisher_success(doi_prefix, publisher_name, best_for_publisher, result)
                print(f"[PDF Smart] Success via publisher-optimized source: {best_for_publisher}")
                return True, dl_message, best_for_publisher

        time.sleep(rate_limit_delay)

    # Step 2: Try sources ranked by performance
    source_rankings = get_source_rankings()

    for source_info in source_rankings:
        source_name = source_info['name']

        # Skip if already tried
        if source_name in tried_sources:
            continue

        # Skip if requires unavailable library
        requires_lib = source_info.get('requires_library')
        if not check_library_available(requires_lib):
            print(f"[PDF Smart] Skipping {source_name}: required library '{requires_lib}' not available")
            continue

        # Skip if disabled
        if not source_info.get('enabled', True):
            print(f"[PDF Smart] Skipping {source_name}: disabled")
            continue

        print(f"[PDF Smart] Trying {source_name} (success rate: {source_info['success_rate']:.1f}%)")
        tried_sources.add(source_name)

        success, result, response_time = try_source(source_name, doi, {})

        # Classify failure
        failure_category = None if success else classify_failure(result)

        # Log attempt
        log_download_attempt(
            project_id=project_id,
            doi=doi,
            source_name=source_name,
            success=success,
            failure_reason=None if success else result,
            failure_category=failure_category,
            response_time_ms=response_time,
            pdf_url=result if success else None
        )

        if success:
            # Try to download the PDF
            dl_success, dl_message = download_pdf(doi, result, save_dir)

            if dl_success:
                # Record this success for publisher pattern learning
                record_publisher_success(doi_prefix, publisher_name, source_name, result)
                print(f"[PDF Smart] Success via {source_name}")

                # Remove from retry queue if it was there
                remove_from_retry_queue(project_id, doi)

                return True, dl_message, source_name
            else:
                # Download failed even though we got a URL
                failure_cat = classify_failure(dl_message)
                log_download_attempt(
                    project_id=project_id,
                    doi=doi,
                    source_name=f"{source_name}_download",
                    success=False,
                    failure_reason=dl_message,
                    failure_category=failure_cat,
                    response_time_ms=None,
                    pdf_url=result
                )
        else:
            print(f"[PDF Smart] {source_name} failed: {result}")

        # Rate limiting between sources
        time.sleep(rate_limit_delay)

    # Step 3: Try publisher direct as last resort before giving up
    if 'publisher_direct' not in tried_sources:
        print(f"[PDF Smart] Trying publisher_direct as last resort")
        success, result, response_time = try_source('publisher_direct', doi, {})

        log_download_attempt(
            project_id=project_id,
            doi=doi,
            source_name='publisher_direct',
            success=success,
            failure_reason=None if success else result,
            failure_category=None if success else classify_failure(result),
            response_time_ms=response_time,
            pdf_url=result if success else None
        )

        if success:
            dl_success, dl_message = download_pdf(doi, result, save_dir)
            if dl_success:
                record_publisher_success(doi_prefix, publisher_name, 'publisher_direct', result)
                return True, dl_message, 'publisher_direct'

    # All sources failed - determine if we should retry
    print(f"[PDF Smart] All sources failed for {doi}")

    # Check if any failures were temporary
    # For simplicity, we'll add to retry queue if we had at least one temporary failure
    # In a more sophisticated version, we could check the last attempt's failure category

    return False, "All download sources failed", "none"


def process_dois_smart(
    doi_list: List[str],
    project_id: int,
    project_dir: str,
    progress_callback=None
) -> Dict:
    """
    Process multiple DOIs using smart download strategy.

    Args:
        doi_list: List of DOIs to download
        project_id: Project ID for tracking
        project_dir: Directory to save PDFs
        progress_callback: Optional callback(idx, doi, success, message, source)

    Returns: {
        "downloaded": [(doi, filename, message, source), ...],
        "needs_upload": [(doi, filename, reason), ...],
        "errors": [(doi, error), ...]
    }
    """
    # Initialize database
    init_pdf_download_db()

    # Create project directory
    try:
        Path(project_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[PDF Smart] Error creating project directory: {e}")
        return {
            "downloaded": [],
            "needs_upload": [],
            "errors": [("", f"Failed to create project directory: {str(e)}")]
        }

    results = {
        "downloaded": [],
        "needs_upload": [],
        "errors": []
    }

    for idx, doi in enumerate(doi_list):
        doi = doi.strip()
        if not doi:
            continue

        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        # Validate DOI
        if not validate_doi(doi):
            print(f"[PDF Smart] Invalid DOI: {doi}")
            results["errors"].append((doi, "Invalid DOI format"))
            if progress_callback:
                progress_callback(idx, doi, False, "Invalid DOI format", "")
            continue

        doi_hash = generate_doi_hash(doi)
        filename = sanitize_filename(f"{doi_hash}.pdf")

        print(f"[PDF Smart] Processing DOI {idx + 1}/{len(doi_list)}: {doi}")

        try:
            success, message, source = download_pdf_smart(doi, project_id, project_dir, progress_callback)

            if success:
                print(f"[PDF Smart] Success via {source}: {message}")
                results["downloaded"].append((doi, filename, message, source))
                if progress_callback:
                    progress_callback(idx, doi, True, message, source)
            else:
                print(f"[PDF Smart] Failed: {message}")
                results["needs_upload"].append((doi, filename, message))
                if progress_callback:
                    progress_callback(idx, doi, False, message, "")

            # Rate limiting between DOIs
            rate_limit_delay = int(get_config_value('rate_limit_delay_seconds', '1'))
            time.sleep(rate_limit_delay)

        except Exception as e:
            print(f"[PDF Smart] Error processing {doi}: {e}")
            results["errors"].append((doi, str(e)))
            if progress_callback:
                progress_callback(idx, doi, False, f"Error: {str(e)}", "")

    print(f"[PDF Smart] Batch complete - Downloaded: {len(results['downloaded'])}, "
          f"Needs upload: {len(results['needs_upload'])}, Errors: {len(results['errors'])}")

    return results


def get_active_download_mechanisms(db_path: str = None) -> List[Dict]:
    """
    Get list of active (enabled) download mechanisms with their status.
    
    Returns: List of dicts with source information:
        - name: source name
        - description: source description
        - enabled: whether source is enabled
        - success_rate: historical success rate (%)
        - total_attempts: total download attempts
        - avg_response_time_ms: average response time
    """
    from pdf_download_db import get_source_rankings, PDF_DB_PATH
    
    if db_path is None:
        db_path = PDF_DB_PATH
    
    try:
        # Get all sources with rankings
        sources = get_source_rankings(db_path)
        
        # Filter to only enabled sources
        active_sources = [s for s in sources if s.get('enabled')]
        
        return active_sources
    except Exception as e:
        print(f"[PDF Smart] Error getting active mechanisms: {e}")
        return []


if __name__ == "__main__":
    # Test smart download with a known open access DOI
    test_doi = "10.1371/journal.pone.0000001"
    test_project_id = 1
    test_dir = "/tmp/test_pdfs_smart"

    print(f"Testing smart PDF download with DOI: {test_doi}\n")

    Path(test_dir).mkdir(exist_ok=True)

    success, message, source = download_pdf_smart(test_doi, test_project_id, test_dir)

    print(f"\nResult:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")
    print(f"  Source: {source}")

    # Show source rankings
    print("\n\nCurrent Source Rankings:")
    rankings = get_source_rankings()
    for rank, source_info in enumerate(rankings[:10], 1):
        print(f"  {rank}. {source_info['name']:20s} - "
              f"{source_info['success_rate']:5.1f}% success, "
              f"{source_info['avg_response_time_ms']:6.0f}ms avg, "
              f"{source_info['total_attempts']:3d} attempts")
