# Database Schema & Relationships

## Core Tables

### User & Authentication
- **admin_users**: Admin user credentials and permissions
- **user_sessions**: Session tracking and authentication state

### Project Management
- **projects**: Annotation project organization
  - Fields: id, name, description, doi_list (JSON), created_at, created_by
  - DOIs stored in lowercase for case-insensitive deduplication

### Literature & Metadata
- **doi_metadata**: DOI information and hashing
  - Fields: doi, doi_hash, title, authors, year, journal
  - DOI hash used for PDF file naming
- **sentences**: Text segments from papers
  - Fields: id, text, literature_link (DOI), contributor_email, project_id, created_at
  
### Annotations
- **triples**: Entity-relation-entity annotations
  - Fields: id, sentence_id, source_entity_name, source_entity_attr, relation_type, sink_entity_name, sink_entity_attr, contributor_email, project_id, created_at
  - Links to entity_types and relation_types

### Schema Definitions
- **entity_types**: Predefined entity categories (Gene, Protein, Pathway, etc.)
  - Fields: name, value, description
- **relation_types**: Predefined relationship types (encodes, activates, etc.)
  - Fields: name, value, category, description

## Key Relationships

### One-to-Many Relationships
```text
projects → sentences (via project_id)
projects → triples (via project_id)
sentences → triples (via sentence_id)
```

### Reference Relationships
```text
triples.source_entity_attr → entity_types.name
triples.sink_entity_attr → entity_types.name
triples.relation_type → relation_types.name
```

### Data Flow
```text
1. DOI validated → doi_metadata created
2. Sentence entered → sentences created (with project_id if selected)
3. Triples added → triples created (linked to sentence_id and project_id)
4. PDF uploaded → stored with doi_hash filename
```

## Schema Categories

### Entity Types (span-attribute)
- Core Biological: Gene, Protein, Variant, Enzyme, QTL, Metabolite
- Phenotypic: Trait
- Regulatory: Regulator, Coordinates
- Systems: Pathway, Process, Factor

### Relation Types
Organized into categories:
- **Ontological**: is_a, part_of, develops_from
- **Regulatory**: regulates, activates, inhibits, represses
- **Molecular**: encodes, binds_to, phosphorylates, methylates, acetylates, interacts_with
- **Quantitative**: increases, decreases, contributes_to
- **Spatial/Temporal**: localizes_to, expressed_in, precedes, follows
- **Associations**: associated_with, causes, prevents, co_occurs_with
- **Influence**: influences, may_influence, does_not_influence, may_not_influence, disrupts
- **Other**: inhers_in, is_related_to, is_not_related_to

## Data Integrity

### Constraints
- Foreign keys enforce referential integrity
- Unique constraints on DOI hashes
- NOT NULL on critical fields (emails, text, DOIs)
- JSON validation for project DOI lists

### Normalization
- All DOIs normalized to lowercase
- Case-insensitive deduplication in projects
- Consistent datetime formats (ISO 8601)

### Indexing
Key indexes for performance:
- doi_metadata.doi_hash
- sentences.literature_link
- triples.sentence_id
- triples.project_id
- triples.source_entity_attr
- triples.relation_type
- triples.sink_entity_attr

## File System Integration

### PDF Storage
```text
project_pdfs/
  ├── project_1/
  │   ├── {doi_hash_1}.pdf
  │   ├── {doi_hash_2}.pdf
  │   └── ...
  ├── project_2/
  └── ...
```

### Highlights Storage
```text
Highlights saved directly in PDF files
No separate database storage required
```

## Query Patterns

### Common Queries
```sql
-- Get all triples for a sentence
SELECT * FROM triples WHERE sentence_id = ?;

-- Get all annotations for a project
SELECT s.*, t.* 
FROM sentences s 
JOIN triples t ON s.id = t.sentence_id 
WHERE s.project_id = ?;

-- Find all relationships of a type
SELECT * FROM triples WHERE relation_type = 'activates';

-- Get contributor statistics
SELECT contributor_email, COUNT(*) as annotation_count
FROM triples
GROUP BY contributor_email;
```

### Performance Considerations
- Use indexes for large dataset queries
- Batch inserts for bulk operations
- Regular database maintenance (VACUUM, ANALYZE)
- Monitor query performance with EXPLAIN

## Maintenance

### Regular Tasks
- Clean orphaned sentences (sentences with no triples)
- Verify referential integrity
- Update statistics for query optimizer
- Archive old sessions
- Backup database regularly

### Data Migration
- Version control for schema changes
- Migration scripts in `/migrations` directory
- Backward compatibility considerations
- Test migrations on copy before production

---

For detailed entity and relation type definitions, see `schema.md`.
