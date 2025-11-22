# Schema Update Guide

## Overview

HARVEST uses a SQLite database to store entity types and relation types that appear in the annotation dropdowns. When new entity types or relation types are added to the codebase, existing databases need to be updated to reflect these changes.

## The Problem

When new entity types or relation types are added to `SCHEMA_JSON` in `harvest_store.py`:

1. The code is updated with the new types
2. New database installations will have all types automatically
3. **Existing databases will NOT have the new types**

This happens because:
- The `init_db()` function uses `INSERT OR IGNORE` which only inserts values that don't already exist
- If the database tables already exist, new types from the code won't be automatically added
- The dropdown options in the UI are fetched from the database, not from the code

## The Solution

Use the `update_schema_types.py` script to synchronize your database with the latest schema.

### Running the Update Script

**Method 1: Using the default database location**

```bash
python3 update_schema_types.py
```

This will update the database at the path specified in `config.py` (default: `harvest.db`).

**Method 2: Using a custom database location**

```bash
HARVEST_DB=/path/to/your/database.db python3 update_schema_types.py
```

### What the Script Does

The script:
1. Reads the latest `SCHEMA_JSON` from `harvest_store.py`
2. Compares it with the current database contents
3. Adds any missing entity types and relation types
4. Updates any entity type values that have changed
5. Reports a summary of changes made

### Example Output

```
Updating schema types in database: harvest.db

Updating entity types...
  + Added entity type: Metabolite
  + Added entity type: Coordinates
  ✓ Added 2 new entity types

Updating relation types...
  + Added relation type: may_influence
  + Added relation type: may_not_influence
  + Added relation type: contributes_to
  + Added relation type: inhers_in
  ✓ Added 4 new relation types

============================================================
Summary:
  Total entity types in database: 9
  Total relation types in database: 15
============================================================

✅ Schema types update completed successfully!
```

## When to Run This Script

Run the update script after:
- Pulling the latest code changes that include schema updates
- Upgrading to a new version of HARVEST
- Noticing that new entity types or relation types are missing from dropdowns

## For Developers: Adding New Schema Types

When adding new entity types or relation types:

1. **Update the code** in `harvest_store.py`:
   ```python
   SCHEMA_JSON = {
       "span-attribute": {
           "Gene": "gene",
           "Protein": "protein",
           "NewEntityType": "new_entity_type",  # Add your new type here
           # ... other types
       },
       "relation-type": {
           "is_a": "is_a",
           "new_relation": "new_relation",  # Add your new type here
           # ... other types
       }
   }
   ```

2. **Document the change** in your commit message

3. **Notify users** to run `update_schema_types.py` after pulling your changes

4. **Consider updating** the migration script if making major schema changes

## Current Schema

As of the latest version, HARVEST supports:

### Entity Types (span-attribute)
- **Gene**: gene
- **Regulator**: regulator
- **Variant**: variant
- **Protein**: protein
- **Trait**: phenotype
- **Enzyme**: enzyme
- **QTL**: qtl
- **Coordinates**: coordinates
- **Metabolite**: metabolite

### Relation Types
- is_a
- part_of
- develops_from
- is_related_to
- is_not_related_to
- increases
- decreases
- influences
- does_not_influence
- may_influence
- may_not_influence
- disrupts
- regulates
- contributes_to
- inhers_in

## Troubleshooting

### "Database does not exist yet"
If you see this message, the database hasn't been created yet. Run the HARVEST application first to create the database, then run the update script.

### Permission Denied
Ensure you have write permissions to the database file and its directory.

### No Changes Made
If the script reports no changes, your database is already up to date with the latest schema.

## Related Files

- `harvest_store.py` - Contains the SCHEMA_JSON definition
- `update_schema_types.py` - The database update script
- `migrate_db_v2.py` - Database migration script for structural changes
- `config.py` - Configuration including database path

## See Also

- [Installation Guide](INSTALLATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- Database schema documentation in `assets/db_model.md`
