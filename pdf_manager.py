#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Management for Projects
Handles downloading and managing PDFs for project DOIs with multiple source fallbacks
"""

import os
import requests
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import time

# Import config and set NCBI_API_KEY environment variable before importing metapub
try:
    from config import UNPAYWALL_EMAIL, ENABLE_METAPUB_FALLBACK, ENABLE_HABANERO_DOWNLOAD, HABANERO_PROXY_URL, NCBI_API_KEY
    # Set NCBI_API_KEY as environment variable if provided in config
    # This must be done before importing metapub
    if NCBI_API_KEY and not os.getenv('NCBI_API_KEY'):
        os.environ['NCBI_API_KEY'] = NCBI_API_KEY
except ImportError:
    UNPAYWALL_EMAIL = "research@example.com"
    ENABLE_METAPUB_FALLBACK = False
    ENABLE_HABANERO_DOWNLOAD = True
    HABANERO_PROXY_URL = ""
    NCBI_API_KEY = ""

# Try importing optional libraries
try:
    from metapub import PubMedFetcher
    from metapub.findit import FindIt
    METAPUB_AVAILABLE = True
    FINDIT_AVAILABLE = True
except ImportError:
    METAPUB_AVAILABLE = False
    FINDIT_AVAILABLE = False
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

def generate_doi_hash(doi: str) -> str:
    """Generate a hash from DOI for file naming"""
    return hashlib.sha256(doi.encode('utf-8')).hexdigest()[:16]

def check_open_access(doi: str, email: str = None) -> Tuple[bool, str]:
    """
    Check if a DOI is open access and get the download URL if available.
    Uses both REST API and unpywall library for better PDF link detection.
    Returns: (is_open_access, pdf_url or error_message)
    """
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

def _get_pdf_filename_from_doi(doi: str) -> Optional[str]:
    """
    Extract PDF filename from DOI for known journal patterns.
    
    Args:
        doi: Digital Object Identifier
    
    Returns:
        PDF filename if pattern is recognized, None otherwise
    
    Examples:
        10.1371/journal.pone.0229615 -> pone.0229615.pdf
        10.1371/journal.pcbi.1008279 -> pcbi.1008279.pdf
    """
    # Handle PLOS journals (PLoS ONE, PLoS Computational Biology, etc.)
    # DOI pattern: 10.1371/journal.{journal_code}.{article_id}
    if "/journal." in doi:
        parts = doi.split('/')
        if len(parts) >= 2:
            journal_part = parts[-1]  # e.g., "journal.pone.0229615"
            if journal_part.startswith("journal."):
                # Remove "journal." prefix to get filename
                filename = journal_part.replace("journal.", "") + ".pdf"
                return filename
    
    # Add more patterns here for other journals as needed
    # For now, return None for unrecognized patterns
    return None

def try_metapub_download(doi: str) -> Tuple[bool, str]:
    """
    Try to find PDF using metapub (PubMed Central, arXiv, etc.)
    Uses multiple approaches:
    1. Direct PMC/arXiv lookup via PubMedFetcher
    2. FindIt module for publisher-specific PDF access
    
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
                    # Use correct PMC domain (pmc.ncbi.nlm.nih.gov instead of www.ncbi.nlm.nih.gov)
                    pmc_base_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{article.pmc}/pdf/"
                    
                    # Try to construct PDF filename from DOI for known journal patterns
                    pdf_filename = _get_pdf_filename_from_doi(doi)
                    
                    if pdf_filename:
                        pmc_url = pmc_base_url + pdf_filename
                        print(f"[PDF] Found PMC article with filename: {pmc_url}")
                    else:
                        # Fallback to directory URL (server may redirect to correct PDF)
                        pmc_url = pmc_base_url
                        print(f"[PDF] Found PMC article (directory URL): {pmc_url}")
                    
                    return True, pmc_url
                
                # Check if it's an arXiv paper
                if 'arxiv' in doi.lower():
                    arxiv_id = doi.split('/')[-1]
                    arxiv_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                    print(f"[PDF] Found arXiv paper: {arxiv_url}")
                    return True, arxiv_url
                
                # If we have a PMID but no PMC, try FindIt for publisher-specific access
                if article.pmid and FINDIT_AVAILABLE:
                    print(f"[PDF] Trying FindIt for publisher-specific access (PMID: {article.pmid})...")
                    try:
                        findit = FindIt(pmid=article.pmid, verify=False)
                        if findit.url:
                            print(f"[PDF] FindIt found PDF: {findit.url}")
                            return True, findit.url
                        else:
                            print(f"[PDF] FindIt: {findit.reason}")
                    except Exception as findit_error:
                        print(f"[PDF] FindIt lookup failed: {findit_error}")
                
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
        doi_hash = generate_doi_hash(doi)
        filename = f"{doi_hash}.pdf"
        filepath = os.path.join(save_dir, filename)
        
        # Check if file already exists
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                return True, f"File already exists: {filename} ({file_size} bytes)"
        
        # Download with proper headers
        # PMC and other publishers may require more realistic browser headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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
            # Log final URL after redirects
            if response.url != pdf_url:
                print(f"[PDF] Redirected to: {response.url}")
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                # For PMC URLs, sometimes the content-type might be missing or incorrect
                # Check if URL looks like a PDF URL and content starts with PDF magic bytes
                if pdf_url.endswith('.pdf') or '/pdf/' in pdf_url:
                    # Peek at first few bytes to check for PDF signature (%PDF)
                    first_chunk = next(response.iter_content(chunk_size=4), b'')
                    if first_chunk.startswith(b'%PDF'):
                        print(f"[PDF] Content-type is '{content_type}' but content is PDF (verified by signature)")
                        # Reset the response by making a new request
                        response = requests.get(pdf_url, headers=headers, proxies=proxies, timeout=30, stream=True, allow_redirects=True)
                    else:
                        return False, f"Response is not a PDF (content-type: {content_type})"
                else:
                    return False, f"Response is not a PDF (content-type: {content_type})"
            
            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
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
    Path(project_dir).mkdir(parents=True, exist_ok=True)
    
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
        
        doi_hash = generate_doi_hash(doi)
        filename = f"{doi_hash}.pdf"
        
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
    
    pdfs = []
    for filename in os.listdir(project_dir):
        if filename.endswith('.pdf'):
            filepath = os.path.join(project_dir, filename)
            pdfs.append({
                "filename": filename,
                "size": os.path.getsize(filepath),
                "path": filepath
            })
    
    return pdfs

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
