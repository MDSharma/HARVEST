**Current schema (essential)**

{SCHEMA_JSON}

**Entity Types (span-attribute)**

Core biological entities:
- **Gene**: Genetic loci or gene names
- **Regulator**: Regulatory elements or factors
- **Variant**: Genetic variants or alleles
- **Protein**: Protein names or identifiers
- **Trait**: Phenotypes or observable characteristics
- **Enzyme**: Enzymatic proteins
- **QTL**: Quantitative trait loci
- **Coordinates**: Genomic coordinates or positions
- **Metabolite**: Metabolic compounds or small molecules
- **Pathway**: Biological pathways or networks
- **Process**: Biological processes or mechanisms
- **Factor**: Biotic or abiotic factors affecting biological systems

**Relation Types**

Ontological relations:
- **is_a**: Subclass or type relationship
- **part_of**: Component or compositional relationship
- **develops_from**: Developmental origin

General relations:
- **is_related_to**: Generic positive association
- **is_not_related_to**: Lack of association or negative result
- **influences**: General influence without specific direction
- **does_not_influence**: No influence observed
- **may_influence**: Potential or conditional influence
- **may_not_influence**: Possible lack of influence

Regulatory relations:
- **regulates**: General regulatory relationship
- **activates**: Positive regulation or activation
- **inhibits**: Negative regulation or inhibition
- **represses**: Gene expression repression
- **disrupts**: Disruption or interference

Quantitative relations:
- **increases**: Quantitative increase or upregulation
- **decreases**: Quantitative decrease or downregulation
- **contributes_to**: Partial contribution

Molecular interactions:
- **encodes**: Gene encodes protein relationship
- **binds_to**: Physical binding or interaction
- **interacts_with**: Generic molecular interaction
- **phosphorylates**: Phosphorylation modification
- **methylates**: Methylation modification
- **acetylates**: Acetylation modification

Spatial and temporal:
- **localizes_to**: Subcellular or tissue localization
- **expressed_in**: Expression pattern in tissue/cell type
- **precedes**: Temporal precedence
- **follows**: Temporal succession

Phenotypic associations:
- **associated_with**: Association with phenotype or condition
- **causes**: Causal relationship
- **prevents**: Prevention or protective effect
- **co_occurs_with**: Co-occurrence or correlation

Other:
- **inhers_in**: Inherent property or quality

**Tables**

```text
sentences(id, text, literature_link, created_at)
triples(id, sentence_id, source_entity_name, source_entity_attr, relation_type,
       sink_entity_name, sink_entity_attr, created_at)
entity_types(name, value)
relation_types(name)
```
