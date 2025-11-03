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
"""

import logging
from typing import List, Dict, Any, Optional, Set
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Lazy imports to avoid loading heavy libraries at startup
_semantic_scholar = None
_sentence_transformers = None
_arxiv = None
_wos_client = None


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
    """Get Web of Science API key from environment"""
    global _wos_client
    if _wos_client is None:
        import os
        api_key = os.getenv('WOS_API_KEY')
        if api_key:
            _wos_client = api_key
        else:
            logger.warning("WOS_API_KEY not set. Web of Science searches will be disabled.")
            _wos_client = False  # Use False to indicate checked but not available
    return _wos_client if _wos_client else None


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
    Simple query expansion using common synonyms.
    Returns a list of query variations.
    
    Note: Not applicable for Web of Science advanced queries.
    """
    # Basic synonym mapping for common terms
    synonym_map = {
        'ai': ['artificial intelligence', 'machine learning', 'deep learning'],
        'ml': ['machine learning', 'artificial intelligence'],
        'drug': ['pharmaceutical', 'medicine', 'therapeutic'],
        'disease': ['disorder', 'illness', 'pathology'],
        'gene': ['genetic', 'genomic'],
        'protein': ['peptide', 'polypeptide'],
    }

    query_lower = query.lower()
    expanded = [query]

    for term, synonyms in synonym_map.items():
        if term in query_lower:
            for synonym in synonyms:
                if synonym not in query_lower:
                    expanded.append(query_lower.replace(term, synonym))

    return list(set(expanded))[:3]  # Limit to 3 variations


@lru_cache(maxsize=100)
def search_semantic_scholar(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    """
    Search Semantic Scholar API for papers.
    Cached to avoid redundant API calls.
    """
    try:
        s2 = _get_semantic_scholar()

        # Search with fields we need
        results = s2.search_paper(
            query,
            limit=limit,
            fields=['title', 'abstract', 'authors', 'year', 'externalIds', 'citationCount']
        )

        papers = []
        for paper in results:
            # Extract DOI from externalIds
            doi = None
            if hasattr(paper, 'externalIds') and paper.externalIds:
                doi = paper.externalIds.get('DOI')

            # Extract authors
            authors = []
            if hasattr(paper, 'authors') and paper.authors:
                authors = [a.name if hasattr(a, 'name') else str(a) for a in paper.authors[:3]]

            papers.append({
                'title': paper.title if hasattr(paper, 'title') else 'N/A',
                'abstract': paper.abstract if hasattr(paper, 'abstract') else '',
                'authors': authors,
                'year': paper.year if hasattr(paper, 'year') else None,
                'doi': doi,
                'source': 'Semantic Scholar',
                'citations': paper.citationCount if hasattr(paper, 'citationCount') else 0
            })

        logger.info(f"Retrieved {len(papers)} papers from Semantic Scholar")
        return papers

    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {e}")
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
def search_web_of_science(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Search Web of Science Expanded API for papers.
    Uses the direct REST API as shown in Clarivate examples.
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
    
    API Reference: https://github.com/clarivate/wos_api_usecases/
    """
    try:
        import requests
        
        api_key = _get_wos_api_key()
        
        if api_key is None:
            logger.warning("Web of Science API key not available. Check WOS_API_KEY environment variable.")
            return []
        
        # Convert to WoS advanced query format if needed
        wos_query = convert_to_wos_query(query)
        logger.info(f"Web of Science query: {wos_query}")
        
        # Use Web of Science Expanded API endpoint
        # Search WOS Core Collection database
        params = {
            'databaseId': 'WOS',
            'usrQuery': wos_query,  # Use converted query
            'count': min(limit, 100),  # API max is 100 per request
            'firstRecord': 1
        }
        
        response = requests.get(
            url='https://api.clarivate.com/api/wos',
            params=params,
            headers={'X-ApiKey': api_key},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Web of Science API error {response.status_code}: {response.text}")
            return []
        
        result = response.json()
        
        # Parse the response structure from WoS Expanded API
        papers = []
        records = result.get('Data', {}).get('Records', {}).get('records', {}).get('REC', [])
        
        for record in records:
            # Extract basic metadata
            static_data = record.get('static_data', {})
            summary = static_data.get('summary', {})
            fullrecord_metadata = static_data.get('fullrecord_metadata', {})
            
            # Extract title
            titles = summary.get('titles', {}).get('title', [])
            title = 'N/A'
            for t in titles:
                if t.get('type') == 'item':
                    title = t.get('content', 'N/A')
                    break
            
            # Extract DOI
            doi = None
            identifiers = static_data.get('fullrecord_metadata', {}).get('identifiers', {})
            if identifiers:
                doi_list = identifiers.get('identifier', [])
                for identifier in doi_list:
                    if identifier.get('type') == 'doi':
                        doi = identifier.get('value')
                        break
            
            # Extract UT (unique identifier) as fallback
            if not doi:
                ut = record.get('UID')
                if ut:
                    doi = f"WOS:{ut}"
            
            # Extract authors
            authors = []
            names = summary.get('names', {}).get('name', [])
            for name in names[:3]:  # Limit to first 3 authors
                if name.get('role') == 'author':
                    display_name = name.get('display_name') or name.get('full_name')
                    if display_name:
                        authors.append(display_name)
            
            # Extract year
            year = None
            pub_info = summary.get('pub_info', {})
            pubyear = pub_info.get('pubyear')
            if pubyear:
                try:
                    year = int(pubyear)
                except (ValueError, TypeError):
                    pass
            
            # Extract abstract
            abstract = ''
            abstracts = fullrecord_metadata.get('abstracts', {}).get('abstract', [])
            for abs_item in abstracts:
                abstract_text = abs_item.get('abstract_text', {}).get('p', '')
                if abstract_text:
                    abstract = abstract_text
                    break
            
            # Extract citation count
            citations = 0
            dynamic_data = record.get('dynamic_data', {})
            citation_related = dynamic_data.get('citation_related', {})
            tc_list = citation_related.get('tc_list', {}).get('silo_tc', [])
            for tc in tc_list:
                if tc.get('coll_id') == 'WOS':
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
        
        logger.info(f"Retrieved {len(papers)} papers from Web of Science")
        return papers
    
    except requests.RequestException as e:
        logger.error(f"Web of Science API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Web of Science search failed: {e}")
        return []


def deduplicate_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate papers by DOI and title similarity.
    Prioritizes papers with more citations.
    """
    seen_dois = set()
    seen_titles = set()
    unique_papers = []

    # Sort by citations (descending) to prioritize highly cited papers
    sorted_papers = sorted(papers, key=lambda x: x.get('citations', 0), reverse=True)

    for paper in sorted_papers:
        # Check DOI
        doi = paper.get('doi')
        if doi and doi in seen_dois:
            continue

        # Check title (case-insensitive, normalized)
        title = paper.get('title', '').lower().strip()
        if title and title in seen_titles:
            continue

        # Add to unique list
        unique_papers.append(paper)
        if doi:
            seen_dois.add(doi)
        if title:
            seen_titles.add(title)

    logger.info(f"Deduplicated {len(papers)} papers to {len(unique_papers)} unique papers")
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
    previous_papers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Main search function that orchestrates the entire search pipeline:
    1. Query expansion (AutoResearch)
    2. Multi-source search (DeepResearch - Python Reimpl)
    3. Deduplication (including previous search results)
    4. Semantic reranking (DELM)
    
    Args:
        query: Search query string
        top_k: Number of top results to return
        sources: List of sources to search. Options: 'semantic_scholar', 'arxiv', 'web_of_science'
                 If None, defaults to ['semantic_scholar', 'arxiv']
        previous_papers: Papers from previous searches in session to build upon
    
    Returns:
        Dictionary with papers and metadata, including execution details.
    """
    start_time = time.time()
    execution_log = []  # Track execution steps for display
    
    # Default sources if not specified
    if sources is None:
        sources = ['semantic_scholar', 'arxiv']
    
    # Validate sources
    valid_sources = {'semantic_scholar', 'arxiv', 'web_of_science'}
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
        
        # Step 1: AutoResearch - Query expansion (skip for WoS advanced queries)
        step1_start = time.time()
        if is_wos_advanced and using_wos_only:
            queries = [query]  # No expansion for WoS advanced queries
            logger.info(f"Using Web of Science advanced query syntax: {query}")
            execution_log.append({
                'step': 'Query Processing',
                'description': 'Web of Science Advanced Query',
                'details': f"Using advanced query syntax (no expansion): {query}",
                'elapsed_ms': int((time.time() - step1_start) * 1000),
                'status': 'completed'
            })
        else:
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

        # Step 2: DeepResearch (Python Reimpl) - Multi-source search
        step2_start = time.time()
        all_papers = []
        source_details = []
        
        # Search Semantic Scholar if requested
        if 'semantic_scholar' in sources:
            s2_start = time.time()
            s2_papers = []
            for q in queries[:1]:  # Use only the primary query for S2
                s2_results = search_semantic_scholar(q, limit=40)
                s2_papers.extend(s2_results)
                all_papers.extend(s2_results)
            s2_time = time.time() - s2_start
            s2_count = len(s2_papers)
            source_details.append(f"Semantic Scholar ({s2_count} in {s2_time:.2f}s)")
        
        # Search arXiv if requested
        if 'arxiv' in sources:
            arxiv_start = time.time()
            arxiv_papers = search_arxiv(query, limit=10)
            all_papers.extend(arxiv_papers)
            arxiv_time = time.time() - arxiv_start
            arxiv_count = len(arxiv_papers)
            source_details.append(f"arXiv ({arxiv_count} in {arxiv_time:.2f}s)")
        
        # Search Web of Science if requested
        if 'web_of_science' in sources:
            wos_start = time.time()
            wos_papers = search_web_of_science(query, limit=20)
            all_papers.extend(wos_papers)
            wos_time = time.time() - wos_start
            wos_count = len(wos_papers)
            source_details.append(f"Web of Science ({wos_count} in {wos_time:.2f}s)")

        step2_time = time.time() - step2_start
        execution_log.append({
            'step': 'DeepResearch (Python Reimpl)',
            'description': 'Multi-Source Paper Retrieval',
            'details': f"Retrieved {len(all_papers)} papers: {', '.join(source_details)}",
            'elapsed_ms': int(step2_time * 1000),
            'status': 'completed'
        })

        if not all_papers:
            return {
                'success': False,
                'papers': [],
                'message': 'No papers found. Try a different query.',
                'elapsed_time': time.time() - start_time,
                'execution_log': execution_log
            }

        # Step 2b: Deduplication (including previous search results)
        dedup_start = time.time()
        
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

        # Step 3: DELM - Semantic reranking (skip for WoS advanced queries)
        step3_start = time.time()
        if is_wos_advanced and using_wos_only:
            # For WoS advanced queries, skip semantic reranking and just limit results
            reranked_papers = unique_papers[:top_k]
            logger.info(f"Skipping semantic reranking for WoS advanced query, returning top {len(reranked_papers)} results")
            execution_log.append({
                'step': 'Result Selection',
                'description': 'WoS Query Results',
                'details': f"Returning top {len(reranked_papers)} results (no semantic reranking for advanced queries)",
                'elapsed_ms': int((time.time() - step3_start) * 1000),
                'status': 'completed'
            })
        else:
            reranked_papers = rerank_papers(unique_papers, query, top_k=top_k)
            step3_time = time.time() - step3_start
            execution_log.append({
                'step': 'DELM',
                'description': 'Semantic Reranking',
                'details': f"Reranked {len(unique_papers)} papers using semantic similarity, returning top {len(reranked_papers)} results",
                'elapsed_ms': int(step3_time * 1000),
                'status': 'completed'
            })

        # Format abstracts (snippet only)
        for paper in reranked_papers:
            abstract = paper.get('abstract', '')
            if len(abstract) > 300:
                paper['abstract_snippet'] = abstract[:300] + '...'
            else:
                paper['abstract_snippet'] = abstract

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
