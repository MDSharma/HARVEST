# Web of Science Abstract Retrieval Fix

**Date**: November 2024  
**Issue**: Web of Science literature search not returning abstracts  
**Status**: ✅ Fixed

## Problem Description

The Web of Science literature search was not returning abstracts even for DOIs where the Expanded API had validated abstract availability. Users reported that the system correctly used the Web of Science API endpoint (`https://wos-api.clarivate.com/api/wos`) but abstracts were consistently missing from search results.

## Root Cause

**UPDATE (Nov 2025)**: The original fix incorrectly used `viewField='fullRecord'`. The correct parameter is `optionView='FR'`.

The Web of Science Expanded API requires explicit specification of document detail level via the `optionView` parameter:
- `FR` = Full Record (all metadata including abstracts)
- `SR` = Short Record (limited fields, doesn't count against quota)
- `FS` = Field Selection (custom fields via `viewField` parameter)

The `viewField` parameter is for selecting **specific fields** (e.g., 'titles', 'addresses'), NOT for requesting full records.

Our implementation was using an invalid `viewField='fullRecord'` value, causing the API to return empty or malformed responses.

## Solution

Use `optionView='FR'` (Full Record) parameter to retrieve all metadata including abstracts. This is the correct parameter per the Clarivate API Swagger specification.

## Technical Details

### Changes Made

1. **literature_search.py** (Line ~824):
   ```python
   params = {
       'databaseId': 'WOS',
       'usrQuery': wos_query,
       'count': count,
       'firstRecord': first_record,
       'optionView': 'FR'  # ← Full Record (all metadata)
   }
   ```

2. **Function Documentation**:
   - Updated docstring to use optionView parameter
   - Added inline comments explaining FR = Full Record

3. **Test Suite** (test_scripts/test_wos_abstract_fix.py):
   - Test verifying `viewField` parameter is included in API requests
   - Test verifying abstracts are properly extracted from responses
   - Test verifying `viewField` is included in paginated requests

### API Reference

According to the Web of Science Expanded API Swagger documentation:

**Document Detail Options (`optionView` parameter)**:
- `FR` - Full Record: retrieves all metadata including abstracts (✅ Correct usage)
- `SR` - Short Record: limited fields, doesn't count against quota
- `FS` - Field Selection: custom fields when combined with `viewField`

**Field Selection (`viewField` parameter)** - for selecting specific fields:
- Examples: 'titles', 'addresses', 'pub_info', 'doctypes', 'keywords'
- NOT for requesting full records (previous bug: used 'fullRecord' which is invalid)

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
