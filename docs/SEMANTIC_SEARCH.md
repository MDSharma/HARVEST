# Enhanced Semantic Search Documentation

## Overview

The HARVEST application includes an enhanced semantic search capability that allows users to discover relevant academic papers from multiple sources with advanced features like API selection, cumulative session building, and intelligent deduplication.

## Features

### 1. Multi-Source Search

The semantic search system can query multiple academic databases simultaneously:

- **Semantic Scholar** - Open academic paper search from AI2
  - Largest open corpus
  - Includes citation counts
  - Free to use, no API key required
  
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

### API Information

- **Endpoint**: `https://api.clarivate.com/api/wos`
- **Database**: WOS (Web of Science Core Collection)
- **Implementation**: Based on [Clarivate's official examples](https://github.com/clarivate/wos_api_usecases/tree/main/python/societal_impact_analytics)
- **Max results per query**: 100

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

Papers are deduplicated using:
1. **Primary key**: DOI exact match
2. **Secondary key**: Title similarity (case-insensitive)
3. **Priority**: Higher citation count preferred
4. **Scope**: Across all sources and session history

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
