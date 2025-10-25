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

try:
    from config import UNPAYWALL_EMAIL, ENABLE_METAPUB_FALLBACK, ENABLE_HABANERO_DOWNLOAD, HABANERO_PROXY_URL
except ImportError:
    UNPAYWALL_EMAIL = "research@example.com"
    ENABLE_METAPUB_FALLBACK = True
    ENABLE_HABANERO_DOWNLOAD = False
    HABANERO_PROXY_URL = ""

# Try importing optional libraries
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

def generate_doi_hash(doi: str) -> str:
    """Generate a hash from DOI for file naming"""
    return hashlib.sha256(doi.encode('utf-8')).hexdigest()[:16]

def check_open_access(doi: str, email: str = None) -> Tuple[bool, str]:
    """
    Check if a DOI is open access and get the download URL if available.
    Returns: (is_open_access, pdf_url or error_message)
    """
    # Check Unpaywall API for open access
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
                    return True, best_oa["url"]
            return False, "Not open access"
        else:
            return False, f"Unpaywall API error: {r.status_code}"
    except Exception as e:
        return False, f"Error checking open access: {str(e)}"

def try_metapub_download(doi: str) -> Tuple[bool, str]:
    """
    Try to find PDF using metapub (PubMed Central, arXiv, etc.)
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
        doi_hash = generate_doi_hash(doi)
        filename = f"{doi_hash}.pdf"
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
        
        response = requests.get(pdf_url, headers=headers, proxies=proxies, timeout=30, stream=True)
        
        if response.ok:
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
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
