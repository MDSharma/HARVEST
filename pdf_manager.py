#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Management for Projects
Handles downloading and managing PDFs for project DOIs with multiple source fallbacks
"""

import os
import re
import requests
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time
from urllib.parse import urlparse
import ipaddress
import warnings

# Suppress pkg_resources deprecation warning from eutils (dependency of metapub)
# The eutils package uses deprecated pkg_resources API which will be removed in 2025
# We use pmc_enhanced as the preferred alternative to metapub
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)

try:
    from config import UNPAYWALL_EMAIL, ENABLE_METAPUB_FALLBACK, ENABLE_HABANERO_DOWNLOAD, HABANERO_PROXY_URL
except ImportError:
    UNPAYWALL_EMAIL = "research@example.com"
    ENABLE_METAPUB_FALLBACK = False
    ENABLE_HABANERO_DOWNLOAD = True
    HABANERO_PROXY_URL = ""

# Try importing optional libraries
# Note: metapub depends on eutils which uses deprecated pkg_resources
# The warning is suppressed at module level; prefer pmc_enhanced over metapub
try:
    from metapub import PubMedFetcher
    METAPUB_AVAILABLE = True
except ImportError:
    METAPUB_AVAILABLE = False
    print("[PDF] Warning: metapub not installed. Fallback downloads disabled.")

try:
    from habanero import Crossref
    HABANERO_AVAILABLE = True
except ImportError:
    HABANERO_AVAILABLE = False
    print("[PDF] Warning: habanero not installed. Institutional access disabled.")

try:
    from unpywall import Unpywall
    from unpywall.utils import UnpywallCredentials
    UNPYWALL_AVAILABLE = True
    # Configure Unpywall with email if available
    if UNPAYWALL_EMAIL and UNPAYWALL_EMAIL != "your-email@example.com":
        try:
            UnpywallCredentials(UNPAYWALL_EMAIL)
        except Exception as e:
            print(f"[PDF] Warning: Could not set Unpywall credentials: {e}")
except ImportError:
    UNPYWALL_AVAILABLE = False
    print("[PDF] Warning: unpywall library not installed. Using REST API fallback only.")

# Security constants
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100 MB limit for PDF downloads
ALLOWED_URL_SCHEMES = ['http', 'https']  # Only allow HTTP(S) downloads

def validate_doi(doi: str) -> bool:
    """
    Validate DOI format to prevent injection attacks.
    Returns True if DOI is valid, False otherwise.
    
    DOI format: 10.prefix/suffix
    - Prefix: 4-9 digits
    - Suffix: Can contain any printable ASCII character except whitespace
    
    Per DOI spec, the suffix can include: a-z A-Z 0-9 - . _ ; ( ) / : and more
    We exclude only dangerous characters that could enable injection attacks:
    - No whitespace
    - No quotes (single or double)
    - No backslashes
    - No control characters
    """
    if not doi or not isinstance(doi, str):
        return False
    
    # Must start with 10.xxxx/ where xxxx is 4-9 digits
    if not re.match(r'^10\.\d{4,9}/', doi):
        return False
    
    # Check for dangerous characters that could enable injection
    # Allow: a-z A-Z 0-9 and common DOI punctuation: . - _ ( ) [ ] / : ;
    # Explicitly block: quotes, backslash, whitespace, control characters
    dangerous_chars = r'[\s\\"\'\x00-\x1f\x7f]'
    if re.search(dangerous_chars, doi):
        return False
    
    # Additional length check to prevent abuse
    if len(doi) > 200:  # DOIs are typically much shorter
        return False
    
    return True

def validate_url(url: str) -> bool:
    """
    Validate URL to ensure it's safe to download from.
    Returns True if URL is valid and safe, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        parsed = urlparse(url)
        # Check scheme is allowed
        if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
            print(f"[PDF] Security: Blocked URL with invalid scheme: {parsed.scheme}")
            return False
        
        # Check for localhost/internal IPs (SSRF protection)
        hostname = parsed.hostname
        if hostname:
            hostname_lower = hostname.lower()
            
            # Block localhost explicitly
            if hostname_lower in ['localhost', '0.0.0.0', '::1']:
                print(f"[PDF] Security: Blocked URL targeting internal network: {hostname}")
                return False
            
            # Try to parse as IP address
            try:
                ip = ipaddress.ip_address(hostname)
                # Block private, loopback, link-local, and multicast addresses
                if (ip.is_private or ip.is_loopback or 
                    ip.is_link_local or ip.is_multicast or 
                    ip.is_reserved):
                    print(f"[PDF] Security: Blocked URL targeting internal network: {hostname}")
                    return False
            except ValueError:
                # Not an IP address, it's a hostname - allow it
                pass
        
        return True
    except Exception as e:
        print(f"[PDF] Security: URL validation error: {e}")
        return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    Returns sanitized filename with only alphanumeric and safe characters.
    """
    # Remove any path components
    filename = os.path.basename(filename)
    # Keep only alphanumeric, dots, hyphens, and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Remove leading dots to prevent hidden files
    filename = filename.lstrip('.')
    # Ensure it ends with .pdf
    if not filename.endswith('.pdf'):
        filename = filename + '.pdf'
    return filename

def generate_doi_hash(doi: str) -> str:
    """Generate a hash from DOI for file naming"""
    return hashlib.sha256(doi.encode('utf-8')).hexdigest()[:16]

def check_open_access(doi: str, email: str = None) -> Tuple[bool, str]:
    """
    Check if a DOI is open access and get the download URL if available.
    Uses both REST API and unpywall library for better PDF link detection.
    Returns: (is_open_access, pdf_url or error_message)
    """
    # Validate DOI format
    if not validate_doi(doi):
        return False, f"Invalid DOI format: {doi}"
    
    # First try the REST API approach
    try:
        if email is None:
            email = UNPAYWALL_EMAIL
        url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
        r = requests.get(url, timeout=10)
        
        if r.ok:
            data = r.json()
            if data.get("is_oa"):
                # Try to get best OA location
                best_oa = data.get("best_oa_location")
                if best_oa and best_oa.get("url_for_pdf"):
                    return True, best_oa["url_for_pdf"]
                elif best_oa and best_oa.get("url"):
                    # Found OA but no direct PDF URL - try unpywall library as fallback
                    if UNPYWALL_AVAILABLE:
                        print(f"[PDF] Unpaywall REST API: is_oa=True but url_for_pdf is null, trying unpywall library...")
                        try:
                            pdf_link = Unpywall.get_pdf_link(doi=doi)
                            if pdf_link:
                                print(f"[PDF] Unpywall library found PDF link: {pdf_link}")
                                return True, pdf_link
                            else:
                                print(f"[PDF] Unpywall library returned no PDF link")
                        except Exception as e:
                            print(f"[PDF] Unpywall library error: {e}")
                    return True, best_oa["url"]
            return False, "Not open access"
        else:
            return False, f"Unpaywall API error: {r.status_code}"
    except Exception as e:
        # If REST API fails and unpywall library is available, try it as fallback
        if UNPYWALL_AVAILABLE:
            print(f"[PDF] Unpaywall REST API failed ({str(e)}), trying unpywall library...")
            try:
                pdf_link = Unpywall.get_pdf_link(doi=doi)
                if pdf_link:
                    print(f"[PDF] Unpywall library found PDF link: {pdf_link}")
                    return True, pdf_link
            except Exception as lib_error:
                print(f"[PDF] Unpywall library also failed: {lib_error}")
        return False, f"Error checking open access: {str(e)}"

def try_metapub_download(doi: str) -> Tuple[bool, str]:
    """
    Try to find PDF using metapub (PubMed Central, arXiv, etc.)
    
    LEGACY: This function uses the metapub library which depends on eutils.
    The eutils package uses deprecated pkg_resources API.
    Prefer using try_pmc_enhanced() and try_arxiv_enhanced() instead.
    
    Returns: (success, pdf_url or error_message)
    """
    if not METAPUB_AVAILABLE or not ENABLE_METAPUB_FALLBACK:
        return False, "Metapub not available or disabled"
    
    try:
        print(f"[PDF] Trying metapub for: {doi}")
        fetcher = PubMedFetcher()
        
        # Try to get article by DOI
        try:
            article = fetcher.article_by_doi(doi)
            if article:
                # Check for PMC ID (PubMed Central)
                if article.pmc:
                    pmc_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{article.pmc}/pdf/"
                    print(f"[PDF] Found PMC article: {pmc_url}")
                    return True, pmc_url
                
                # Check if it's an arXiv paper
                if 'arxiv' in doi.lower():
                    arxiv_id = doi.split('/')[-1]
                    arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    print(f"[PDF] Found arXiv paper: {arxiv_url}")
                    return True, arxiv_url
        except Exception as e:
            print(f"[PDF] Metapub lookup failed: {e}")
        
        return False, "No open access version found via metapub"
    except Exception as e:
        return False, f"Metapub error: {str(e)}"

def try_habanero_download(doi: str) -> Tuple[bool, str]:
    """
    Try to get PDF using habanero (Crossref) with optional institutional access
    Returns: (success, pdf_url or error_message)
    """
    if not HABANERO_AVAILABLE or not ENABLE_HABANERO_DOWNLOAD:
        return False, "Habanero not available or disabled"
    
    try:
        print(f"[PDF] Trying habanero/Crossref for: {doi}")
        cr = Crossref()
        
        # Get work metadata
        work = cr.works(ids=doi)
        if work and 'message' in work:
            message = work['message']
            
            # Check for links
            if 'link' in message:
                for link in message['link']:
                    if link.get('content-type') == 'application/pdf':
                        pdf_url = link.get('URL')
                        if pdf_url:
                            print(f"[PDF] Found PDF link via Crossref: {pdf_url}")
                            return True, pdf_url
            
            # Try publisher URL if available
            if 'URL' in message:
                url = message['URL']
                # Some publishers have predictable PDF URLs
                if 'doi.org' in url:
                    # This would require institutional access
                    print(f"[PDF] Publisher URL (may need institutional access): {url}")
                    return True, url
        
        return False, "No accessible PDF found via habanero"
    except Exception as e:
        return False, f"Habanero error: {str(e)}"

def download_pdf(doi: str, pdf_url: str, save_dir: str, use_proxy: bool = False) -> Tuple[bool, str]:
    """
    Download PDF from URL and save with doi_hash filename.
    Returns: (success, message)
    """
    try:
        # Validate DOI format
        if not validate_doi(doi):
            return False, f"Invalid DOI format: {doi}"
        
        # Validate URL
        if not validate_url(pdf_url):
            return False, f"Invalid or unsafe URL: {pdf_url}"
        
        doi_hash = generate_doi_hash(doi)
        filename = sanitize_filename(f"{doi_hash}.pdf")
        filepath = os.path.join(save_dir, filename)
        
        # Check if file already exists
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                return True, f"File already exists: {filename} ({file_size} bytes)"
        
        # Download with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ResearchBot/1.0)',
        }
        
        # Use proxy if enabled and URL provided
        proxies = None
        if use_proxy and HABANERO_PROXY_URL:
            proxies = {
                'http': HABANERO_PROXY_URL,
                'https': HABANERO_PROXY_URL,
            }
            print(f"[PDF] Using proxy: {HABANERO_PROXY_URL}")
        
        response = requests.get(pdf_url, headers=headers, proxies=proxies, timeout=30, stream=True, allow_redirects=True)
        
        if response.ok:
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                return False, f"Response is not a PDF (content-type: {content_type})"
            
            # Check content length to prevent DoS
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_PDF_SIZE:
                return False, f"File too large ({int(content_length)} bytes exceeds {MAX_PDF_SIZE} bytes limit)"
            
            # Save file with size limit
            total_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        # Check size during download
                        if total_size > MAX_PDF_SIZE:
                            f.close()
                            os.remove(filepath)
                            return False, f"Download aborted: file size exceeds {MAX_PDF_SIZE} bytes limit"
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            if file_size < 1000:  # Likely an error page
                os.remove(filepath)
                return False, f"Downloaded file too small ({file_size} bytes), likely an error page"
            
            return True, f"Downloaded: {filename} ({file_size} bytes)"
        else:
            return False, f"Download failed: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"Download error: {str(e)}"

def download_pdf_multi_source(doi: str, save_dir: str) -> Tuple[bool, str, str]:
    """
    Try to download PDF from multiple sources in order:
    1. Unpaywall (open access)
    2. Metapub (PMC, arXiv, etc.) if enabled
    3. Habanero/Crossref with optional institutional access if enabled
    
    Returns: (success, message, source_used)
    """
    # Check if file already exists
    doi_hash = generate_doi_hash(doi)
    filename = f"{doi_hash}.pdf"
    filepath = os.path.join(save_dir, filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return True, f"File already exists: {filename}", "cached"
    
    # Try Unpaywall first
    print(f"[PDF] Step 1: Trying Unpaywall for {doi}")
    is_oa, pdf_url_or_reason = check_open_access(doi)
    if is_oa:
        success, message = download_pdf(doi, pdf_url_or_reason, save_dir)
        if success:
            return True, message, "unpaywall"
        print(f"[PDF] Unpaywall download failed: {message}")
    else:
        print(f"[PDF] Unpaywall check failed: {pdf_url_or_reason}")
    
    # Try metapub as fallback
    if ENABLE_METAPUB_FALLBACK and METAPUB_AVAILABLE:
        print(f"[PDF] Step 2: Trying Metapub for {doi}")
        metapub_success, metapub_url = try_metapub_download(doi)
        if metapub_success:
            success, message = download_pdf(doi, metapub_url, save_dir)
            if success:
                return True, message, "metapub"
            print(f"[PDF] Metapub download failed: {message}")
        else:
            print(f"[PDF] Metapub check failed: {metapub_url}")
    
    # Try habanero with optional institutional access
    if ENABLE_HABANERO_DOWNLOAD and HABANERO_AVAILABLE:
        print(f"[PDF] Step 3: Trying Habanero for {doi}")
        hab_success, hab_url = try_habanero_download(doi)
        if hab_success:
            # Try without proxy first
            success, message = download_pdf(doi, hab_url, save_dir, use_proxy=False)
            if success:
                return True, message, "habanero"
            
            # Try with proxy if configured
            if HABANERO_PROXY_URL:
                print(f"[PDF] Retrying with institutional proxy")
                success, message = download_pdf(doi, hab_url, save_dir, use_proxy=True)
                if success:
                    return True, message, "habanero_proxy"
            
            print(f"[PDF] Habanero download failed: {message}")
        else:
            print(f"[PDF] Habanero check failed: {hab_url}")
    
    # All methods failed
    return False, "All download methods failed", "none"

def process_project_dois(doi_list: List[str], project_dir: str) -> Dict:
    """
    Process a list of DOIs for a project:
    - Check open access status
    - Download available PDFs using multiple sources
    - Track what needs manual upload
    
    Returns: {
        "downloaded": [(doi, filename, message, source), ...],
        "needs_upload": [(doi, filename, reason), ...],
        "errors": [(doi, error), ...]
    }
    """
    return process_project_dois_with_progress(doi_list, project_dir, None)

def process_project_dois_with_progress(doi_list: List[str], project_dir: str, progress_callback=None) -> Dict:
    """
    Process a list of DOIs for a project with progress updates.
    
    Args:
        doi_list: List of DOIs to process
        project_dir: Directory to save PDFs
        progress_callback: Optional callback function(current_idx, doi, success, message, source)
    
    Returns: {
        "downloaded": [(doi, filename, message, source), ...],
        "needs_upload": [(doi, filename, reason), ...],
        "errors": [(doi, error), ...]
    }
    """
    # Create project directory if it doesn't exist
    try:
        Path(project_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[PDF] Error creating project directory: {e}")
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
        
        # Clean DOI - remove any URL prefixes
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        
        # Validate DOI format
        if not validate_doi(doi):
            print(f"[PDF] Invalid DOI format: {doi}")
            results["errors"].append((doi, "Invalid DOI format"))
            if progress_callback:
                progress_callback(idx, doi, False, "Invalid DOI format", "")
            continue
        
        doi_hash = generate_doi_hash(doi)
        filename = sanitize_filename(f"{doi_hash}.pdf")
        
        print(f"[PDF] Processing DOI {idx + 1}/{len(doi_list)}: {doi}")
        
        try:
            # Try multi-source download
            success, message, source = download_pdf_multi_source(doi, project_dir)
            
            if success:
                print(f"[PDF] Success via {source}: {message}")
                results["downloaded"].append((doi, filename, message, source))
                if progress_callback:
                    progress_callback(idx, doi, True, message, source)
            else:
                # All methods failed - needs manual upload
                print(f"[PDF] Failed: {message}")
                results["needs_upload"].append((doi, filename, message))
                if progress_callback:
                    progress_callback(idx, doi, False, message, "")
            
            # Be nice to APIs
            time.sleep(1)
            
        except Exception as e:
            print(f"[PDF] Error processing {doi}: {e}")
            results["errors"].append((doi, str(e)))
            if progress_callback:
                progress_callback(idx, doi, False, f"Error: {str(e)}", "")
    
    print(f"[PDF] Batch complete - Downloaded: {len(results['downloaded'])}, "
          f"Needs upload: {len(results['needs_upload'])}, Errors: {len(results['errors'])}")
    
    return results

def get_project_pdf_dir(project_id: int, base_dir: str = "project_pdfs") -> str:
    """Get the directory path for a project's PDFs"""
    return os.path.join(base_dir, f"project_{project_id}")

def list_project_pdfs(project_dir: str) -> List[Dict]:
    """
    List all PDFs in a project directory.
    Returns: [{"filename": "xxx.pdf", "size": 12345, "path": "..."}, ...]
    """
    if not os.path.exists(project_dir):
        return []
    
    # Resolve to absolute path to prevent directory traversal
    project_dir = os.path.abspath(project_dir)
    
    pdfs = []
    try:
        for filename in os.listdir(project_dir):
            # Sanitize filename and only allow PDF files
            if not filename.endswith('.pdf'):
                continue
            
            # Prevent directory traversal by ensuring the file is within project_dir
            filepath = os.path.abspath(os.path.join(project_dir, filename))
            if not filepath.startswith(project_dir):
                print(f"[PDF] Security: Blocked access to file outside project directory: {filename}")
                continue
            
            # Check if it's a file (not a directory or symlink)
            if os.path.isfile(filepath) and not os.path.islink(filepath):
                pdfs.append({
                    "filename": os.path.basename(filename),
                    "size": os.path.getsize(filepath),
                    "path": filepath
                })
    except Exception as e:
        print(f"[PDF] Error listing PDFs: {e}")
        return []
    
    return pdfs


# ========================================================================
# Enhanced Smart Download System
# ========================================================================

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
    import time
    from pdf_sources import (
        try_europe_pmc, try_core, try_semantic_scholar, try_scihub,
        try_publisher_direct, try_biorxiv_medrxiv, try_arxiv_enhanced,
        try_pmc_enhanced, try_zenodo, try_doaj
    )
    
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
    from pdf_download_db import (
        init_pdf_download_db, log_download_attempt, get_source_rankings,
        get_best_source_for_publisher, record_publisher_success,
        add_to_retry_queue, remove_from_retry_queue, get_config_value
    )
    from pdf_sources import (
        classify_failure, is_temporary_failure, extract_doi_prefix, get_publisher_name
    )
    
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

    # All sources failed
    print(f"[PDF Smart] All sources failed for {doi}")
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
    from pdf_download_db import init_pdf_download_db, get_config_value
    
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
        print(f"[PDF] Error getting active mechanisms: {e}")
        return []


if __name__ == "__main__":
    # Test with a known open access DOI
    test_doi = "10.1371/journal.pone.0000001"
    print(f"Testing with DOI: {test_doi}")
    
    test_dir = "/tmp/test_pdfs"
    Path(test_dir).mkdir(exist_ok=True)
    
    success, message, source = download_pdf_multi_source(test_doi, test_dir)
    print(f"Success: {success}")
    print(f"Message: {message}")
    print(f"Source: {source}")
