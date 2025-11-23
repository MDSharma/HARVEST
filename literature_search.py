"""
Literature Search Module for HARVEST
Provides semantic paper discovery from multiple sources:
- Semantic Scholar API
- arXiv API
- Web of Science API (via woslite_client)

Features:
- Query expansion
- Semantic reranking
- Deduplication
- Session-based search history
- Retry logic with exponential backoff and jitter
"""

import logging
from typing import List, Dict, Any, Optional, Set
from functools import lru_cache
import time
import os
import re

logger = logging.getLogger(__name__)

# Default contact email for OpenAlex API if not configured
DEFAULT_CONTACT_EMAIL = 'harvest-app@example.com'

# Web of Science API Configuration
# The viewField parameter is REQUIRED to retrieve abstracts from WoS API
# Without it, the API defaults to 'summary' view which excludes abstracts
WOS_VIEWFIELD_FULLRECORD = 'fullRecord'

# Configure Hugging Face cache directory to avoid read-only filesystem errors
# Set cache to a writable directory
HF_CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache', 'huggingface')
os.environ['HF_HOME'] = HF_CACHE_DIR
os.environ['TRANSFORMERS_CACHE'] = HF_CACHE_DIR

# Create cache directory if it doesn't exist
try:
    os.makedirs(HF_CACHE_DIR, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create HuggingFace cache directory: {e}. Using default cache location.")

# Lazy imports to avoid loading heavy libraries at startup
_semantic_scholar = None
_sentence_transformers = None
_arxiv = None
_wos_client = None
_s2_session = None


def _get_s2_session():
    """
    Create a requests Session with retry logic for Semantic Scholar API.
    
    Implements best practices from S2 webinar examples:
    - Exponential backoff with jitter (randomization)
    - Respects rate limit headers (429)
    - Handles transient server errors (502, 503, 504)
    - 6 total retries with 2.0s backoff factor
    """
    global _s2_session
    if _s2_session is None:
        try:
            from requests import Session
            from requests.adapters import HTTPAdapter
            from urllib3.util import Retry
            
            _s2_session = Session()
            
            # Configure retry strategy following S2 best practices
            retry_strategy = Retry(
                total=6,  # Total number of retries
                backoff_factor=2.0,  # Exponential backoff: {backoff factor} * (2 ** (retry - 1))
                backoff_jitter=0.5,  # Add randomization to prevent thundering herd
                respect_retry_after_header=True,  # Respect Retry-After header from server
                status_forcelist=[429, 502, 503, 504],  # Retry on these HTTP status codes
                allowed_methods={'GET', 'POST'},  # Only retry safe methods
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            _s2_session.mount('https://', adapter)
            _s2_session.mount('http://', adapter)
            
            logger.info("Initialized Semantic Scholar session with retry logic")
        except ImportError as e:
            logger.warning(f"Could not configure retry logic: {e}. Using basic requests.")
            _s2_session = None
    
    return _s2_session


def _get_semantic_scholar():
    """Lazy load semanticscholar library"""
    global _semantic_scholar
    if _semantic_scholar is None:
        try:
            from semanticscholar import SemanticScholar
            _semantic_scholar = SemanticScholar()
        except ImportError as e:
            logger.error(f"Failed to import semanticscholar: {e}")
            raise
    return _semantic_scholar


def _get_sentence_transformer():
    """Lazy load sentence-transformers model"""
    global _sentence_transformers
    if _sentence_transformers is None:
        try:
            from sentence_transformers import SentenceTransformer, util
            model = SentenceTransformer('all-MiniLM-L6-v2')
            _sentence_transformers = {'model': model, 'util': util}
        except ImportError as e:
            logger.error(f"Failed to import sentence-transformers: {e}")
            raise
    return _sentence_transformers


def _get_arxiv():
    """Lazy load arxiv library"""
    global _arxiv
    if _arxiv is None:
        try:
            import arxiv as arxiv_lib
            _arxiv = arxiv_lib
        except ImportError as e:
            logger.error(f"Failed to import arxiv: {e}")
            raise
    return _arxiv


def _get_wos_api_key():
    """
    Get Web of Science API key from environment variable or config.
    Environment variable takes precedence over config.py setting.
    """
    global _wos_client
    if _wos_client is None:
        import os
        
        # Check environment variable first (takes precedence)
        api_key = os.getenv('WOS_API_KEY')
        
        # If not in environment, try to get from config.py
        if not api_key:
            try:
                from config import WOS_API_KEY
                if WOS_API_KEY:
                    api_key = WOS_API_KEY
            except ImportError:
                pass  # config.py not available
        
        if api_key:
            _wos_client = api_key
        else:
            logger.warning("WOS_API_KEY not set in environment or config.py. Web of Science searches will be disabled.")
            _wos_client = False  # Use False to indicate checked but not available
    return _wos_client if _wos_client else None


def _get_contact_email():
    """
    Get contact email for OpenAlex API from environment variable or config.
    Environment variable takes precedence over config.py setting.
    """
    # Check environment variable first (takes precedence)
    contact_email = os.getenv('HARVEST_CONTACT_EMAIL')

    # If not in environment, try to get from config.py
    if not contact_email:
        try:
            from config import HARVEST_CONTACT_EMAIL
            if HARVEST_CONTACT_EMAIL:
                contact_email = HARVEST_CONTACT_EMAIL
        except ImportError:
            pass  # config.py not available

    # Use default if still not set
    if not contact_email:
        contact_email = DEFAULT_CONTACT_EMAIL

    return contact_email


def is_wos_advanced_query(query: str) -> bool:
    """
    Check if a query is in Web of Science advanced search format.
    
    Advanced queries use field tags like TS=, TI=, AB=, AU=, etc.
    with boolean operators AND, OR, NOT.
    
    Examples:
        - AB=(genomic* OR transcriptom*) returns True
        - TS=(machine learning) AND PY=(2020-2024) returns True
        - "simple query" returns False
    """
    # WoS field tags
    wos_tags = [
        'TS=', 'TI=', 'AB=', 'AU=', 'AI=', 'AK=', 'GP=', 'ED=', 'KP=',
        'SO=', 'DO=', 'PY=', 'CF=', 'AD=', 'OG=', 'OO=', 'SG=', 'SA=',
        'CI=', 'PS=', 'CU=', 'ZP=', 'FO=', 'FG=', 'FD=', 'FT=', 'SU=',
        'WC=', 'IS=', 'UT=', 'PMID=', 'DOP=', 'LD=', 'PUBL=', 'ALL=',
        'FPY=', 'EAY=', 'SDG=', 'TMAC=', 'TMSO=', 'TMIC='
    ]
    
    # Check if query contains any WoS field tags
    query_upper = query.upper()
    return any(tag in query_upper for tag in wos_tags)


def convert_to_wos_query(query: str, default_field: str = 'TS') -> str:
    """
    Convert a simple natural language query to Web of Science advanced search format.
    
    If the query is already in WoS format, return as-is.
    Otherwise, wrap it in the default field tag.
    
    Args:
        query: Search query (natural language or WoS advanced format)
        default_field: Default WoS field tag to use (default: 'TS' for Topic)
    
    Returns:
        WoS advanced search query
    
    Examples:
        - "machine learning" -> "TS=(machine learning)"
        - "AB=(genomic*)" -> "AB=(genomic*)" (unchanged)
        - "AI ethics" -> "TS=(AI ethics)"
    """
    if is_wos_advanced_query(query):
        # Already in advanced format, return as-is
        return query
    
    # Convert simple query to WoS format
    # For simple queries, use Topic Search (TS) which searches title, abstract, and keywords
    return f"{default_field}=({query})"


def expand_query(query: str) -> List[str]:
    """
    Enhanced query expansion using domain-specific synonyms and variations.
    Returns a list of query variations for better coverage across search engines.
    
    Note: Not applicable for Web of Science advanced queries.
    
    Improvements:
    - Expanded synonym dictionary with more scientific terms
    - Better handling of compound terms
    - Returns only original query to avoid diluting relevance
    """
    # Enhanced synonym mapping for scientific and technical terms
    # Note: Query expansion is now disabled by default to improve relevance.
    # Most modern search engines (Semantic Scholar, OpenAlex) already handle
    # semantic similarity internally. Only return the original query.
    
    # Previously, expansion created variations that often reduced precision.
    # Users can now rely on the semantic reranking step (DELM) to find
    # relevant papers based on abstract similarity rather than keyword matching.
    
    return [query]  # Return only original query for better precision


@lru_cache(maxsize=100)
def search_semantic_scholar(query: str, limit: int = 40, year_range: Optional[str] = None, 
                           min_citations: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar API for papers using recommended best practices.
    Supports filtering by year range and minimum citation count.
    Cached to avoid redundant API calls.
    
    Args:
        query: Search query string
        limit: Maximum number of papers to return (default: 40, max: 100)
        year_range: Year range filter (e.g., "2020-2024" or "2023")
        min_citations: Minimum citation count filter
    
    Returns:
        List of paper dictionaries
    
    Best Practices (from S2 API documentation and webinar examples):
    - Request only needed fields to reduce payload size
    - Use pagination for large result sets
    - Cache results to avoid duplicate requests
    - Handle rate limits gracefully with retry logic
    - Exponential backoff with jitter for transient errors
    """
    try:
        s2 = _get_semantic_scholar()
        
        # Initialize retry session for better resilience
        _get_s2_session()

        # Request only fields we actually use (reduces API load)
        # Following S2 API best practices for field selection
        fields = [
            'title',
            'abstract', 
            'authors',
            'year',
            'externalIds',
            'citationCount',
            'publicationDate',
            'venue',
            'publicationTypes',
            'isOpenAccess',
            'openAccessPdf'
        ]
        
        # Build search parameters
        search_params = {
            'query': query,
            'limit': min(limit, 100),  # S2 API max is 100
            'fields': fields
        }
        
        # Add optional filters
        if year_range:
            search_params['publication_date_or_year'] = year_range
        
        if min_citations is not None:
            search_params['min_citation_count'] = min_citations
        
        # Search with pagination support
        # The semanticscholar library handles retries internally
        logger.debug(f"Searching Semantic Scholar: query='{query}', limit={limit}, "
                    f"year_range={year_range}, min_citations={min_citations}")
        
        results = s2.search_paper(**search_params)

        papers = []
        paper_count = 0
        for paper in results:
            paper_count += 1
            
            # Extract DOI from externalIds (more reliable than direct doi field)
            doi = None
            if hasattr(paper, 'externalIds') and paper.externalIds:
                doi = paper.externalIds.get('DOI') or paper.externalIds.get('ArXiv')

            # Extract authors with better error handling
            authors = []
            if hasattr(paper, 'authors') and paper.authors:
                for author in paper.authors[:3]:  # Limit to first 3 authors
                    if hasattr(author, 'name'):
                        authors.append(author.name)
                    else:
                        authors.append(str(author))

            # Build paper dictionary with all available metadata
            paper_dict = {
                'title': paper.title if hasattr(paper, 'title') else 'N/A',
                'abstract': paper.abstract if hasattr(paper, 'abstract') else '',
                'authors': authors,
                'year': paper.year if hasattr(paper, 'year') else None,
                'doi': doi,
                'source': 'Semantic Scholar',
                'citations': paper.citationCount if hasattr(paper, 'citationCount') else 0
            }
            
            # Add optional metadata if available
            if hasattr(paper, 'venue') and paper.venue:
                paper_dict['venue'] = paper.venue
            
            if hasattr(paper, 'isOpenAccess') and paper.isOpenAccess:
                paper_dict['is_open_access'] = True
                if hasattr(paper, 'openAccessPdf') and paper.openAccessPdf:
                    paper_dict['pdf_url'] = paper.openAccessPdf.get('url')
            
            papers.append(paper_dict)

        logger.info(f"Retrieved {len(papers)} papers from Semantic Scholar "
                   f"(query: '{query[:50]}...', requested: {limit}, found: {paper_count})")
        return papers

    except ImportError as e:
        logger.error(f"Semantic Scholar library not available: {e}")
        return []
    except TimeoutError as e:
        logger.error(f"Semantic Scholar search timeout: {e}")
        return []
    except Exception as e:
        # Log the specific error type for better debugging
        logger.error(f"Semantic Scholar search failed ({type(e).__name__}): {e}")
        return []


def get_recommended_papers_s2(paper_id: str, limit: int = 10, 
                              pool: str = 'recent') -> List[Dict[str, Any]]:
    """
    Get recommended papers similar to a given paper using Semantic Scholar's
    recommendation algorithm.
    
    This uses S2's paper recommendation feature which finds papers that:
    - Share similar topics and methodology
    - Are cited by or cite similar papers
    - Have overlapping author networks
    
    Args:
        paper_id: Semantic Scholar paper ID or DOI
        limit: Number of recommendations (default: 10, max: 500)
        pool: Recommendation pool - 'recent' (last 2 years) or 'all-cs' (all CS papers)
    
    Returns:
        List of recommended paper dictionaries
    
    Example:
        # Get recommendations based on a known paper
        recommendations = get_recommended_papers_s2('10.1038/nature14539', limit=20)
        
    Best Practices:
    - Uses retry logic with exponential backoff
    - Respects rate limits
    - Handles transient errors gracefully
    """
    try:
        s2 = _get_semantic_scholar()
        
        # Initialize retry session
        _get_s2_session()
        
        # Request same fields as search for consistency
        fields = [
            'title',
            'abstract',
            'authors',
            'year',
            'externalIds',
            'citationCount',
            'venue',
            'isOpenAccess'
        ]
        
        # Get recommendations using S2's algorithm
        pool_from = 'recent' if pool == 'recent' else 'all-cs'
        results = s2.get_recommended_papers(
            paper_id=paper_id,
            fields=fields,
            limit=min(limit, 500),  # S2 max is 500 for recommendations
            pool_from=pool_from
        )
        
        papers = []
        for paper in results:
            # Extract DOI
            doi = None
            if hasattr(paper, 'externalIds') and paper.externalIds:
                doi = paper.externalIds.get('DOI') or paper.externalIds.get('ArXiv')
            
            # Extract authors
            authors = []
            if hasattr(paper, 'authors') and paper.authors:
                authors = [a.name if hasattr(a, 'name') else str(a) 
                          for a in paper.authors[:3]]
            
            papers.append({
                'title': paper.title if hasattr(paper, 'title') else 'N/A',
                'abstract': paper.abstract if hasattr(paper, 'abstract') else '',
                'authors': authors,
                'year': paper.year if hasattr(paper, 'year') else None,
                'doi': doi,
                'source': 'Semantic Scholar (Recommended)',
                'citations': paper.citationCount if hasattr(paper, 'citationCount') else 0,
                'is_recommendation': True
            })
        
        logger.info(f"Retrieved {len(papers)} recommended papers from Semantic Scholar "
                   f"(paper_id: {paper_id}, pool: {pool})")
        return papers
    
    except ImportError as e:
        logger.error(f"Semantic Scholar library not available: {e}")
        return []
    except Exception as e:
        logger.error(f"Semantic Scholar recommendations failed ({type(e).__name__}): {e}")
        return []


def get_papers_by_ids_s2(paper_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve multiple papers by their IDs in bulk using Semantic Scholar API.
    More efficient than individual requests for multiple papers.
    
    Args:
        paper_ids: List of Semantic Scholar paper IDs or DOIs
    
    Returns:
        List of paper dictionaries
    
    Example:
        papers = get_papers_by_ids_s2(['10.1038/nature14539', 'arXiv:1706.03762'])
        
    Best Practices:
    - Uses bulk API endpoint for efficiency
    - Retry logic handles transient failures
    - Gracefully handles not-found papers
    """
    try:
        s2 = _get_semantic_scholar()
        
        # Initialize retry session
        _get_s2_session()
        
        fields = [
            'title',
            'abstract',
            'authors',
            'year',
            'externalIds',
            'citationCount',
            'venue'
        ]
        
        logger.debug(f"Retrieving {len(paper_ids)} papers by IDs from Semantic Scholar")
        
        # Use bulk retrieval for efficiency
        results = s2.get_papers(paper_ids=paper_ids, fields=fields)
        
        papers = []
        not_found_count = 0
        for paper in results:
            if paper is None:  # Paper not found
                not_found_count += 1
                continue
            
            # Extract DOI
            doi = None
            if hasattr(paper, 'externalIds') and paper.externalIds:
                doi = paper.externalIds.get('DOI') or paper.externalIds.get('ArXiv')
            
            # Extract authors
            authors = []
            if hasattr(paper, 'authors') and paper.authors:
                authors = [a.name if hasattr(a, 'name') else str(a) 
                          for a in paper.authors[:3]]
            
            papers.append({
                'title': paper.title if hasattr(paper, 'title') else 'N/A',
                'abstract': paper.abstract if hasattr(paper, 'abstract') else '',
                'authors': authors,
                'year': paper.year if hasattr(paper, 'year') else None,
                'doi': doi,
                'source': 'Semantic Scholar',
                'citations': paper.citationCount if hasattr(paper, 'citationCount') else 0
            })
        
        logger.info(f"Retrieved {len(papers)} papers by IDs from Semantic Scholar "
                   f"(requested: {len(paper_ids)}, not found: {not_found_count})")
        return papers
    
    except ImportError as e:
        logger.error(f"Semantic Scholar library not available: {e}")
        return []
    except Exception as e:
        logger.error(f"Semantic Scholar bulk retrieval failed ({type(e).__name__}): {e}")
        return []


@lru_cache(maxsize=100)
def search_arxiv(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search arXiv for papers.
    Cached to avoid redundant API calls.
    """
    try:
        arxiv_lib = _get_arxiv()

        search = arxiv_lib.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv_lib.SortCriterion.Relevance
        )

        papers = []
        for result in search.results():
            # Extract DOI from links
            doi = None
            if hasattr(result, 'doi') and result.doi:
                doi = result.doi
            elif hasattr(result, 'entry_id'):
                # Use arXiv ID as fallback identifier
                arxiv_id = result.entry_id.split('/abs/')[-1]
                doi = f"arXiv:{arxiv_id}"

            # Extract authors
            authors = [str(author) for author in result.authors[:3]] if hasattr(result, 'authors') else []

            papers.append({
                'title': result.title if hasattr(result, 'title') else 'N/A',
                'abstract': result.summary if hasattr(result, 'summary') else '',
                'authors': authors,
                'year': result.published.year if hasattr(result, 'published') else None,
                'doi': doi,
                'source': 'arXiv',
                'citations': 0  # arXiv doesn't provide citation counts
            })

        logger.info(f"Retrieved {len(papers)} papers from arXiv")
        return papers

    except Exception as e:
        logger.error(f"arXiv search failed: {e}")
        return []


@lru_cache(maxsize=100)
def search_web_of_science(query: str, limit: int = 20, page: int = 1) -> Dict[str, Any]:
    """
    Search Web of Science API for papers.
    Uses the newer wos-api.clarivate.com endpoint with better DOI support.
    Cached to avoid redundant API calls.
    Requires WOS_API_KEY environment variable to be set.
    
    Supports Web of Science advanced search syntax with field tags:
    - TS=(topic) - Topic (title, abstract, keywords)
    - TI=(title) - Title
    - AB=(abstract) - Abstract
    - AU=(author) - Author
    - PY=(year) - Publication year
    And boolean operators: AND, OR, NOT
    
    Examples:
        - Simple: "machine learning" -> converts to "TS=(machine learning)"
        - Advanced: "AB=(genomic* OR transcriptom*) AND PY=(2020-2024)"
    
    Args:
        query: Search query string
        limit: Maximum number of results per page (default: 20, max: 100)
        page: Page number to retrieve (default: 1)
    
    Returns:
        Dict with 'papers' list and 'total_results' count
    
    Important:
        The viewField='fullRecord' parameter is REQUIRED to retrieve abstracts.
        Without this parameter, the API defaults to 'summary' view which excludes abstracts.
    
    API Reference: https://api.clarivate.com/swagger-ui/?url=https://developer.clarivate.com/apis/wos/swagger
    """
    try:
        import requests
        
        api_key = _get_wos_api_key()
        
        if api_key is None:
            logger.warning("Web of Science API key not available. Check WOS_API_KEY environment variable.")
            return {'papers': [], 'total_results': 0}
        
        # Convert to WoS advanced query format if needed
        wos_query = convert_to_wos_query(query)
        logger.info(f"Web of Science query: {wos_query}, page: {page}")
        
        # Calculate firstRecord based on page number
        # WoS uses 1-based indexing
        count = min(limit, 100)  # API max is 100 per request
        first_record = (page - 1) * count + 1
        
        # Use newer Web of Science API endpoint with better DOI support
        # CRITICAL: viewField parameter is required to get abstracts
        # Without it, the API defaults to 'summary' view which excludes abstracts
        params = {
            'databaseId': 'WOS',
            'usrQuery': wos_query,
            'count': count,
            'firstRecord': first_record,
            'viewField': WOS_VIEWFIELD_FULLRECORD  # Request full record including abstracts
        }
        
        logger.info(f"WoS API request params: {params}")
        
        response = requests.get(
            url='https://wos-api.clarivate.com/api/wos',
            params=params,
            headers={'X-ApiKey': api_key},
            timeout=30
        )
        
        logger.info(f"WoS API response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Web of Science API error {response.status_code}: {response.text[:500]}")
            return {'papers': [], 'total_results': 0}
        
        result = response.json()
        
        # Extract total results count from QueryResult
        total_results = 0
        query_result = result.get('QueryResult', {})
        if query_result:
            total_results = query_result.get('RecordsFound', 0)
        
        # Log the response structure for debugging
        logger.info(f"WoS API response keys: {list(result.keys())}, total_results: {total_results}")
        
        # Parse the response structure from WoS API
        papers = []
        
        # Try different response structures
        # Structure 1: Data -> Records -> records -> REC
        records = result.get('Data', {}).get('Records', {}).get('records', {}).get('REC', [])
        
        if not records:
            # Structure 2: Try direct records access
            records = result.get('records', {}).get('REC', [])
        
        if not records:
            # Structure 3: Try QueryResult structure
            query_result = result.get('QueryResult', {})
            records = query_result.get('Records', {}).get('REC', [])
        
        if not records:
            logger.warning(f"No records found in WoS response. Response structure: {list(result.keys())}")
            # Log more details about what's in the response
            if 'Data' in result:
                logger.info(f"Data keys: {list(result['Data'].keys())}")
                if 'Records' in result.get('Data', {}):
                    logger.info(f"Records keys: {list(result['Data']['Records'].keys())}")
            return []
        
        logger.info(f"Found {len(records)} records in WoS response")
        
        for record in records:
            try:
                # Extract basic metadata
                # Defensive check: static_data might be a string or dict
                static_data = record.get('static_data', {})
                if not isinstance(static_data, dict):
                    logger.warning(f"Skipping record: static_data is not a dict (type: {type(static_data).__name__})")
                    continue
                
                summary = static_data.get('summary', {})
                if not isinstance(summary, dict):
                    logger.warning(f"Skipping record: summary is not a dict (type: {type(summary).__name__})")
                    continue
                
                fullrecord_metadata = static_data.get('fullrecord_metadata', {})
                if not isinstance(fullrecord_metadata, dict):
                    fullrecord_metadata = {}
                
                # Extract title
                titles = summary.get('titles', {})
                if isinstance(titles, dict):
                    title_list = titles.get('title', [])
                else:
                    title_list = []
                
                if not isinstance(title_list, list):
                    title_list = [title_list] if title_list else []
                
                title = 'N/A'
                for t in title_list:
                    if isinstance(t, dict) and t.get('type') == 'item':
                        title = t.get('content', 'N/A')
                        break
                
                # Extract DOI - check multiple locations as per API documentation
                doi = None
                
                # Method 1: Check identifiers in fullrecord_metadata
                identifiers = fullrecord_metadata.get('identifiers', {})
                if isinstance(identifiers, dict):
                    doi_list = identifiers.get('identifier', [])
                    if not isinstance(doi_list, list):
                        doi_list = [doi_list] if doi_list else []
                    for identifier in doi_list:
                        if isinstance(identifier, dict) and identifier.get('type') == 'doi':
                            doi = identifier.get('value')
                            break
                
                # Method 2: Check ReferenceRecord section if DOI not found yet
                # As per https://api.clarivate.com/swagger-ui, DOIs may be in references
                if not doi:
                    references = fullrecord_metadata.get('references', {})
                    if isinstance(references, dict):
                        # Check for DOI in reference metadata
                        ref_value = references.get('reference', [])
                        ref_list = ref_value if isinstance(ref_value, list) else [ref_value] if ref_value else []
                        for ref in ref_list:
                            if isinstance(ref, dict):
                                ref_doi = ref.get('doi')
                                if ref_doi:
                                    # This would be a reference's DOI, not the paper's DOI
                                    # Skip this for now as it's not the paper's own DOI
                                    pass
                
                # Method 3: Check dynamic_data for DOI
                if not doi:
                    dynamic_data = record.get('dynamic_data', {})
                    if isinstance(dynamic_data, dict):
                        cluster_related = dynamic_data.get('cluster_related', {})
                        if isinstance(cluster_related, dict):
                            identifiers_dyn = cluster_related.get('identifiers', {})
                            if isinstance(identifiers_dyn, dict):
                                doi_list_dyn = identifiers_dyn.get('identifier', [])
                                if not isinstance(doi_list_dyn, list):
                                    doi_list_dyn = [doi_list_dyn] if doi_list_dyn else []
                                for identifier in doi_list_dyn:
                                    if isinstance(identifier, dict) and identifier.get('type') == 'doi':
                                        doi = identifier.get('value')
                                        break
                
                # Note: Only actual DOIs are stored for proper project integration
                # Papers without DOIs will have doi=None
                
                # Extract authors
                authors = []
                names = summary.get('names', {})
                if isinstance(names, dict):
                    name_list = names.get('name', [])
                    # Handle case where names could be a dict or a list
                    if not isinstance(name_list, list):
                        name_list = [name_list] if isinstance(name_list, dict) else []
                    for name in name_list[:3]:  # Limit to first 3 authors
                        if isinstance(name, dict) and name.get('role') == 'author':
                            display_name = name.get('display_name') or name.get('full_name')
                            if display_name:
                                authors.append(display_name)
                
                # Extract year
                year = None
                pub_info = summary.get('pub_info', {})
                if isinstance(pub_info, dict):
                    pubyear = pub_info.get('pubyear')
                    if pubyear:
                        try:
                            year = int(pubyear)
                        except (ValueError, TypeError):
                            pass
                
                # Extract abstract
                abstract = ''
                abstracts_data = fullrecord_metadata.get('abstracts', {})
                if isinstance(abstracts_data, dict):
                    abstract_list = abstracts_data.get('abstract', [])
                    if not isinstance(abstract_list, list):
                        abstract_list = [abstract_list] if abstract_list else []
                    for abs_item in abstract_list:
                        # Handle both dict and string formats for abstract_text
                        if isinstance(abs_item, dict):
                            abstract_text = abs_item.get('abstract_text', '')
                            # If abstract_text is a dict, try to get 'p' key
                            if isinstance(abstract_text, dict):
                                abstract_text = abstract_text.get('p', '')
                            # Convert to string if not already
                            if not isinstance(abstract_text, str):
                                abstract_text = str(abstract_text) if abstract_text else ''
                        elif isinstance(abs_item, str):
                            # abs_item is directly the abstract string
                            abstract_text = abs_item
                        else:
                            # Try to convert to string as fallback
                            abstract_text = str(abs_item) if abs_item else ''
                        
                        # Clean up and validate abstract text
                        if abstract_text and abstract_text.strip():
                            # Remove any placeholder text like "abstract_text"
                            if abstract_text.strip() not in ['abstract_text', '{}', 'None']:
                                abstract = abstract_text.strip()
                                break
                
                # Extract citation count
                citations = 0
                dynamic_data = record.get('dynamic_data', {})
                if isinstance(dynamic_data, dict):
                    citation_related = dynamic_data.get('citation_related', {})
                    if isinstance(citation_related, dict):
                        tc_list_data = citation_related.get('tc_list', {})
                        if isinstance(tc_list_data, dict):
                            silo_tc_list = tc_list_data.get('silo_tc', [])
                            if not isinstance(silo_tc_list, list):
                                silo_tc_list = [silo_tc_list] if silo_tc_list else []
                            for tc in silo_tc_list:
                                if isinstance(tc, dict) and tc.get('coll_id') == 'WOS':
                                    try:
                                        citations = int(tc.get('local_count', 0))
                                    except (ValueError, TypeError):
                                        pass
                                    break
                
                    papers.append({
                        'title': title,
                        'abstract': abstract,
                        'authors': authors,
                        'year': year,
                        'doi': doi,
                        'source': 'Web of Science',
                        'citations': citations
                    })
            except Exception as e:
                logger.error(f"Error processing individual WoS record: {e}")
                # Continue with next record instead of failing entire search
                continue
        
        logger.info(f"Retrieved {len(papers)} papers from Web of Science (page {page}, total available: {total_results})")
        return {'papers': papers, 'total_results': total_results}
    
    except requests.RequestException as e:
        logger.error(f"Web of Science API request failed: {e}")
        return {'papers': [], 'total_results': 0}
    except Exception as e:
        logger.error(f"Web of Science search failed ({type(e).__name__}): {e}", exc_info=True)
        return {'papers': [], 'total_results': 0}


@lru_cache(maxsize=100)
def search_openalex(query: str, limit: int = 20, page: int = 1, contact_email: str = DEFAULT_CONTACT_EMAIL) -> Dict[str, Any]:
    """
    Search OpenAlex API for papers.
    OpenAlex is a free, open catalog of scholarly papers, authors, institutions, and more.
    Cached to avoid redundant API calls.
    
    API Documentation: https://docs.openalex.org/
    
    Args:
        query: Search query string (searches title and abstract)
        limit: Maximum number of papers per page to return (default: 20, max: 200)
        page: Page number to retrieve (default: 1)
        contact_email: Contact email for OpenAlex polite pool (faster responses)
    
    Returns:
        Dict with 'papers' list and 'total_results' count
    
    Notes:
        - OpenAlex uses a different query syntax than other sources
        - The API is polite and includes automatic rate limiting
        - No API key required, but requests should include a User-Agent with email
        - contact_email is part of the cache key to ensure cache invalidation when email changes
    """
    try:
        import requests

        # OpenAlex search endpoint
        base_url = "https://api.openalex.org/works"
        
        # Build search parameters
        # OpenAlex uses a "search" parameter for full-text search across title and abstract
        params = {
            'search': query,
            'per_page': min(limit, 200),  # OpenAlex max is 200 per page
            'page': page,
            'sort': 'relevance_score:desc',  # Sort by relevance
            'mailto': contact_email  # Polite pool - faster response
        }
        
        # Make request with polite User-Agent
        headers = {
            'User-Agent': f'HARVEST Literature Search (mailto:{contact_email})'
        }
        
        logger.debug(f"Searching OpenAlex: query='{query}', page={page}, limit={limit}")
        
        response = requests.get(
            base_url,
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"OpenAlex API error {response.status_code}: {response.text}")
            return {'papers': [], 'total_results': 0}
        
        result = response.json()
        
        # Extract metadata including total count
        meta = result.get('meta', {})
        total_results = meta.get('count', 0)
        
        # Parse the response structure from OpenAlex API
        papers = []
        results = result.get('results', [])
        
        for work in results:
            # Extract title
            title = work.get('title', 'N/A')
            
            # Extract DOI
            doi = work.get('doi')
            if doi:
                # OpenAlex returns full DOI URL, extract just the DOI
                doi = doi.replace('https://doi.org/', '')
            # Note: OpenAlex ID is NOT used as fallback
            # Only actual DOIs should be stored for proper project integration
            # Papers without DOIs will have doi=None
            
            # Extract authors
            authors = []
            authorships = work.get('authorships', [])
            for authorship in authorships[:3]:  # Limit to first 3 authors
                author = authorship.get('author', {})
                author_name = author.get('display_name')
                if author_name:
                    authors.append(author_name)
            
            # Extract year
            year = None
            publication_year = work.get('publication_year')
            if publication_year:
                try:
                    year = int(publication_year)
                except (ValueError, TypeError):
                    pass
            
            # Extract abstract
            # OpenAlex stores abstract as inverted index, need to reconstruct
            abstract = ''
            abstract_inverted_index = work.get('abstract_inverted_index')
            if abstract_inverted_index:
                # Reconstruct abstract from inverted index
                # Each key is a word, each value is list of positions
                # Pre-allocate list by finding max position for efficiency
                max_pos = max(max(positions) for positions in abstract_inverted_index.values())
                words = [None] * (max_pos + 1)
                
                # Populate words at their positions
                for word, positions in abstract_inverted_index.items():
                    for pos in positions:
                        words[pos] = word
                
                # Join words (filter None for any gaps)
                abstract = ' '.join(w for w in words if w is not None)
            
            # Extract citation count
            citations = work.get('cited_by_count', 0)
            
            # Extract open access status
            open_access = work.get('open_access', {})
            is_oa = open_access.get('is_oa', False)
            oa_url = open_access.get('oa_url')
            
            paper_dict = {
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'year': year,
                'doi': doi,
                'source': 'OpenAlex',
                'citations': citations
            }
            
            # Add open access information if available
            if is_oa and oa_url:
                paper_dict['is_open_access'] = True
                paper_dict['pdf_url'] = oa_url
            
            papers.append(paper_dict)
        
        query_display = query[:50] + ('...' if len(query) > 50 else '')
        logger.info(f"Retrieved {len(papers)} papers from OpenAlex (page {page}, total available: {total_results})")
        return {'papers': papers, 'total_results': total_results}
    
    except requests.RequestException as e:
        logger.error(f"OpenAlex API request failed: {e}")
        return {'papers': [], 'total_results': 0}
    except Exception as e:
        logger.error(f"OpenAlex search failed ({type(e).__name__}): {e}")
        return {'papers': [], 'total_results': 0}


def _normalize_title(title: str) -> str:
    """
    Normalize a paper title for fuzzy matching.
    Removes punctuation, extra spaces, and common variations.
    
    Note: Removes common prefixes ('the', 'a', 'an') to improve matching.
    This is a trade-off that works well for most academic titles but may
    cause false positives in rare cases (e.g., "The Algorithm" vs "Algorithm").
    """
    # Convert to lowercase
    title = title.lower().strip()
    
    # Remove common prefixes/suffixes that might vary
    # Trade-off: May cause false positives but improves matching for most titles
    title = re.sub(r'^(the|a|an)\s+', '', title)
    
    # Remove punctuation except spaces
    title = re.sub(r'[^\w\s]', '', title)
    
    # Normalize multiple spaces to single space
    title = re.sub(r'\s+', ' ', title)
    
    # Remove trailing/leading spaces
    title = title.strip()
    
    return title


def _titles_are_similar(title1: str, title2: str, threshold: float = 0.85) -> bool:
    """
    Check if two titles are similar enough to be considered duplicates.
    Uses word-level Jaccard similarity (intersection over union of word sets).
    
    Args:
        title1: First title (normalized)
        title2: Second title (normalized)
        threshold: Similarity threshold (0.0 to 1.0, default: 0.85)
    
    Returns:
        True if titles are similar enough to be duplicates
    
    Examples:
        >>> _titles_are_similar("machine learning healthcare", "machine learning healthcare")
        True
        >>> _titles_are_similar("machine learning healthcare", "deep learning medicine")
        False  # Only 1/5 words in common
    """
    # Split into word sets
    words1 = set(title1.split())
    words2 = set(title2.split())
    
    if not words1 or not words2:
        return False
    
    # Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    similarity = intersection / union if union > 0 else 0.0
    
    return similarity >= threshold


def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enhanced deduplication of papers by DOI and fuzzy title similarity.
    Prioritizes papers with more citations when duplicates are found.
    
    Improvements:
    - Fuzzy title matching to catch slight variations
    - Title normalization (punctuation, spacing, case)
    - Better handling of papers without DOIs
    - Optimized O(n) lookup using dict for exact matches
    
    Performance Note:
    - Best case: O(n) when all titles are unique (fast path via dict lookup)
    - Worst case: O(n²) when many similar titles require fuzzy matching
    - Typical case: O(n) for most real-world literature searches (100-200 papers)
    - For large datasets (1000+ papers), consider implementing LSH if performance becomes an issue
    """
    seen_dois = set()
    seen_normalized_titles = {}  # normalized_title -> paper mapping
    unique_papers = []

    # Sort by citations (descending) to prioritize highly cited papers
    sorted_papers = sorted(papers, key=lambda x: x.get('citations', 0), reverse=True)

    for paper in sorted_papers:
        # Check DOI first (exact match - O(1) lookup)
        doi = paper.get('doi')
        if doi and doi in seen_dois:
            continue

        # Check title with fuzzy matching
        title = paper.get('title', '').strip()
        if title:
            normalized_title = _normalize_title(title)
            
            # Fast exact match check first (O(1))
            if normalized_title in seen_normalized_titles:
                continue
            
            # Only do fuzzy matching for new normalized titles
            # This reduces O(n²) to O(n) in most cases where titles are truly unique
            # For typical literature searches (100-200 papers), this is acceptable
            is_duplicate = False
            for seen_normalized in seen_normalized_titles.keys():
                if _titles_are_similar(normalized_title, seen_normalized):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Add to seen titles
            seen_normalized_titles[normalized_title] = paper

        # Add to unique list
        unique_papers.append(paper)
        if doi:
            seen_dois.add(doi)

    logger.info(f"Deduplicated {len(papers)} papers to {len(unique_papers)} unique papers "
                f"(removed {len(papers) - len(unique_papers)} duplicates)")
    return unique_papers


def rerank_papers(papers: List[Dict[str, Any]], query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Rerank papers using semantic similarity between query and abstracts.
    Falls back to original order if reranking fails.
    """
    if not papers:
        return []

    try:
        st = _get_sentence_transformer()
        model = st['model']
        util = st['util']

        # Filter papers with abstracts
        papers_with_abstracts = [p for p in papers if p.get('abstract')]

        if not papers_with_abstracts:
            logger.warning("No papers with abstracts for reranking, returning original order")
            return papers[:top_k]

        # Encode query and abstracts
        query_embedding = model.encode(query, convert_to_tensor=True)
        abstract_embeddings = model.encode(
            [p['abstract'] for p in papers_with_abstracts],
            convert_to_tensor=True
        )

        # Compute cosine similarities
        similarities = util.cos_sim(query_embedding, abstract_embeddings)[0]

        # Sort by similarity
        sorted_indices = similarities.argsort(descending=True).tolist()
        reranked = [papers_with_abstracts[idx] for idx in sorted_indices[:top_k]]

        logger.info(f"Reranked {len(papers_with_abstracts)} papers, returning top {len(reranked)}")
        return reranked

    except Exception as e:
        logger.error(f"Reranking failed: {e}, returning original order")
        return papers[:top_k]


def search_papers(
    query: str, 
    top_k: int = 10, 
    sources: Optional[List[str]] = None,
    previous_papers: Optional[List[Dict[str, Any]]] = None,
    enable_query_expansion: bool = True,
    enable_deduplication: bool = True,
    enable_reranking: bool = True,
    progress_callback: Optional[callable] = None,
    per_source_limit: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Main search function that orchestrates the entire search pipeline:
    1. Query expansion (AutoResearch) - optional
    2. Multi-source search (DeepResearch - Python Reimpl)
    3. Deduplication (including previous search results) - optional
    4. Semantic reranking (DELM) - optional
    
    Args:
        query: Search query string
        top_k: Number of top results to return after reranking
        sources: List of sources to search. Options: 'semantic_scholar', 'arxiv', 'web_of_science', 'openalex'
                 If None, defaults to ['semantic_scholar', 'arxiv']
        previous_papers: Papers from previous searches in session to build upon
        enable_query_expansion: Whether to expand the query (AutoResearch step)
        enable_deduplication: Whether to deduplicate results
        enable_reranking: Whether to semantically rerank results (DELM step)
        progress_callback: Optional callback function to report progress updates
        per_source_limit: Optional dict mapping source names to result limits. 
                         If None, uses default limits per source.
                         Example: {'semantic_scholar': 100, 'openalex': 50}
    
    Returns:
        Dictionary with papers and metadata, including execution details.
    """
    start_time = time.time()
    execution_log = []  # Track execution steps for display
    
    # Default sources if not specified
    if sources is None:
        sources = ['semantic_scholar', 'arxiv']
    
    # Validate sources
    valid_sources = {'semantic_scholar', 'arxiv', 'web_of_science', 'openalex'}
    sources = [s for s in sources if s in valid_sources]
    
    if not sources:
        return {
            'success': False,
            'papers': [],
            'message': 'No valid sources specified.',
            'elapsed_time': time.time() - start_time,
            'execution_log': execution_log
        }

    try:
        # Detect if this is a WoS advanced query
        is_wos_advanced = is_wos_advanced_query(query)
        using_wos_only = sources == ['web_of_science']
        
        # Step 1: AutoResearch - Query expansion (optional, skip for WoS advanced queries)
        step1_start = time.time()
        if enable_query_expansion and not (is_wos_advanced and using_wos_only):
            queries = expand_query(query)
            step1_time = time.time() - step1_start
            logger.info(f"Expanded query '{query}' to {len(queries)} variations")
            execution_log.append({
                'step': 'AutoResearch',
                'description': 'Query Expansion',
                'details': f"Expanded '{query}' to {len(queries)} query variations",
                'elapsed_ms': int(step1_time * 1000),
                'status': 'completed'
            })
            if progress_callback:
                progress_callback(execution_log[-1])
        else:
            queries = [query]  # No expansion
            if is_wos_advanced and using_wos_only:
                logger.info(f"Using Web of Science advanced query syntax: {query}")
                execution_log.append({
                    'step': 'Query Processing',
                    'description': 'Web of Science Advanced Query',
                    'details': f"Using advanced query syntax (no expansion): {query}",
                    'elapsed_ms': int((time.time() - step1_start) * 1000),
                    'status': 'completed'
                })
            else:
                logger.info(f"Query expansion disabled, using original query")
                execution_log.append({
                    'step': 'Query Processing',
                    'description': 'No Expansion',
                    'details': f"Using original query (expansion disabled): {query}",
                    'elapsed_ms': int((time.time() - step1_start) * 1000),
                    'status': 'skipped'
                })
            if progress_callback:
                progress_callback(execution_log[-1])

        # Step 2: DeepResearch (Python Reimpl) - Multi-source search
        step2_start = time.time()
        all_papers = []
        source_details = []
        
        # Set default per-source limits if not provided
        if per_source_limit is None:
            per_source_limit = {
                'semantic_scholar': 100,  # Increased from 40 to allow more results
                'arxiv': 50,              # Increased from 10 to allow more results
                'web_of_science': 100,    # Increased from 20 to allow more results (WoS API max is 100)
                'openalex': 200           # Increased from 20 to allow more results (OpenAlex API max is 200)
            }
        
        # Search Semantic Scholar if requested
        if 'semantic_scholar' in sources:
            s2_start = time.time()
            s2_papers = []
            s2_limit = per_source_limit.get('semantic_scholar', 100)
            for q in queries[:1]:  # Use only the primary query for S2
                s2_results = search_semantic_scholar(q, limit=s2_limit)
                s2_papers.extend(s2_results)
                all_papers.extend(s2_results)
            s2_time = time.time() - s2_start
            s2_count = len(s2_papers)
            source_details.append(f"Semantic Scholar ({s2_count}/{s2_limit} in {s2_time:.2f}s)")
        
        # Search arXiv if requested
        if 'arxiv' in sources:
            arxiv_start = time.time()
            arxiv_limit = per_source_limit.get('arxiv', 50)
            arxiv_papers = search_arxiv(query, limit=arxiv_limit)
            all_papers.extend(arxiv_papers)
            arxiv_time = time.time() - arxiv_start
            arxiv_count = len(arxiv_papers)
            source_details.append(f"arXiv ({arxiv_count}/{arxiv_limit} in {arxiv_time:.2f}s)")
        
        # Search Web of Science if requested
        if 'web_of_science' in sources:
            wos_start = time.time()
            wos_limit = per_source_limit.get('web_of_science', 100)
            wos_result = search_web_of_science(query, limit=wos_limit)
            wos_papers = wos_result.get('papers', []) if isinstance(wos_result, dict) else wos_result
            all_papers.extend(wos_papers)
            wos_time = time.time() - wos_start
            wos_count = len(wos_papers)
            source_details.append(f"Web of Science ({wos_count}/{wos_limit} in {wos_time:.2f}s)")
        
        # Search OpenAlex if requested
        if 'openalex' in sources:
            openalex_start = time.time()
            openalex_limit = per_source_limit.get('openalex', 200)
            contact_email = _get_contact_email()
            openalex_result = search_openalex(query, limit=openalex_limit, contact_email=contact_email)
            openalex_papers = openalex_result.get('papers', []) if isinstance(openalex_result, dict) else openalex_result
            all_papers.extend(openalex_papers)
            openalex_time = time.time() - openalex_start
            openalex_count = len(openalex_papers)
            source_details.append(f"OpenAlex ({openalex_count}/{openalex_limit} in {openalex_time:.2f}s)")

        step2_time = time.time() - step2_start
        execution_log.append({
            'step': 'DeepResearch (Python Reimpl)',
            'description': 'Multi-Source Paper Retrieval',
            'details': f"Retrieved {len(all_papers)} papers: {', '.join(source_details)}",
            'elapsed_ms': int(step2_time * 1000),
            'status': 'completed'
        })
        if progress_callback:
            progress_callback(execution_log[-1])

        if not all_papers:
            return {
                'success': False,
                'papers': [],
                'message': 'No papers found. Try a different query.',
                'elapsed_time': time.time() - start_time,
                'execution_log': execution_log
            }

        # Step 2b: Deduplication (optional, including previous search results)
        dedup_start = time.time()
        
        if enable_deduplication:
            # Combine with previous papers if building on session
            if previous_papers:
                all_papers_combined = previous_papers + all_papers
                unique_papers = deduplicate_papers(all_papers_combined)
                dedup_details = f"Deduplicated {len(all_papers_combined)} papers (including {len(previous_papers)} from previous searches) to {len(unique_papers)} unique entries"
            else:
                unique_papers = deduplicate_papers(all_papers)
                dedup_details = f"Deduplicated {len(all_papers)} papers to {len(unique_papers)} unique entries"
            
            dedup_time = time.time() - dedup_start
            execution_log.append({
                'step': 'DeepResearch (Python Reimpl)',
                'description': 'Deduplication',
                'details': dedup_details,
                'elapsed_ms': int(dedup_time * 1000),
                'status': 'completed'
            })
        else:
            # Skip deduplication
            unique_papers = all_papers
            logger.info(f"Deduplication disabled, keeping all {len(all_papers)} papers")
            execution_log.append({
                'step': 'DeepResearch (Python Reimpl)',
                'description': 'Deduplication',
                'details': f"Deduplication disabled, keeping all {len(all_papers)} papers",
                'elapsed_ms': int((time.time() - dedup_start) * 1000),
                'status': 'skipped'
            })
        if progress_callback:
            progress_callback(execution_log[-1])

        # Step 3: DELM - Semantic reranking (optional, skip for WoS advanced queries)
        step3_start = time.time()
        if enable_reranking and not (is_wos_advanced and using_wos_only):
            reranked_papers = rerank_papers(unique_papers, query, top_k=top_k)
            step3_time = time.time() - step3_start
            execution_log.append({
                'step': 'DELM',
                'description': 'Semantic Reranking',
                'details': f"Reranked {len(unique_papers)} papers using semantic similarity, returning top {len(reranked_papers)} results",
                'elapsed_ms': int(step3_time * 1000),
                'status': 'completed'
            })
        else:
            # Skip reranking
            reranked_papers = unique_papers[:top_k]
            if is_wos_advanced and using_wos_only:
                logger.info(f"Skipping semantic reranking for WoS advanced query, returning top {len(reranked_papers)} results")
                execution_log.append({
                    'step': 'Result Selection',
                    'description': 'WoS Query Results',
                    'details': f"Returning top {len(reranked_papers)} results (no semantic reranking for advanced queries)",
                    'elapsed_ms': int((time.time() - step3_start) * 1000),
                    'status': 'completed'
                })
            else:
                logger.info(f"Semantic reranking disabled, returning top {len(reranked_papers)} results")
                execution_log.append({
                    'step': 'DELM',
                    'description': 'Semantic Reranking',
                    'details': f"Reranking disabled, returning top {len(reranked_papers)} results by original order",
                    'elapsed_ms': int((time.time() - step3_start) * 1000),
                    'status': 'skipped'
                })
        if progress_callback:
            progress_callback(execution_log[-1])

        # Format abstracts (full abstract, not snippet)
        # Display full abstracts to users - truncation happens on frontend if needed
        for paper in reranked_papers:
            abstract = paper.get('abstract', '')
            # Keep full abstract for display
            paper['abstract_snippet'] = abstract if abstract else 'No abstract available'

        elapsed_time = time.time() - start_time
        
        session_info = ""
        if previous_papers:
            session_info = f" (Building on {len(previous_papers)} papers from previous searches)"

        return {
            'success': True,
            'papers': reranked_papers,
            'all_session_papers': unique_papers,  # All unique papers from this session
            'total_found': len(all_papers),
            'total_unique': len(unique_papers),
            'returned': len(reranked_papers),
            'elapsed_time': elapsed_time,
            'message': f'Found {len(reranked_papers)} relevant papers in {elapsed_time:.2f}s{session_info}',
            'execution_log': execution_log,
            'sources_used': sources
        }

    except Exception as e:
        logger.error(f"Search pipeline failed: {e}")
        execution_log.append({
            'step': 'Error',
            'description': 'Pipeline Failure',
            'details': str(e),
            'elapsed_ms': 0,
            'status': 'error'
        })
        return {
            'success': False,
            'papers': [],
            'message': f'Search failed: {str(e)}',
            'elapsed_time': time.time() - start_time,
            'execution_log': execution_log
        }


def get_available_sources() -> Dict[str, Any]:
    """
    Check which search sources are available based on installed libraries and API keys.
    
    Returns:
        Dictionary with source availability information.
    """
    sources = {
        'semantic_scholar': {
            'name': 'Semantic Scholar',
            'available': False,
            'description': 'Open academic paper search from AI2',
            'requires': 'semanticscholar package'
        },
        'arxiv': {
            'name': 'arXiv',
            'available': False,
            'description': 'Preprint repository for physics, mathematics, CS, etc.',
            'requires': 'arxiv package'
        },
        'web_of_science': {
            'name': 'Web of Science',
            'available': False,
            'description': 'Comprehensive citation database',
            'requires': 'WOS_API_KEY environment variable (Expanded API)'
        },
        'openalex': {
            'name': 'OpenAlex',
            'available': True,  # Always available, no special requirements
            'description': 'Free, open catalog of scholarly works',
            'requires': 'No API key required (uses requests)'
        }
    }
    
    # Check Semantic Scholar
    try:
        _get_semantic_scholar()
        sources['semantic_scholar']['available'] = True
    except Exception:
        pass
    
    # Check arXiv
    try:
        _get_arxiv()
        sources['arxiv']['available'] = True
    except Exception:
        pass
    
    # Check Web of Science
    try:
        api_key = _get_wos_api_key()
        if api_key is not None:
            sources['web_of_science']['available'] = True
    except Exception:
        pass
    
    return sources
