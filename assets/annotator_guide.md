# HARVEST Annotator Guide

HARVEST is a human-in-the-loop tool for extracting actionable insights from scientific literature, focusing on biological knowledge extraction. As an annotator, you label entities (e.g., genes, proteins, diseases) and their relationships in sentences from papers, creating (source, relation, sink) triples for a queryable knowledge graph.

## Quick Start

### 1. Enter Your Email
- Provide your email address for attribution and session tracking
- Required for all annotations to credit your contributions
- Stored securely for provenance tracking

### 2. Select a Project (Optional)
- Choose an existing project from the dropdown if working on a specific campaign
- Projects organize annotations and may provide suggested DOIs
- DOI selector shows 📄 emoji for papers with available PDFs
- Contact an admin if you need a new project created

### 3. Enter and Validate a DOI
- Enter the paper's DOI (e.g., `10.1038/nature12345`)
- System validates automatically and stores reference
- If DOI is part of selected project, it auto-confirms from the project's list
- Request admin assistance if PDF is needed but not available

### 4. View the PDF (If Available)
- PDFs load in the side panel viewer when available
- Toggle viewer visibility as needed
- Read content to identify relevant sentences for annotation

#### PDF Highlighting (Optional)
- Enable highlighting mode with the "Highlight" button
- Select text, choose a color from the picker
- Use "Save" (Ctrl+S) or "Clear All" to manage highlights
- Highlights saved directly to the PDF
- Keyboard shortcuts: H for highlight, arrow keys for navigation

### 5. Input the Sentence
- Manually type or paste the sentence to annotate
- Focus on sentences describing entities, traits, or relationships
- One sentence can have multiple triples for detailed extraction

### 6. Annotate with Triples

Create (source, relation, sink) triples to capture knowledge:

#### Source Entity
- The starting entity (e.g., gene, protein, pathway)
- Select entity type from dropdown
- Examples: "FLC gene", "Arabidopsis thaliana", "Cold stress"

#### Relation Type
- The connection between entities
- Select from comprehensive relation types:
  - **Ontological**: is_a, part_of, develops_from
  - **Regulatory**: regulates, activates, inhibits, represses
  - **Molecular**: encodes, binds_to, phosphorylates, interacts_with
  - **Quantitative**: increases, decreases
  - **Associations**: associated_with, causes, prevents, co_occurs_with
  - **Spatial/Temporal**: localizes_to, expressed_in, precedes, follows

#### Sink Entity
- The ending entity
- Select entity type from dropdown
- Examples: "flowering time", "vernalization pathway"

#### Multiple Triples
- Click "Add Triple" to create additional triples for the same sentence
- Capture complex relationships from detailed text
- Each triple represents one relationship

#### Custom Types
- If a needed label isn't available, choose "Other..."
- Suggest new entity or relation types
- Admins can add approved types to the database

### 7. Save Your Annotations
- Review sentence, DOI, and all triples
- Click "Save" to store in database
- Sentence stored once with all triples linked
- Includes your email, DOI, and project for provenance

### 8. Browse Annotations
- Switch to "Browse" tab to review saved annotations
- Filter by project, DOI, entity types, or relation types
- Customize displayed fields
- Export data for analysis
- Verify quality and consistency

## Entity & Relation Types

### Available Entity Types
- **Core Biological**: Gene, Protein, Variant, Enzyme, QTL, Metabolite
- **Phenotypic**: Trait (observable characteristics)
- **Regulatory**: Regulator, Coordinates
- **Systems**: Pathway, Process, Factor (biotic/abiotic)

### Relation Type Categories

See `schema.md` for complete list with descriptions. Key categories:
- Ontological relationships (is_a, part_of)
- Regulatory actions (activates, inhibits, represses)
- Molecular interactions (encodes, binds_to, phosphorylates)
- Quantitative changes (increases, decreases)
- Spatial/temporal (localizes_to, expressed_in, precedes)
- Associations (associated_with, causes, prevents)

## Tips for Quality Annotations

### Best Practices
1. **Be Specific**: Use precise entity names from the paper
2. **Stay Contextual**: Capture relationships as described in the sentence
3. **Multiple Triples**: One sentence often contains several relationships
4. **Verify DOIs**: Ensure DOI format is correct (10.xxxx/xxxxx)
5. **Review**: Use Browse tab to check your previous annotations

### Common Patterns
- **Gene → Protein**: Use "encodes" relation
- **Protein → Trait**: Use "influences", "increases", or "decreases"
- **Entity → Process**: Use "part_of" or "participates_in"
- **Causal**: Use "causes" or "prevents" for clear causality
- **Temporal**: Use "precedes" or "follows" for sequences

### What to Annotate
✅ **Good candidates:**
- Entity-relationship statements
- Experimental results
- Causal relationships
- Functional descriptions
- Regulatory mechanisms

❌ **Avoid:**
- Speculative statements without evidence
- Background information not specific to the study
- Purely methodological sentences
- Redundant information already captured

## Privacy & Data

- **Emails**: Used for attribution only
- **Data Source**: Annotations from public scientific literature
- **Security**: All data handled securely
- **Provenance**: Full tracking of contributor, DOI, and project

## Troubleshooting

### Common Issues
- **PDF doesn't load**: PDF may not be available - contact admin
- **DOI validation errors**: Check format (e.g., 10.1038/nature12345)
- **Dropdowns missing**: Clear browser cache (Ctrl+Shift+R)
- **Save fails**: Verify email and DOI are entered

### Getting Help
- Check the FAQ section
- Contact an admin for project-related questions
- Report issues on GitHub
- Request new entity/relation types via "Other..." option

## Advanced Features

### Keyboard Shortcuts
- **H**: Toggle highlight mode
- **Ctrl+S**: Save highlights
- **Arrow keys**: Navigate PDF pages
- **Tab**: Move between form fields

### Browser Compatibility
- Works best in modern browsers (Chrome, Firefox, Safari, Edge)
- Enable JavaScript
- Clear cache if experiencing issues

---

For admin features like project creation, PDF management, and database maintenance, see `admin_guide.md`.
