#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Additional PDF Download Sources
Lightweight implementations using REST APIs for Europe PMC, CORE, Semantic Scholar, and SciHub
"""

import requests
import re
from typing import Tuple, Optional, Dict, List
import time
import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
]

SCIHUB_MIRRORS = [
    'https://sci-hub.se',
    'https://sci-hub.st',
    'https://sci-hub.ru',
]

PUBLISHER_PREFIXES = {
    '10.1038': 'Nature Publishing Group',
    '10.1016': 'Elsevier',
    '10.1007': 'Springer',
    '10.1002': 'Wiley',
    '10.1093': 'Oxford University Press',
    '10.1371': 'PLOS',
    '10.1073': 'PNAS',  # Proceedings of the National Academy of Sciences
    '10.1177': 'SAGE Publications',
    '10.1080': 'Taylor & Francis',
    '10.3389': 'Frontiers',
    '10.1186': 'BioMed Central',
}


def get_random_user_agent() -> str:
    """Get a random User-Agent string for request rotation"""
    return random.choice(USER_AGENTS)


def extract_doi_prefix(doi: str) -> str:
    """Extract the publisher prefix from a DOI (e.g., '10.1371' from '10.1371/journal.pone.0000001')"""
    match = re.match(r'^(10\.\d+)', doi)
    return match.group(1) if match else ''


def get_publisher_name(doi: str) -> str:
    """Get publisher name from DOI prefix"""
    prefix = extract_doi_prefix(doi)
    return PUBLISHER_PREFIXES.get(prefix, 'Unknown Publisher')


def try_europe_pmc(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find PDF using Europe PMC REST API.
    Europe PMC provides access to life sciences literature.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # Search for article by DOI
        search_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        params = {
            'query': f'DOI:{doi}',
            'format': 'json',
            'resultType': 'core'
        }

        response = requests.get(search_url, params=params, headers=headers, timeout=timeout)

        if not response.ok:
            return False, f"Europe PMC API error: HTTP {response.status_code}"

        data = response.json()
        result_list = data.get('resultList', {})
        results = result_list.get('result', [])

        if not results:
            return False, "No results found in Europe PMC"

        article = results[0]

        # Check if full text is available
        has_pdf = article.get('hasPDF', 'N') == 'Y'
        is_open_access = article.get('isOpenAccess', 'N') == 'Y'

        if not (has_pdf or is_open_access):
            return False, "No open access PDF available in Europe PMC"

        # Try to get PDF link from full text URLs
        pmcid = article.get('pmcid')
        pmid = article.get('pmid')

        if pmcid:
            # Europe PMC format
            pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"
            return True, pdf_url
        elif pmid:
            # Try PMC format
            pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/pdf/"
            return True, pdf_url

        # Check for external links
        full_text_urls = article.get('fullTextUrlList', {}).get('fullTextUrl', [])
        for url_entry in full_text_urls:
            availability = url_entry.get('availability', '')
            url = url_entry.get('url', '')

            if 'free' in availability.lower() or 'open' in availability.lower():
                if url:
                    # Try to construct PDF URL
                    if 'europepmc.org' in url and pmcid:
                        pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"
                        return True, pdf_url
                    elif '.pdf' in url.lower():
                        return True, url

        return False, "Europe PMC: Article found but no accessible PDF link"

    except requests.Timeout:
        return False, "Europe PMC timeout"
    except Exception as e:
        return False, f"Europe PMC error: {str(e)}"


def try_core(doi: str, api_key: Optional[str] = None, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find PDF using CORE.ac.uk REST API.
    CORE aggregates open access research papers from repositories worldwide.

    Note: CORE API requires an API key for full access. Without a key, results may be limited.
    Get a free API key at: https://core.ac.uk/services/api

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # Add API key if provided
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'

        # Search for article by DOI
        search_url = "https://api.core.ac.uk/v3/search/works"
        params = {
            'q': f'doi:"{doi}"',
            'limit': 1
        }

        response = requests.get(search_url, params=params, headers=headers, timeout=timeout)

        if not response.ok:
            if response.status_code == 401:
                return False, "CORE API: Authentication required (API key needed)"
            elif response.status_code == 403:
                return False, "CORE API: Access forbidden"
            return False, f"CORE API error: HTTP {response.status_code}"

        data = response.json()
        results = data.get('results', [])

        if not results:
            return False, "No results found in CORE"

        article = results[0]

        # Check for download URL
        download_url = article.get('downloadUrl')
        if download_url and download_url.lower().endswith('.pdf'):
            return True, download_url

        # Check for full text link
        links = article.get('links', [])
        for link in links:
            link_type = link.get('type', '')
            url = link.get('url', '')

            if link_type == 'download' or '.pdf' in url.lower():
                return True, url

        # Check if display URL might be a PDF
        display_url = article.get('displayUrl')
        if display_url and '.pdf' in display_url.lower():
            return True, display_url

        return False, "CORE: Article found but no PDF download link"

    except requests.Timeout:
        return False, "CORE timeout"
    except Exception as e:
        return False, f"CORE error: {str(e)}"


def try_semantic_scholar(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find PDF using Semantic Scholar API.
    Semantic Scholar provides academic paper metadata and may have PDF links.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # Query by DOI
        api_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
        params = {
            'fields': 'title,openAccessPdf,isOpenAccess,externalIds'
        }

        response = requests.get(api_url, params=params, headers=headers, timeout=timeout)

        if not response.ok:
            if response.status_code == 404:
                return False, "Paper not found in Semantic Scholar"
            return False, f"Semantic Scholar API error: HTTP {response.status_code}"

        data = response.json()

        # Check for open access PDF
        is_open_access = data.get('isOpenAccess', False)
        open_access_pdf = data.get('openAccessPdf')

        if open_access_pdf and isinstance(open_access_pdf, dict):
            pdf_url = open_access_pdf.get('url')
            if pdf_url:
                return True, pdf_url

        if not is_open_access:
            return False, "Not open access according to Semantic Scholar"

        # Try ArXiv ID if available
        external_ids = data.get('externalIds', {})
        arxiv_id = external_ids.get('ArXiv')
        if arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return True, pdf_url

        return False, "Semantic Scholar: No PDF link available"

    except requests.Timeout:
        return False, "Semantic Scholar timeout"
    except Exception as e:
        return False, f"Semantic Scholar error: {str(e)}"


def try_scihub(doi: str, mirror_index: int = 0, timeout: int = 20) -> Tuple[bool, str]:
    """
    Try to find PDF using Sci-Hub (optional, use responsibly).

    IMPORTANT: Sci-Hub may not be legal in all jurisdictions. Use this source
    only as a last resort and ensure compliance with your local laws.
    This function is disabled by default in the database configuration.

    Args:
        doi: The DOI to search for
        mirror_index: Which Sci-Hub mirror to try (0-2)
        timeout: Request timeout in seconds

    Returns: (success, pdf_url or error_message)
    """
    try:
        if mirror_index >= len(SCIHUB_MIRRORS):
            return False, "All Sci-Hub mirrors exhausted"

        mirror = SCIHUB_MIRRORS[mirror_index]
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        # Request the DOI page
        scihub_url = f"{mirror}/{doi}"
        response = requests.get(scihub_url, headers=headers, timeout=timeout, allow_redirects=True)

        if not response.ok:
            # Try next mirror
            if mirror_index < len(SCIHUB_MIRRORS) - 1:
                return try_scihub(doi, mirror_index + 1, timeout)
            return False, f"Sci-Hub error: HTTP {response.status_code}"

        # Parse HTML to find PDF link
        content = response.text

        # Look for direct PDF link
        pdf_patterns = [
            r'<embed[^>]+src="([^"]+\.pdf[^"]*)"',
            r'<iframe[^>]+src="([^"]+\.pdf[^"]*)"',
            r'onclick="location\.href=\'([^\']+\.pdf[^\']*)\'',
            r'href="(//[^"]+\.pdf[^"]*)"',
        ]

        for pattern in pdf_patterns:
            match = re.search(pattern, content)
            if match:
                pdf_url = match.group(1)

                # Handle protocol-relative URLs
                if pdf_url.startswith('//'):
                    pdf_url = 'https:' + pdf_url

                # Handle relative URLs
                elif not pdf_url.startswith('http'):
                    pdf_url = mirror + pdf_url

                return True, pdf_url

        # Try next mirror if this one didn't work
        if mirror_index < len(SCIHUB_MIRRORS) - 1:
            return try_scihub(doi, mirror_index + 1, timeout)

        return False, "Sci-Hub: Could not extract PDF link from page"

    except requests.Timeout:
        # Try next mirror on timeout
        if mirror_index < len(SCIHUB_MIRRORS) - 1:
            return try_scihub(doi, mirror_index + 1, timeout)
        return False, "Sci-Hub timeout"
    except Exception as e:
        return False, f"Sci-Hub error: {str(e)}"


def try_biorxiv_medrxiv(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find PDF from bioRxiv or medRxiv preprint repositories.
    These are the main preprint servers for life sciences and medicine.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # bioRxiv/medRxiv use the same URL pattern
        # Check if it's a bioRxiv or medRxiv DOI
        if '10.1101' in doi:  # bioRxiv/medRxiv DOI prefix
            # Try constructing direct PDF URL
            # Format: https://www.biorxiv.org/content/10.1101/2021.01.01.12345v1.full.pdf
            # or: https://www.medrxiv.org/content/10.1101/2021.01.01.12345v1.full.pdf
            
            # Try bioRxiv first - use direct URL without HEAD check
            # (HEAD requests often fail even when PDF exists)
            pdf_url = f"https://www.biorxiv.org/content/{doi}.full.pdf"
            try:
                response = requests.head(pdf_url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    return True, pdf_url
            except requests.RequestException:
                pass  # Continue to try other methods
            
            # Try medRxiv
            pdf_url = f"https://www.medrxiv.org/content/{doi}.full.pdf"
            try:
                response = requests.head(pdf_url, headers=headers, timeout=timeout, allow_redirects=True)
                if response.status_code == 200:
                    return True, pdf_url
            except requests.RequestException:
                pass  # Continue to API check
        
        # Try bioRxiv API
        # bioRxiv/medRxiv content details API
        api_url = f"https://api.biorxiv.org/details/biorxiv/{doi}"
        try:
            response = requests.get(api_url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'collection' in data and len(data['collection']) > 0:
                    article = data['collection'][0]
                    # Construct PDF URL from article data
                    server = article.get('server', 'biorxiv')
                    doi_full = article.get('doi', doi)
                    pdf_url = f"https://www.{server}.org/content/{doi_full}.full.pdf"
                    return True, pdf_url
        except requests.RequestException:
            pass  # Continue to medRxiv API
        
        # Try medRxiv API
        api_url = f"https://api.biorxiv.org/details/medrxiv/{doi}"
        try:
            response = requests.get(api_url, headers=headers, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'collection' in data and len(data['collection']) > 0:
                    article = data['collection'][0]
                    server = article.get('server', 'medrxiv')
                    doi_full = article.get('doi', doi)
                    pdf_url = f"https://www.{server}.org/content/{doi_full}.full.pdf"
                    return True, pdf_url
        except requests.RequestException:
            pass  # All methods exhausted

        return False, "Not found in bioRxiv or medRxiv"

    except requests.Timeout:
        return False, "bioRxiv/medRxiv timeout"
    except Exception as e:
        return False, f"bioRxiv/medRxiv error: {str(e)}"


def try_arxiv_enhanced(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Enhanced arXiv integration with better DOI and ID handling.
    Supports both DOI-based and arXiv ID-based lookups.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}
        arxiv_id = None

        # Check if DOI contains arxiv
        if 'arxiv' in doi.lower():
            # Extract arXiv ID from DOI (e.g., "10.48550/arXiv.2101.00001", "arXiv:2103.00020")
            # Support multiple separators: '.', '/', ':', or none
            arxiv_match = re.search(r'arxiv[.:/]?(\d+\.\d+)', doi, re.IGNORECASE)
            if arxiv_match:
                arxiv_id = arxiv_match.group(1)
        else:
            # Try arXiv API to find by DOI
            api_url = f"http://export.arxiv.org/api/query?search_query=doi:{doi}&max_results=1"
            response = requests.get(api_url, headers=headers, timeout=timeout)
            
            if response.ok:
                content = response.text
                # Parse XML to find arXiv ID
                id_match = re.search(r'<id>http://arxiv\.org/abs/(\d+\.\d+)(v\d+)?</id>', content)
                if id_match:
                    arxiv_id = id_match.group(1)

        if arxiv_id:
            # Construct PDF URL
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            return True, pdf_url

        return False, "Not found in arXiv"

    except requests.Timeout:
        return False, "arXiv timeout"
    except Exception as e:
        return False, f"arXiv error: {str(e)}"


def try_pmc_enhanced(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Enhanced PubMed Central integration using E-utilities API.
    Better than metapub library for PMC access.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # Step 1: Convert DOI to PMCID using ID Converter API
        id_converter_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
        params = {
            'ids': doi,
            'format': 'json',
            'tool': 'harvest',
            'email': 'research@example.com'
        }
        
        response = requests.get(id_converter_url, params=params, headers=headers, timeout=timeout)
        
        if not response.ok:
            return False, f"PMC ID converter error: HTTP {response.status_code}"

        data = response.json()
        records = data.get('records', [])
        
        if not records:
            return False, "DOI not found in PubMed Central"

        record = records[0]
        
        # Check if article is available in PMC
        status = record.get('status', '')
        if status == 'error':
            return False, "Article not available in PMC"

        pmcid = record.get('pmcid')
        if not pmcid:
            return False, "No PMCID found for this DOI"

        # Step 2: Construct PMC PDF URL
        # Remove "PMC" prefix if present
        pmcid_num = pmcid.replace('PMC', '')
        
        # Try multiple PMC PDF URL formats
        pdf_urls = [
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid_num}/pdf/",
            f"https://europepmc.org/articles/PMC{pmcid_num}?pdf=render",
        ]

        for pdf_url in pdf_urls:
            # Quick check if URL is accessible
            head_response = requests.head(pdf_url, headers=headers, timeout=timeout, allow_redirects=True)
            if head_response.ok:
                return True, pdf_url

        # Return first URL even if check failed (might still work)
        return True, pdf_urls[0]

    except requests.Timeout:
        return False, "PMC timeout"
    except Exception as e:
        return False, f"PMC error: {str(e)}"


def try_zenodo(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find PDF from Zenodo repository.
    Zenodo is CERN's multidisciplinary open repository.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # Zenodo API endpoint
        # Search by DOI
        api_url = "https://zenodo.org/api/records"
        params = {
            'q': f'doi:"{doi}"',
            'size': 1
        }

        response = requests.get(api_url, params=params, headers=headers, timeout=timeout)

        if response.status_code != 200:
            return False, f"Zenodo API error: HTTP {response.status_code}"

        data = response.json()
        hits = data.get('hits', {}).get('hits', [])

        if not hits:
            return False, "Not found in Zenodo"

        record = hits[0]
        
        # Check if record has files
        # Zenodo API v3 structure has files as a list
        files = record.get('files', [])
        
        # Look for PDF files
        for file_info in files:
            filename = file_info.get('key', '').lower()
            file_type = file_info.get('type', '').lower()
            
            if filename.endswith('.pdf') or 'pdf' in file_type:
                # Try multiple locations for the download URL
                links = file_info.get('links', {})
                pdf_url = links.get('self') or links.get('download') or file_info.get('url')
                if pdf_url:
                    return True, pdf_url

        # If no direct PDF found in files list, check metadata for alternative structures
        # Some records might have files in metadata
        metadata = record.get('metadata', {})
        
        # Check for related identifiers that might point to PDFs
        related_identifiers = metadata.get('related_identifiers', [])
        for identifier in related_identifiers:
            if identifier.get('relation') == 'isSupplementTo' or identifier.get('relation') == 'isIdenticalTo':
                url = identifier.get('identifier', '')
                if '.pdf' in url.lower():
                    return True, url
        
        # If still no PDF, check links for download
        links = record.get('links', {})
        if 'files' in links:
            # Return the files endpoint URL
            return True, links['files']
        
        # Last resort: check for download link in record
        if 'download' in links:
            return True, links['download']

        return False, "No PDF file found in Zenodo record"

    except requests.Timeout:
        return False, "Zenodo timeout"
    except Exception as e:
        return False, f"Zenodo error: {str(e)}"


def try_doaj(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to find article in DOAJ (Directory of Open Access Journals).
    DOAJ indexes high-quality open access journals.

    Returns: (success, pdf_url or error_message)
    """
    try:
        headers = {'User-Agent': get_random_user_agent()}

        # DOAJ API endpoint
        api_url = "https://doaj.org/api/search/articles/doi"
        
        # Clean DOI (remove URL prefix if present)
        clean_doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
        
        # Search by DOI
        search_url = f"{api_url}:{clean_doi}"
        
        response = requests.get(search_url, headers=headers, timeout=timeout)

        if not response.ok:
            return False, f"DOAJ API error: HTTP {response.status_code}"

        data = response.json()
        results = data.get('results', [])

        if not results:
            return False, "Not found in DOAJ"

        article = results[0]
        bibjson = article.get('bibjson', {})

        # Look for fulltext link
        links = bibjson.get('link', [])
        for link in links:
            link_type = link.get('type', '').lower()
            url = link.get('url', '')
            
            if link_type == 'fulltext' and url:
                # Check if it's a PDF URL
                if url.lower().endswith('.pdf'):
                    return True, url
                # Otherwise return the fulltext page URL
                # (might redirect to PDF or have PDF download link)
                return True, url

        # Check identifier for additional URLs
        identifiers = bibjson.get('identifier', [])
        for ident in identifiers:
            if ident.get('type') == 'doi':
                doi_url = ident.get('id', '')
                if doi_url:
                    # DOAJ confirms it's OA, but we need to get PDF from publisher
                    return False, "DOAJ: Article is OA but no direct PDF link (try publisher)"

        return False, "DOAJ: No fulltext link found"

    except requests.Timeout:
        return False, "DOAJ timeout"
    except Exception as e:
        return False, f"DOAJ error: {str(e)}"


def try_publisher_direct(doi: str, timeout: int = 15) -> Tuple[bool, str]:
    """
    Try to construct direct publisher PDF URL based on known patterns.
    This works for some open access publishers with predictable URL structures.

    Returns: (success, pdf_url or error_message)
    """
    try:
        prefix = extract_doi_prefix(doi)
        publisher = get_publisher_name(doi)

        # PLOS (Public Library of Science)
        if prefix == '10.1371':
            # PLOS uses a predictable pattern
            # e.g., https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0000001&type=printable
            journal_match = re.search(r'journal\.(\w+)\.', doi)
            if journal_match:
                journal = journal_match.group(1)
                pdf_url = f"https://journals.plos.org/plos{journal}/article/file?id={doi}&type=printable"
                return True, pdf_url

        # Frontiers
        elif prefix == '10.3389':
            # Frontiers pattern: https://www.frontiersin.org/articles/10.3389/fpsyg.2020.00001/pdf
            pdf_url = f"https://www.frontiersin.org/articles/{doi}/pdf"
            return True, pdf_url

        # BioMed Central (BMC)
        elif prefix == '10.1186':
            # BMC pattern: https://link.springer.com/content/pdf/{doi}.pdf
            pdf_url = f"https://link.springer.com/content/pdf/{doi}.pdf"
            return True, pdf_url

        # PNAS (Proceedings of the National Academy of Sciences)
        elif prefix == '10.1073':
            # PNAS pattern: https://www.pnas.org/doi/pdf/{doi}?download=true
            # Example: 10.1073/pnas.0905754106 -> https://www.pnas.org/doi/pdf/10.1073/pnas.0905754106?download=true
            pdf_url = f"https://www.pnas.org/doi/pdf/{doi}?download=true"
            return True, pdf_url

        # ArXiv (handle arXiv DOIs) - use enhanced version instead
        if 'arxiv' in doi.lower():
            return try_arxiv_enhanced(doi, timeout)

        return False, f"No known direct pattern for publisher: {publisher}"

    except Exception as e:
        return False, f"Publisher direct error: {str(e)}"


def classify_failure(error_message: str, status_code: Optional[int] = None) -> str:
    """
    Classify the type of failure for better retry logic.

    Categories:
    - rate_limit: Too many requests, retry later
    - paywall: Behind paywall, needs institutional access or manual upload
    - not_found: Paper not found in this source
    - network_error: Connection issues, retry soon
    - invalid_pdf: Downloaded but not a valid PDF
    - timeout: Request timed out, retry soon
    - authentication: Requires authentication/API key
    - server_error: Server-side error, retry later
    """
    error_lower = error_message.lower()

    # Rate limiting
    if status_code == 429 or 'rate limit' in error_lower or 'too many requests' in error_lower:
        return 'rate_limit'

    # Authentication
    if status_code in [401, 403] or 'auth' in error_lower or 'forbidden' in error_lower or 'api key' in error_lower:
        return 'authentication'

    # Not found
    if status_code == 404 or 'not found' in error_lower or 'no results' in error_lower:
        return 'not_found'

    # Paywall
    if 'paywall' in error_lower or 'not open access' in error_lower or 'subscription required' in error_lower:
        return 'paywall'

    # Invalid content
    if 'not a pdf' in error_lower or 'invalid' in error_lower or 'too small' in error_lower:
        return 'invalid_pdf'

    # Timeout
    if 'timeout' in error_lower:
        return 'timeout'

    # Server errors
    if status_code and status_code >= 500:
        return 'server_error'

    # Network errors
    if 'connection' in error_lower or 'network' in error_lower:
        return 'network_error'

    # Default to network error for retryable issues
    return 'network_error'


def is_temporary_failure(failure_category: str) -> bool:
    """
    Determine if a failure is temporary and worth retrying.

    Temporary failures: rate_limit, timeout, network_error, server_error
    Permanent failures: paywall, not_found, invalid_pdf, authentication
    """
    temporary_categories = ['rate_limit', 'timeout', 'network_error', 'server_error']
    return failure_category in temporary_categories


def get_retry_delay_seconds(failure_category: str, retry_count: int = 0) -> int:
    """
    Get recommended delay in seconds before retry based on failure type.
    Uses exponential backoff.
    """
    base_delays = {
        'rate_limit': 300,      # 5 minutes base
        'timeout': 30,          # 30 seconds base
        'network_error': 60,    # 1 minute base
        'server_error': 120,    # 2 minutes base
    }

    base_delay = base_delays.get(failure_category, 60)

    # Exponential backoff: base * 2^retry_count, with jitter
    delay = base_delay * (2 ** retry_count)
    jitter = random.uniform(0, delay * 0.1)  # Add 0-10% jitter

    return int(delay + jitter)


if __name__ == "__main__":
    # Test the sources with known open access DOIs
    test_doi_plos = "10.1371/journal.pone.0000001"  # PLOS
    test_doi_arxiv = "10.48550/arXiv.2101.00001"  # arXiv
    
    print(f"Testing PDF sources with PLOS DOI: {test_doi_plos}\n")

    # Test Europe PMC
    print("1. Testing Europe PMC...")
    success, result = try_europe_pmc(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test CORE (without API key)
    print("2. Testing CORE...")
    success, result = try_core(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test Semantic Scholar
    print("3. Testing Semantic Scholar...")
    success, result = try_semantic_scholar(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test Publisher Direct
    print("4. Testing Publisher Direct...")
    success, result = try_publisher_direct(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test bioRxiv/medRxiv
    print("5. Testing bioRxiv/medRxiv...")
    biorxiv_doi = "10.1101/2021.01.01.425364"  # Example bioRxiv DOI
    success, result = try_biorxiv_medrxiv(biorxiv_doi)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test Enhanced arXiv
    print("6. Testing Enhanced arXiv...")
    success, result = try_arxiv_enhanced(test_doi_arxiv)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test Enhanced PMC
    print("7. Testing Enhanced PMC...")
    success, result = try_pmc_enhanced(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test Zenodo
    print("8. Testing Zenodo...")
    zenodo_doi = "10.5281/zenodo.1234567"  # Example Zenodo DOI
    success, result = try_zenodo(zenodo_doi)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test DOAJ
    print("9. Testing DOAJ...")
    success, result = try_doaj(test_doi_plos)
    print(f"   Success: {success}")
    print(f"   Result: {result}\n")

    # Test failure classification
    print("10. Testing failure classification...")
    test_errors = [
        ("HTTP 429", 429),
        ("Not found", 404),
        ("Not open access", None),
        ("Connection timeout", None),
        ("Response is not a PDF", None),
    ]
    for error_msg, status in test_errors:
        category = classify_failure(error_msg, status)
        is_temp = is_temporary_failure(category)
        print(f"   '{error_msg}' -> {category} (temporary: {is_temp})")
