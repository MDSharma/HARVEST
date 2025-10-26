"""
Literature Search Module for Text2Trait
Provides semantic paper discovery from Semantic Scholar and arXiv
with query expansion, reranking, and deduplication.
"""

import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

# Lazy imports to avoid loading heavy libraries at startup
_semantic_scholar = None
_sentence_transformers = None
_arxiv = None


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


def expand_query(query: str) -> List[str]:
    """
    Simple query expansion using common synonyms.
    Returns a list of query variations.
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


def search_papers(query: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Main search function that orchestrates the entire search pipeline:
    1. Query expansion
    2. Multi-source search (Semantic Scholar + arXiv)
    3. Deduplication
    4. Semantic reranking

    Returns a dictionary with papers and metadata.
    """
    start_time = time.time()

    try:
        # Expand query
        queries = expand_query(query)
        logger.info(f"Expanded query '{query}' to {len(queries)} variations")

        # Search both sources
        all_papers = []

        # Semantic Scholar (40 papers)
        for q in queries[:1]:  # Use only the primary query for S2
            s2_papers = search_semantic_scholar(q, limit=40)
            all_papers.extend(s2_papers)

        # arXiv (10 papers)
        arxiv_papers = search_arxiv(query, limit=10)
        all_papers.extend(arxiv_papers)

        if not all_papers:
            return {
                'success': False,
                'papers': [],
                'message': 'No papers found. Try a different query.',
                'elapsed_time': time.time() - start_time
            }

        # Deduplicate
        unique_papers = deduplicate_papers(all_papers)

        # Rerank
        reranked_papers = rerank_papers(unique_papers, query, top_k=top_k)

        # Format abstracts (snippet only)
        for paper in reranked_papers:
            abstract = paper.get('abstract', '')
            if len(abstract) > 300:
                paper['abstract_snippet'] = abstract[:300] + '...'
            else:
                paper['abstract_snippet'] = abstract

        elapsed_time = time.time() - start_time

        return {
            'success': True,
            'papers': reranked_papers,
            'total_found': len(all_papers),
            'total_unique': len(unique_papers),
            'returned': len(reranked_papers),
            'elapsed_time': elapsed_time,
            'message': f'Found {len(reranked_papers)} relevant papers in {elapsed_time:.2f}s'
        }

    except Exception as e:
        logger.error(f"Search pipeline failed: {e}")
        return {
            'success': False,
            'papers': [],
            'message': f'Search failed: {str(e)}',
            'elapsed_time': time.time() - start_time
        }
