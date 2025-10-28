**Database Schema & Relationships**

```text
admin_users, projects, doi_metadata, sentences, triples
entity_types, relation_types, user_sessions
```

**Key Relationships:**
- **sentences → triples**: One-to-Many (one sentence → many triples)
- **projects → triples**: One-to-Many (one project → many triples)
- **triples** reference **entity_types** and **relation_types**
- **doi_metadata** stores DOI hashes for PDF mapping
