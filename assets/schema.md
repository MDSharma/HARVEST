**Current schema (essential)**

{SCHEMA_JSON}

**Tables**

```text
sentences(id, text, literature_link, created_at)
triples(id, sentence_id, source_entity_name, source_entity_attr, relation_type,
       sink_entity_name, sink_entity_attr, created_at)
entity_types(name, value)
relation_types(name)
```
