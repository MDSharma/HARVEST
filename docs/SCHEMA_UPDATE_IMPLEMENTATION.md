# Schema Update Implementation - Summary

## Overview
This document summarizes the fix for the issue where new entity types and relation types were not appearing in the annotation dropdowns after upgrading HARVEST.

## Problem Statement
In commit 469712b, new relation types and entity types were added to the SCHEMA_JSON in the codebase. However, these new additions were not showing up in the triples dropdowns in the annotate or edit triples sections. The root cause was that the new types were added to the code but not to the database.

## Root Cause Analysis

### The Issue
1. **Code Updated**: New types were added to `SCHEMA_JSON` in both `harvest_store.py` and `frontend/__init__.py`
2. **Database Not Updated**: The `init_db()` function uses `INSERT OR IGNORE` which only inserts new types when tables are first created
3. **Schema Mismatch**: Backend `SCHEMA_JSON` had fewer types than the frontend
4. **Existing Databases Affected**: Users with existing databases didn't get the new types automatically

### Technical Details
- Entity and relation types are stored in database tables: `entity_types` and `relation_types`
- The frontend fetches these types via the `/api/choices` endpoint from the backend
- The backend reads from the database, not from the SCHEMA_JSON directly
- For new installations, `init_db()` populates the database with all types from SCHEMA_JSON
- For existing installations, the database tables remained unchanged after the code update

## Solution Implemented

### 1. Schema Update Script (`update_schema_types.py`)
Created a migration script that:
- Reads the latest SCHEMA_JSON from the code
- Compares it with the current database contents
- Adds any missing entity types and relation types
- Updates any changed entity type values
- Provides detailed output of changes made

**Key Features:**
- Safe to run multiple times (idempotent)
- Can be run on any database (new or existing)
- Supports custom database paths via environment variable
- Reports detailed summary of changes

### 2. Backend Schema Synchronization (`harvest_store.py`)
Updated the backend SCHEMA_JSON to include all types from the frontend:

**Added Entity Types:**
- Pathway
- Process
- Factor

**Added Relation Types:**
- encodes
- binds_to
- phosphorylates
- methylates
- acetylates
- activates
- inhibits
- represses
- interacts_with
- localizes_to
- expressed_in
- associated_with
- causes
- prevents
- co_occurs_with
- precedes
- follows

### 3. Documentation
Created comprehensive documentation:
- **docs/SCHEMA_UPDATE_GUIDE.md**: Complete guide with usage instructions, troubleshooting, and developer guidelines
- **docs/SCHEMA_UPDATE_QUICKSTART.md**: Quick reference for users experiencing dropdown issues
- **README.md**: Updated with schema update instructions
- **docs/README.md**: Updated index to reference new documentation

### 4. Testing
Created two comprehensive test scripts:
- **test_scripts/test_schema_sync.py**: Verifies that backend, frontend, and database schemas are synchronized
- **test_scripts/test_update_schema.py**: Verifies that the update script correctly updates old databases

## Complete Schema

### Entity Types (12)
1. Coordinates
2. Enzyme
3. Factor
4. Gene
5. Metabolite
6. Pathway
7. Process
8. Protein
9. QTL
10. Regulator
11. Trait
12. Variant

### Relation Types (32)
1. acetylates
2. activates
3. associated_with
4. binds_to
5. causes
6. co_occurs_with
7. contributes_to
8. decreases
9. develops_from
10. disrupts
11. does_not_influence
12. encodes
13. expressed_in
14. follows
15. increases
16. influences
17. inhers_in (inherent in)
18. inhibits
19. interacts_with
20. is_a
21. is_not_related_to
22. is_related_to
23. localizes_to
24. may_influence
25. may_not_influence
26. methylates
27. part_of
28. phosphorylates
29. precedes
30. prevents
31. regulates
32. represses

## User Instructions

### For Users with Existing Databases
Run the update script after pulling the latest code:
```bash
python3 update_schema_types.py
```

### For New Installations
No action needed - the database will be initialized with all types automatically.

## Verification
All implemented changes have been tested and verified:
- ✅ Backend and frontend schemas are synchronized
- ✅ Database initialization includes all types
- ✅ Update script correctly adds missing types to existing databases
- ✅ All tests pass
- ✅ No security vulnerabilities detected (CodeQL scan)

## Files Changed
1. `update_schema_types.py` - New file: Database update script
2. `harvest_store.py` - Modified: Updated SCHEMA_JSON
3. `README.md` - Modified: Added update instructions
4. `docs/README.md` - Modified: Added documentation references
5. `docs/SCHEMA_UPDATE_GUIDE.md` - New file: Comprehensive guide
6. `docs/SCHEMA_UPDATE_QUICKSTART.md` - New file: Quick reference
7. `test_scripts/test_schema_sync.py` - New file: Schema sync test
8. `test_scripts/test_update_schema.py` - New file: Update script test

## Future Considerations

### For Developers
When adding new entity or relation types:
1. Update SCHEMA_JSON in both `harvest_store.py` and `frontend/__init__.py`
2. Keep both schemas synchronized
3. Document the changes in commit messages
4. Inform users to run `update_schema_types.py` after upgrading

### For Maintenance
- The update script can be run periodically to ensure schema consistency
- Consider integrating the schema update into the regular migration process
- The test scripts can be used for continuous integration validation

## Security Considerations
- The update script only modifies the `entity_types` and `relation_types` tables
- No data loss occurs - only additions are made
- Database transactions ensure atomicity of updates
- CodeQL security scan found no vulnerabilities

## Impact Assessment

### Positive Impact
- Users will now see all available entity and relation types in dropdowns
- More comprehensive annotation capabilities
- Better alignment with biological ontologies
- Improved user experience

### Breaking Changes
None - this is purely additive. Existing annotations remain unchanged.

### Migration Path
Simple and safe:
1. Pull latest code
2. Run `python3 update_schema_types.py`
3. Restart application if running

## Conclusion
This fix successfully addresses the issue of missing entity and relation types in the annotation dropdowns. The solution is comprehensive, well-tested, and documented, ensuring that both new and existing users have access to the full schema capabilities.
