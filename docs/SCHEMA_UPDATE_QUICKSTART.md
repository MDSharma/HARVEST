# Schema Update Fix - Quick Reference

## Problem
After upgrading to the latest version, new entity types and relation types were not appearing in the annotation dropdowns.

## Root Cause
New types were added to the code (SCHEMA_JSON), but the database tables `entity_types` and `relation_types` were not updated automatically for existing installations.

## Solution
Run the schema update script:

```bash
python3 update_schema_types.py
```

This will:
- Add any missing entity types to your database
- Add any missing relation types to your database
- Show a summary of changes made

## Expected Output

```
Updating schema types in database: harvest.db

Updating entity types...
  + Added entity type: Metabolite
  + Added entity type: Coordinates
  + Added entity type: Pathway
  + Added entity type: Process
  + Added entity type: Factor
  ✓ Added 5 new entity types

Updating relation types...
  + Added relation type: may_influence
  + Added relation type: may_not_influence
  + Added relation type: contributes_to
  + Added relation type: inhers_in
  + Added relation type: encodes
  + Added relation type: binds_to
  + Added relation type: phosphorylates
  + Added relation type: methylates
  + Added relation type: acetylates
  + Added relation type: activates
  + Added relation type: inhibits
  + Added relation type: represses
  + Added relation type: interacts_with
  + Added relation type: localizes_to
  + Added relation type: expressed_in
  + Added relation type: associated_with
  + Added relation type: causes
  + Added relation type: prevents
  + Added relation type: co_occurs_with
  + Added relation type: precedes
  + Added relation type: follows
  ✓ Added 21 new relation types

============================================================
Summary:
  Total entity types in database: 12
  Total relation types in database: 32
============================================================

✅ Schema types update completed successfully!
```

## New Schema Types

### New Entity Types (5)
- **Metabolite**: metabolite
- **Coordinates**: coordinates
- **Pathway**: pathway
- **Process**: process
- **Factor**: factor (biotic or abiotic factors)

### New Relation Types (21)
- may_influence
- may_not_influence
- contributes_to
- inhers_in (inherent in)
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

## Full Documentation
See [SCHEMA_UPDATE_GUIDE.md](SCHEMA_UPDATE_GUIDE.md) for complete documentation.

## Troubleshooting

### "Database does not exist yet"
The database hasn't been created. Run the application first, then run the update script.

### No changes made
Your database is already up to date. No action needed.

### Permission denied
Ensure you have write permissions to the database file and its directory.

## For Developers
When adding new entity or relation types to SCHEMA_JSON:
1. Update both `harvest_store.py` and `frontend/__init__.py`
2. Document the changes in commit messages
3. Inform users to run `update_schema_types.py`
