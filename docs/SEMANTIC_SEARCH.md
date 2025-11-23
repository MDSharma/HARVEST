# Enhanced Semantic Search Documentation


## Quick Start

# Enhanced Semantic Search - Quick Start Guide

## What's New (Latest Update)

### Enhanced UI and Search Quality (December 2024)

**Visual Improvements:**
- 🎨 **Color-Coded Badges**: Source, year, citations, and open access status
  - Citations: Red (100+), Warning (50+), Info (10+), Gray (<10)
  - Sources: Blue (Semantic Scholar), Green (arXiv), Info (WoS), Warning (OpenAlex)
- ✨ **Better Card Design**: Shadow effects, improved spacing, icons
- 🔍 **Improved Metadata Display**: Icons for authors, DOI links, better typography

**New Features:**
- 📊 **Sorting Controls**: 
  - Relevance (default - semantic similarity)
  - Citations (high to low)
  - Year (newest/oldest first)
  - Instant client-side sorting without re-running search
  
- 🎯 **Source Filtering**:
  - Filter results by specific sources
  - Instant client-side filtering
  - No need to re-run search
  
- 💡 **Helpful Tooltips**:
  - Source selection tooltip explains each database
  - Pipeline controls tooltip explains each step
  - Recommended settings clearly marked in UI

**Search Quality Improvements:**
- ✓ **Enhanced Deduplication**: Fuzzy title matching (85% similarity)
  - Catches formatting variations (e.g., "Machine Learning" vs "machine learning")
  - Removes punctuation differences
  - Case-insensitive matching with word-level comparison
  
- ✓ **Query Expansion**: Now disabled by default for better precision
  - Modern search engines (Semantic Scholar, OpenAlex) handle semantic similarity internally
  - Can be re-enabled if needed via Pipeline Controls
  - Reduces search noise and improves relevance

### Three Major Improvements

1. **🔍 Multi-Source Search**
   - Search Semantic Scholar, arXiv, and Web of Science
   - Select which sources to use for each search
   - Get results from multiple databases at once

2. **📚 Build on Previous Searches**
   - Enable cumulative mode to add results over time
   - Smart deduplication across all searches
   - Build comprehensive literature reviews iteratively

3. **⚙️ Flexible Configuration**
   - See which sources are available
   - Optional Web of Science integration
   - Works great with just free sources (Semantic Scholar + arXiv)

## How to Use

### Basic Search (Same as Before!)

1. Login via Admin tab
2. Go to Literature Search
3. Enter your query: "AI in drug discovery"
4. Click "Search Papers"
5. Done! ✓

### New: Choose Your Sources

Before searching, check/uncheck sources:
- ☑ Semantic Scholar (recommended)
- ☑ arXiv (good for recent research)
- ☐ Web of Science (optional, requires API key)

### New: Build on Previous Searches

To create a comprehensive literature set:

1. **First search**: "machine learning"
   - Get 10 results
   
2. **Check "Build on previous searches"**

3. **Second search**: "deep learning"
   - Get 10 new results
   - Combined with previous = 20 unique papers
   
4. **Third search**: "neural networks"
   - Get 10 more results
   - Combined = 30 unique papers total
   
5. **Click "Clear Session"** when done
   - Start fresh for a new topic

## Web of Science Setup (Optional)

Only if you want premium citation data:

1. Get API key from https://developer.clarivate.com/
2. Set environment variable:
   ```bash
   export WOS_API_KEY="your-key-here"
   ```
3. Restart HARVEST
4. Web of Science checkbox will be available!

**Note**: Uses Web of Science Expanded API directly - no additional packages needed!

### Web of Science Advanced Search

When using Web of Science, you can use **advanced query syntax** for precise searches:

**Simple queries** (auto-converted):
- `"machine learning"` → searches topic field

**Advanced queries** (use as-is):
- `AB=(genomic* OR transcriptom*)` → searches abstracts
- `TI=(CRISPR) AND PY=(2020-2024)` → searches titles and year range
- `AU=(Smith J*) AND TS=(climate)` → searches authors and topic

**Common field tags:**
- `TS=` Topic (title + abstract + keywords)
- `TI=` Title
- `AB=` Abstract
- `AU=` Author
- `PY=` Year (use ranges like `PY=(2020-2024)`)
- `SO=` Journal name
- `DO=` DOI

**Operators:** `AND`, `OR`, `NOT`  
**Wildcards:** `*` (many chars), `?` (one char)

**Example:** `AB=(longevity* OR reproduction*) AND PY=(2015-2024)`

See [WoS Advanced Search Guide](https://webofscience.zendesk.com/hc/en-us/articles/20130361503249) for more details.

## What You Get

Every paper includes:
- Title
- Authors (up to 3)
- Year
- DOI (clickable link)
- Abstract snippet
- Citation count
- Source (which database it came from)

Plus:
- Smart ranking by semantic relevance
- Duplicate removal across sources
- Citation-weighted sorting
- Export to projects

## Tips & Tricks

### For Quick Searches
- Use Semantic Scholar only (fastest)
- Single specific query

### For Comprehensive Reviews
- Enable all available sources
- Use cumulative mode
- Try multiple related queries
- Export everything to one project

### For Recent Research
- Use arXiv only
- Focus on preprints
- Check dates manually

### For Citation Analysis
- Include Semantic Scholar
- Enable Web of Science if available
- Note citation counts

## Troubleshooting

**"No sources selected"**
- Check at least one source box

**Web of Science not available**
- It's optional! Use free sources instead
- Or set up API key (see above)

**No results found**
- Try broader terms
- Check more sources
- Verify spelling

**Session not working**
- Make sure you're logged in
- Check "Build on previous searches" box
- Try "Clear Session" and restart

## More Info

See full documentation: `docs/SEMANTIC_SEARCH.md`

Includes:
- Detailed usage guide
- Technical details
- Advanced features
- API comparison
- Best practices

## Questions?

1. Check `docs/SEMANTIC_SEARCH.md`
2. Review main `README.md`
3. Open a GitHub issue

Happy searching! 🎉


---

## Overview

The HARVEST application includes an enhanced semantic search capability that allows users to discover relevant academic papers from multiple sources with advanced features like API selection, cumulative session building, and intelligent deduplication.

## Features

### 1. Multi-Source Search

The semantic search system can query multiple academic databases simultaneously:

- **Semantic Scholar** - Open academic paper search from AI2
  - Largest open corpus (200M+ papers)
  - Includes citation counts and impact metrics
  - Free to use, no API key required
  - **Advanced features**:
    - Paper recommendations based on similarity
    - Bulk paper retrieval by IDs
    - Filtering by year, citations, open access
    - Venue and publication type filtering
  
- **arXiv** - Preprint repository
  - Physics, mathematics, computer science, etc.
  - Free and open access
  - Latest research before peer review
  
- **Web of Science** (Optional)
  - Comprehensive citation database
  - Requires API key from Clarivate
  - Premium content and citation analytics

### 2. API Selection

Users can select which sources to search, allowing for:
- **Targeted searches** - Focus on specific databases
- **Comprehensive searches** - Query all available sources
- **Cost management** - Avoid paid APIs when not needed

### 3. Cumulative Session Search

The "Build on previous searches" feature enables:
- **Iterative refinement** - Add new results to existing ones
- **Topic exploration** - Expand search scope over time
- **Comprehensive reviews** - Build complete literature sets
- **Smart deduplication** - Automatic removal of duplicates across sessions

### 4. Semantic Reranking

Results are reranked using semantic similarity:
- Embeds query and abstracts using sentence transformers
- Computes cosine similarity scores
- Returns most semantically relevant papers
- Preserves highly-cited papers in ranking

## Usage Guide

### Basic Search

1. **Navigate to Literature Search Tab**
   - Login via Admin tab first (authentication required)

2. **Select Search Sources**
   - Check desired sources: Semantic Scholar, arXiv, Web of Science
   - Default: Semantic Scholar + arXiv

3. **Enter Search Query**
   - Use natural language: "AI in drug discovery"
   - Or specific terms: "CRISPR gene editing ethics"

4. **Click "Search Papers"**
   - Results appear with execution pipeline details
   - Papers are ranked by semantic relevance

### Using Sorting and Filtering (New!)

After getting your results, you can refine them without re-running the search:

1. **Sort Results**
   - Click the "Sort By" dropdown
   - Choose from:
     - Relevance (default - based on semantic similarity to your query)
     - Citations (high to low - shows most influential papers first)
     - Year (newest first - shows latest research)
     - Year (oldest first - shows foundational work)

2. **Filter by Source**
   - Click the "Filter by Source" dropdown
   - Select a specific source to view only those results
   - Choose "All Sources" to see everything again

3. **Visual Indicators**
   - **Source badges** show where each paper came from (color-coded)
   - **Citation badges** show impact (color-coded by count)
   - **Year badges** show publication date
   - **Open access badges** show freely available papers (green)

**Example Workflow:**
1. Search for "machine learning in healthcare"
2. Get 50 results from multiple sources
3. Sort by "Citations (high to low)" to see most influential papers
4. Filter by "arXiv" to see only preprints
5. Sort by "Year (newest first)" to find latest arXiv papers

This is much faster than running multiple searches!

### Cumulative Session Search

To build on previous searches:

1. **Perform Initial Search**
   - Enter query and search normally

2. **Enable "Build on previous searches"**
   - Check the cumulative search option

3. **Enter New Query**
   - Related or refined search terms

4. **Search Again**
   - New results are added to previous ones
   - Duplicates automatically removed
   - Results re-ranked together

5. **Clear Session**
   - Click "Clear Session" to start fresh
   - Session automatically resets on logout

### Configuring Result Limits

The search system allows you to control how many results are fetched from each source and displayed:

#### Results Per Source (Advanced Settings)

Click "Advanced: Results per Source" to configure individual source limits:

- **Semantic Scholar**: 1-100 results (default: 100)
  - API maximum: 100 per request
  - Increased from original 40 to fetch comprehensive results
  
- **arXiv**: 1-100 results (default: 50)
  - API supports up to 100+ results
  - Increased from original 10 to capture more preprints
  
- **Web of Science**: 1-100 results (default: 100)
  - API maximum: 100 per request
  - Increased from original 20 to maximize coverage
  
- **OpenAlex**: 1-200 results (default: 200)
  - API maximum: 200 per page
  - Increased from original 20 to leverage full API capacity

**Benefits of Higher Limits:**
- **More comprehensive results** - Captures a wider range of relevant papers
- **Better deduplication** - More papers to compare across sources
- **Improved ranking** - More candidates for semantic reranking
- **Fuller literature coverage** - Especially important for systematic reviews

**Trade-offs:**
- Higher limits increase search time (typically 5-15 seconds vs 2-5 seconds)
- More results to review (use semantic reranking to focus on top papers)

#### Number of Results to Display

After fetching, deduplication, and reranking, you can control how many papers to display:

- **Range**: 1-100 results
- **Default**: 20 results (increased from original 10)
- **Purpose**: Shows the most relevant papers after semantic reranking

**Recommended Settings:**
- **Quick overview**: 10-20 results
- **Comprehensive review**: 50-100 results
- **Literature mapping**: Use "Build on previous searches" with 20-30 results per query

**Example Workflow:**
1. Set Semantic Scholar to 100, OpenAlex to 200
2. Enable all pipeline features (expansion, deduplication, reranking)
3. Set display count to 30
4. Run search
5. Review top 30 semantically-ranked results from 300 total fetched

### Query Format by Source

Different sources expect different query formats:

- **Semantic Scholar**: Natural language queries
  - Examples: "AI in drug discovery", "CRISPR gene editing"
  
- **arXiv**: Natural language queries
  - Examples: "quantum computing", "deep learning"
  
- **OpenAlex**: Natural language queries
  - Examples: "climate change modeling", "protein folding"
  
- **Web of Science**: Advanced syntax or natural language
  - Natural language is automatically converted to `TS=(query)` format
  - For advanced syntax, see Advanced Search Syntax section below

The source checkboxes indicate the expected query type in parentheses.

### Exporting Results

1. **Select Papers**
   - Check boxes next to desired papers
   - Use "Select All" / "Deselect All" buttons

2. **Export Selected DOIs**
   - Create new project with selections
   - Add to existing project
   - Copy to clipboard

## Search Pipeline

The semantic search executes in three stages:

### Stage 1: AutoResearch - Query Expansion
- Expands query with common synonyms
- Creates up to 3 query variations
- Broadens search scope automatically

### Stage 2: DeepResearch - Multi-Source Retrieval
- Queries selected academic databases
- Retrieves papers with metadata
- Deduplicates across sources
- Merges with session history if enabled

### Stage 3: DELM - Semantic Reranking
- Encodes query and abstracts semantically
- Calculates similarity scores
- Returns top-k most relevant papers
- Preserves citation-weighted ranking

## Semantic Scholar Advanced Features

### Enhanced Search Capabilities

The Semantic Scholar integration follows [best practices from the S2 API documentation](https://www.semanticscholar.org/product/api/tutorial) and [webinar examples](https://github.com/allenai/s2-folks/tree/main/examples/Webinar%20Code%20Examples) for optimal performance and reliability.

**Improved Features:**
- **Selective field requests** - Only requests needed fields to reduce API load
- **Filtering options** - Filter by year range, minimum citations, open access status
- **Pagination support** - Handles large result sets efficiently
- **Retry logic with exponential backoff and jitter** - Automatically retries failed requests with randomized delays
- **Rate limit awareness** - Respects 429 (Too Many Requests) responses
- **Transient error handling** - Automatically retries on 502, 503, 504 server errors
- **Better error handling** - Graceful degradation on API failures with specific error logging
- **Metadata enrichment** - Includes venue, publication type, PDF availability

**Reliability Features (from S2 Webinar Best Practices):**
- **6 automatic retries** with exponential backoff (2.0s factor)
- **Jitter randomization** (0.5s) prevents thundering herd problems
- **Retry-After header respect** for server-directed backoff
- **Graceful degradation** returns empty results instead of crashing

**Year Range Filtering:**
```python
# Search for recent papers only
result = search_semantic_scholar("machine learning", year_range="2023-2024")

# Search for papers from a specific year
result = search_semantic_scholar("CRISPR", year_range="2023")
```

**Citation Filtering:**
```python
# Get only highly-cited papers
result = search_semantic_scholar("climate change", min_citations=100)
```

### Paper Recommendations

Get paper recommendations based on similarity to a known paper using Semantic Scholar's recommendation algorithm. This finds papers that:
- Share similar topics and methodology
- Are cited by or cite similar papers
- Have overlapping author networks

**Usage:**
```python
# Get recommendations based on a paper DOI
recommendations = get_recommended_papers_s2(
    paper_id="10.1038/nature14539",
    limit=20,
    pool='recent'  # or 'all-cs' for all CS papers
)
```

**Recommendation Pools:**
- `'recent'` - Papers from the last 2 years (default, good for current research)
- `'all-cs'` - All computer science papers (good for comprehensive reviews)

### Bulk Paper Retrieval

Efficiently retrieve multiple papers by their IDs (DOIs or S2 paper IDs):

```python
# Get specific papers by DOI
paper_ids = [
    "10.1038/nature14539",
    "arXiv:1706.03762",
    "10.1126/science.aaa1234"
]
papers = get_papers_by_ids_s2(paper_ids)
```

**Use Cases:**
- Building literature sets from citation lists
- Following up on references from a key paper
- Validating DOIs from external sources

### Open Access Detection

The enhanced implementation detects open access papers and extracts PDF URLs when available:

```python
# Search results now include:
{
    'title': 'Paper Title',
    'is_open_access': True,
    'pdf_url': 'https://arxiv.org/pdf/1234.5678.pdf'
}
```

## Web of Science Integration

### Setup

1. **Obtain API Key**
   - Register at https://developer.clarivate.com/
   - Subscribe to Web of Science Expanded API
   - Get your API key

2. **Set Environment Variable**
   ```bash
   export WOS_API_KEY="your-api-key-here"
   ```

3. **Restart Application**
   - Web of Science will appear in source options
   - Green checkmark indicates availability

**Note**: The integration uses the Web of Science Expanded API directly via REST calls. No additional Python packages are required beyond `requests` (already included).

**Technical Note**: The implementation includes the `viewField='fullRecord'` parameter in all API requests to ensure abstracts are returned. Without this parameter, the Web of Science API defaults to 'summary' view which excludes abstracts. This is a critical requirement for proper abstract retrieval.

### API Information

- **Endpoint**: `https://wos-api.clarivate.com/api/wos`
- **Database**: WOS (Web of Science Core Collection)
- **Implementation**: Based on [Clarivate's official examples](https://github.com/clarivate/wos_api_usecases/tree/main/python/societal_impact_analytics)
- **Max results per query**: 100
- **Required Parameters**: `viewField='fullRecord'` to retrieve abstracts

### Advanced Search Syntax

Web of Science supports powerful advanced search queries using **field tags** and **boolean operators**. When you use WoS as your search source, you can use either simple queries or advanced syntax.

#### Simple Queries

Simple queries are automatically converted to Topic Search format:
- `"machine learning"` → `TS=(machine learning)`
- `"climate change"` → `TS=(climate change)`

#### Advanced Query Format

Use field tags to search specific fields:

**Common Field Tags:**
- `TS=` - Topic (searches title, abstract, author keywords, and Keywords Plus®)
- `TI=` - Title
- `AB=` - Abstract
- `AU=` - Author name
- `PY=` - Publication year
- `SO=` - Publication title (journal/book)
- `DO=` - DOI
- `UT=` - Accession number (WoS ID)
- `PMID=` - PubMed ID

**All Available Field Tags:**
```
TS=Topic            TI=Title            AB=Abstract
AU=Author           AI=Author ID        AK=Author Keywords
GP=Group Author     ED=Editor           KP=Keywords Plus
SO=Publication      DO=DOI              PY=Year Published
CF=Conference       AD=Address          OG=Organization
OO=Organization     SG=Suborganization  SA=Street Address
CI=City             PS=Province/State   CU=Country
ZP=Zip/Postal Code  FO=Funding Agency   FG=Grant Number
FD=Funding Details  FT=Funding Text     SU=Research Area
WC=WoS Categories   IS=ISSN/ISBN        UT=Accession Number
PMID=PubMed ID      DOP=Pub Date        LD=Index Date
PUBL=Publisher      ALL=All Fields      FPY=Final Pub Year
EAY=Early Access    SDG=SDG Goals       TMAC=Citation Topic
```

**Boolean Operators:**
- `AND` - Both terms must be present
- `OR` - Either term can be present
- `NOT` - Exclude terms

**Wildcards:**
- `*` - Multiple characters (e.g., `genom*` matches genomic, genomics, genome)
- `?` - Single character (e.g., `wom?n` matches woman, women)

#### Example Queries

**Basic searches:**
```
AB=(genomic* OR transcriptom*)
TI=(machine learning)
AU=(Smith J*)
```

**Complex searches with boolean operators:**
```
AB=(genomic* OR transcriptom*) AND PY=(2020-2024)
TS=(CRISPR) AND AU=(Doudna) NOT TI=(review)
(TI=(climate change) OR AB=(global warming)) AND PY=(2015-2024)
```

**Year ranges:**
```
PY=(2020-2024)           # Papers from 2020 to 2024
PY=(2023)                # Papers from 2023 only
```

**Combining multiple fields:**
```
AB=(longevity* OR reproduction*) AND AU=(Tribolium) AND PY=(2015-2024)
TS=(artificial intelligence) AND SO=(Nature) AND PY=(2020-2024)
```

### Query Behavior

**When using Web of Science ONLY:**
- Advanced queries (with field tags) skip query expansion and semantic reranking
- Results are returned in WoS relevance order
- This preserves the precision of your advanced query

**When using Web of Science with other sources:**
- Simple queries undergo semantic processing across all sources
- Advanced queries are used as-is for WoS, expanded for other sources
- Results are deduplicated and semantically reranked

**Best Practices:**
1. Use advanced syntax for precise, reproducible searches
2. Use wildcards (`*`) for word variations
3. Use field tags to narrow your search scope
4. Test your query at [Web of Science Advanced Search](https://www.webofscience.com/wos/woscc/advanced-search) first
5. Enclose phrases in quotes: `AB=("machine learning")`

### Usage Notes

- Web of Science searches may have rate limits
- Check your API plan for usage quotas
- Results include citation metrics
- Access to paywalled content metadata
- Advanced queries provide more control than natural language search

**Resources:**
- [WoS Advanced Search Guide](https://webofscience.zendesk.com/hc/en-us/articles/20130361503249-Advanced-Search-Query-Builder)
- [WoS Search Tips](https://webofscience.zendesk.com/hc/en-us/sections/360007533194-Search-Tips)

## Configuration

### Environment Variables

```bash
# Optional: Web of Science Expanded API key
export WOS_API_KEY="your-key-here"

# Required for PDF downloads (see main docs)
export UNPAYWALL_EMAIL="your@email.com"
```

### Code Configuration

In `literature_search.py`:

```python
# Customize query expansion synonyms (not used for WoS advanced queries)
synonym_map = {
    'ai': ['artificial intelligence', 'machine learning', 'deep learning'],
    # Add your domain-specific terms
}

# Adjust result limits
semantic_scholar_limit = 40  # Default
arxiv_limit = 10            # Default
wos_limit = 20              # Default
top_k = 10                  # Results to display
```

## Troubleshooting

### Source Not Available

**Symptom**: Source shows ✗ unavailable

**Solutions**:
1. Check if package is installed:
   ```bash
   pip install semanticscholar arxiv
   ```
2. For Web of Science:
   - Verify API key is set
   - Check client library installation
   - Test API key validity

### No Results Found

**Possible causes**:
1. Query too specific - try broader terms
2. Selected sources don't contain matches
3. Network connectivity issues
4. API rate limits reached

**Solutions**:
- Expand search terms
- Enable more sources
- Try again after brief wait
- Check internet connection

### Duplicate Papers

**If seeing duplicates**:
- System automatically deduplicates by DOI and title
- Some papers may appear similar but are different
- Check DOI to verify uniqueness

### Session Not Building

**If cumulative search not working**:
1. Ensure "Build on previous searches" is checked
2. Verify you're logged in (session persists)
3. Try "Clear Session" and restart
4. Check browser console for errors

## API Comparison

| Feature | Semantic Scholar | arXiv | Web of Science |
|---------|-----------------|-------|----------------|
| **Cost** | Free | Free | Paid API key |
| **Coverage** | Broad (all fields) | Physics, Math, CS | Comprehensive |
| **Citations** | Yes | No | Yes |
| **Abstracts** | Yes | Yes | Yes |
| **Full Text** | Links only | Free PDFs | Metadata only |
| **Updates** | Real-time | Daily | Real-time |
| **Rate Limits** | Generous | Generous | Plan-dependent |

## Best Practices

### For Comprehensive Reviews
1. Start with Semantic Scholar + arXiv
2. Enable cumulative search
3. Try multiple query variations
4. Refine with specific terms
5. Export complete set to project

### For Current Research
1. Use arXiv only
2. Search for recent terms
3. Sort by date (manual)
4. Follow up on preprints

### For Citation Analysis
1. Include Semantic Scholar
2. Enable Web of Science if available
3. Note citation counts
4. Track influential papers

### For Topic Exploration
1. Enable cumulative search
2. Start broad, then narrow
3. Build session over time
4. Review all unique papers

## Technical Details

### Deduplication Algorithm

Papers are deduplicated using an enhanced fuzzy matching approach:

1. **Primary key**: DOI exact match
2. **Secondary key**: Fuzzy title similarity (Jaccard similarity with 85% threshold)
   - Titles are normalized: lowercase, punctuation removed, common prefixes stripped
   - Catches near-duplicates that differ slightly in formatting
   - Example: "Machine Learning in Drug Discovery" matches "machine learning in drug discovery"
3. **Priority**: Higher citation count preferred when duplicates found
4. **Scope**: Across all sources and session history

**Title Normalization Process:**
- Convert to lowercase
- Remove common prefixes ("the", "a", "an")
- Remove punctuation
- Normalize whitespace
- Calculate word-level Jaccard similarity

This improved deduplication catches:
- Case variations
- Punctuation differences
- Minor formatting changes
- Whitespace inconsistencies

Without fuzzy matching, papers like these would be treated as separate:
- "Machine Learning in Drug Discovery" 
- "machine learning in drug discovery"
- "Machine learning in drug discovery."

**Configuration:**
```python
# Default similarity threshold: 85%
# Can be adjusted in _titles_are_similar() function
similarity_threshold = 0.85
```

### Semantic Similarity

Uses sentence-transformers library:
- **Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Metric**: Cosine similarity
- **Encoding**: Query + paper abstracts
- **Ranking**: Similarity score × citation weight

### Session Storage

Session papers stored in browser:
- **Storage type**: Session storage (temporary)
- **Persistence**: Until logout or tab close
- **Size limit**: Browser-dependent (~5MB typical)
- **Privacy**: Client-side only, not uploaded

## Advanced Usage

### Programmatic Access

For batch processing or automation:

```python
import literature_search

# Search with specific sources
result = literature_search.search_papers(
    query="machine learning in genomics",
    top_k=20,
    sources=['semantic_scholar', 'arxiv'],
    previous_papers=None  # Or list of previous papers
)

# Access results
if result['success']:
    for paper in result['papers']:
        print(f"Title: {paper['title']}")
        print(f"DOI: {paper['doi']}")
        print(f"Source: {paper['source']}")
        print(f"Citations: {paper['citations']}")
        print()
```

### Custom Query Expansion

Extend query expansion for your domain:

```python
# In literature_search.py
synonym_map = {
    'crispr': ['cas9', 'gene editing', 'genome editing'],
    'protein': ['peptide', 'polypeptide', 'amino acid sequence'],
    # Add your terms
}
```

## Future Enhancements

Planned features:
- [ ] PubMed integration
- [ ] Google Scholar support
- [ ] Citation network visualization
- [ ] Saved search queries
- [ ] Email alerts for new papers
- [ ] Export to BibTeX/RIS
- [ ] Advanced filtering (year, journal, etc.)

## Support

For issues or questions:
1. Check this documentation
2. Review main README.md
3. Open GitHub issue
4. Contact repository maintainers

## References

- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [arXiv API](https://arxiv.org/help/api)
- [Web of Science API](https://developer.clarivate.com/)
- [Sentence Transformers](https://www.sbert.net/)
