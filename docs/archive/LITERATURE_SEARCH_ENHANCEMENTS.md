# Literature Search Enhancements

This document describes the recent enhancements to the HARVEST literature search functionality.

## Table of Contents
- [Overview](#overview)
- [New Features](#new-features)
- [OpenAlex Integration](#openalex-integration)
- [Pipeline Workflow Controls](#pipeline-workflow-controls)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Technical Details](#technical-details)

## Overview

The literature search system has been enhanced with:
1. **OpenAlex** as a new search source
2. **Pipeline Workflow Controls** to customize the search process
3. **Improved visibility** of the search pipeline execution

## New Features

### OpenAlex Integration

OpenAlex is a free, open catalog of scholarly works that includes:
- Over 250 million scholarly works
- Author information and institution affiliations
- Citation relationships
- Open access availability
- No API key required

**Benefits:**
- Free and open access
- Comprehensive coverage across disciplines
- Fast response times (using polite pool)
- Open access information included

**How to Use:**
1. Navigate to the Literature Search tab
2. Check the "OpenAlex" checkbox in the "Select Search Sources" section
3. Enter your search query and click "Search Papers"

### Pipeline Workflow Controls

The search pipeline now has three configurable steps:

#### 1. Query Expansion (AutoResearch)
- **What it does:** Expands your query using synonyms and related terms
- **When to enable:** For broad searches where you want to discover related work
- **When to disable:** For precise searches with specific terminology

#### 2. Deduplication
- **What it does:** Removes duplicate papers based on DOI and title similarity
- **When to enable:** Almost always (recommended)
- **When to disable:** When you want to see all raw results from each source

#### 3. Semantic Reranking (DELM)
- **What it does:** Uses AI to rerank results based on semantic similarity to your query
- **When to enable:** For best relevance ranking (default)
- **When to disable:** For faster searches or when you prefer citation-based ranking

**Default Configuration:**
All three pipeline steps are enabled by default, providing the best balance of relevance and coverage.

## Usage Examples

### Example 1: Quick Search with OpenAlex Only
For a fast search on a specific topic:
1. Select only "OpenAlex" as source
2. Disable "Semantic Reranking" for speed
3. Enter your query
4. Click "Search Papers"

### Example 2: Comprehensive Multi-Source Search
For thorough literature review:
1. Select all available sources (Semantic Scholar, arXiv, Web of Science, OpenAlex)
2. Keep all pipeline controls enabled
3. Enable "Build on previous searches" for cumulative results
4. Perform multiple related searches

### Example 3: Debugging Slow Searches
If searches are slow:
1. Check the "Pipeline Execution Flow" section
2. Identify which step takes longest:
   - If "Semantic Reranking" is slow, consider disabling it
   - If "Semantic Scholar" is slow, try using only OpenAlex
   - If "Query Expansion" adds unwanted results, disable it

## Configuration

### Environment Variables

#### HARVEST_CONTACT_EMAIL
Optional. Set this to your contact email for OpenAlex's polite pool (faster responses).

```bash
export HARVEST_CONTACT_EMAIL="your-email@institution.edu"
```

If not set, defaults to `harvest-app@example.com`.

## Technical Details

### Search Pipeline Architecture

The literature search follows this pipeline:

```
1. Query Processing
   ├─ Query Expansion (optional) → Multiple query variations
   └─ Original query
        ↓
2. Multi-Source Search (DeepResearch)
   ├─ Semantic Scholar (limit: 40)
   ├─ arXiv (limit: 10)
   ├─ Web of Science (limit: 20)
   └─ OpenAlex (limit: 20)
        ↓
3. Deduplication (optional)
   └─ Remove duplicates by DOI and title
        ↓
4. Semantic Reranking (optional)
   └─ Rerank by semantic similarity using DELM
        ↓
5. Results Display
   └─ Top K results with metadata
```

### OpenAlex API Details

**Endpoint:** `https://api.openalex.org/works`

**Parameters:**
- `search`: Query string (searches title and abstract)
- `per_page`: Results per page (max: 200)
- `sort`: Relevance-based sorting
- `mailto`: Contact email for polite pool

**Response Processing:**
- Abstracts are reconstructed from inverted index format
- Open access information is extracted
- DOIs are prioritized, with fallback to OpenAlex IDs

### Pipeline Control Implementation

Each pipeline step is controlled by boolean flags:
- `enable_query_expansion: bool = True`
- `enable_deduplication: bool = True`
- `enable_reranking: bool = True`

When a step is disabled, it's marked as "skipped" in the execution log.

### Execution Log

The pipeline execution flow displays:
- **Step name:** AutoResearch, DeepResearch, DELM
- **Description:** Brief description of what happened
- **Details:** Specific information (query variations, paper counts, etc.)
- **Timing:** Milliseconds taken for the step
- **Status:** completed, skipped, or error

### Performance Considerations

**Typical Search Times:**
- OpenAlex only: 1-3 seconds
- Multiple sources: 5-10 seconds
- With semantic reranking: 10-15 seconds

**Optimization Tips:**
1. Disable semantic reranking for faster searches
2. Use fewer sources for quick results
3. Disable query expansion for precise searches
4. Use session-based cumulative searching instead of large single searches

## Future Enhancements

### Real-Time Progress Updates
For true real-time updates during search execution, future versions may implement:
- Background task processing (Celery, Redis Queue)
- WebSocket or Server-Sent Events
- Live progress bars for each pipeline step

Currently, users see a loading spinner during search, then complete results with timing details.

### Additional Sources
Potential future additions:
- PubMed/PMC
- CrossRef
- Google Scholar (via Serpapi)
- CORE
- Microsoft Academic

### Enhanced Query Processing
- Natural language query understanding
- Automatic field detection (author, year, journal)
- Query suggestions based on typing
- Saved query templates

## Troubleshooting

### OpenAlex Returns No Results
- **Check network connectivity:** OpenAlex requires internet access
- **Verify query format:** Use natural language or specific terms
- **Try broader terms:** OpenAlex has comprehensive coverage but may not have everything

### Semantic Reranking is Slow
- **Disable it:** Uncheck "Semantic Reranking (DELM)" for faster results
- **Reduce result count:** Fewer papers = faster reranking
- **Check system resources:** Reranking uses ML models that need CPU/memory

### Web of Science Not Available
- **Check API key:** Set `WOS_API_KEY` environment variable
- **Verify subscription:** Web of Science requires institutional access

### Searches Timeout
- **Reduce sources:** Try using only OpenAlex or arXiv
- **Disable reranking:** This is the slowest step
- **Simplify query:** Complex queries may take longer

## Support

For issues or questions:
1. Check the execution log for details
2. Review this documentation
3. Check the main HARVEST README
4. Open an issue on GitHub

## References

- [OpenAlex Documentation](https://docs.openalex.org/)
- [OpenAlex API Overview](https://docs.openalex.org/how-to-use-the-api/api-overview)
- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [arXiv API](https://arxiv.org/help/api/)
- [Web of Science API](https://developer.clarivate.com/apis/wos)
