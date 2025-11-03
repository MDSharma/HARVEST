# Enhanced Semantic Search - Quick Start Guide

## What's New

Your HARVEST application now has enhanced semantic search capabilities!

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
