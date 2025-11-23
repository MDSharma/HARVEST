# Web of Science Abstract Retrieval Fix

**Date**: November 2024  
**Issue**: Web of Science literature search not returning abstracts  
**Status**: ✅ Fixed

## Problem Description

The Web of Science literature search was not returning abstracts even for DOIs where the Expanded API had validated abstract availability. Users reported that the system correctly used the Web of Science API endpoint (`https://wos-api.clarivate.com/api/wos`) but abstracts were consistently missing from search results.

## Root Cause

The Web of Science Expanded API requires explicit specification of which fields to retrieve via the `viewField` parameter. Without this parameter, the API defaults to a 'summary' view that **excludes abstracts** and other detailed metadata.

Our implementation was missing this critical parameter, causing the API to return only basic metadata (title, authors, year, DOI) without abstracts.

## Solution

Added the `viewField='fullRecord'` parameter to all Web of Science API requests. This parameter instructs the API to return the complete record including:

- Full abstracts
- Complete author information
- Keywords and subject categories
- Citation data
- All identifiers (DOI, PMID, etc.)

## Technical Details

### Changes Made

1. **literature_search.py** (Line ~658):
   ```python
   params = {
       'databaseId': 'WOS',
       'usrQuery': wos_query,
       'count': count,
       'firstRecord': first_record,
       'viewField': 'fullRecord'  # ← Added this parameter
   }
   ```

2. **Function Documentation**:
   - Updated docstring to document this requirement
   - Added inline comments explaining why the parameter is critical

3. **Test Suite** (test_scripts/test_wos_abstract_fix.py):
   - Test verifying `viewField` parameter is included in API requests
   - Test verifying abstracts are properly extracted from responses
   - Test verifying `viewField` is included in paginated requests

### API Reference

According to the Web of Science Expanded API documentation:

**Available `viewField` Options**:
- `fullRecord` - Complete record including abstracts (✅ Now using this)
- `summary` - Basic metadata only, no abstracts (❌ Was defaulting to this)
- `abstract` - Abstract field only

## Verification

### Tests
- ✅ All existing literature search tests pass (10/10)
- ✅ New abstract fix tests pass (3/3)
- ✅ No breaking changes to existing functionality

### Expected Behavior
After this fix:
1. Web of Science searches now return abstracts when available in WoS database
2. Abstract extraction logic correctly processes the fuller API response
3. Papers without abstracts still handled gracefully (empty string)
4. All other metadata continues to work as before

## Impact

**Before Fix**:
- Web of Science results lacked abstracts
- Reduced usefulness of WoS search results
- Users couldn't perform semantic reranking on WoS-only searches
- Missing context for paper relevance assessment

**After Fix**:
- ✅ Abstracts now retrieved from Web of Science API
- ✅ Full metadata available for all WoS papers
- ✅ Semantic reranking works properly with WoS results
- ✅ Better user experience with complete paper information

## Related Documentation

- **User Documentation**: Updated `docs/SEMANTIC_SEARCH.md` with technical note
- **API Reference**: Web of Science API endpoint correctly documented
- **Code Comments**: Added explanatory comments in `literature_search.py`

## Migration Notes

**For Users**:
- No action required - fix is transparent
- Existing WoS API keys continue to work
- No configuration changes needed

**For Developers**:
- If extending WoS integration, always include `viewField='fullRecord'`
- Test suite includes examples of proper API usage
- See `test_scripts/test_wos_abstract_fix.py` for implementation examples

## References

- [Web of Science Expanded API Documentation](https://developer.clarivate.com/apis/wos)
- [Clarivate API Examples](https://github.com/clarivate/wos_api_usecases)
- Issue: Web of Science abstracts not returning
- PR: Fix Web of Science abstract retrieval by adding viewField parameter

---

**Keywords**: Web of Science, API, abstracts, viewField, literature search, bug fix
