# Text2KG Pipeline

## Automated Triple Extraction Workflow

The Text2KG pipeline enables automated knowledge graph creation from PDF documents through a multi-stage process:

### Pipeline Stages

#### 1. Marker-based PDF → Markdown Conversion
- **Input**: PDF documents from project collection
- **Tool**: [Marker](https://github.com/datalab-to/marker) - Advanced PDF to Markdown converter
- **Output**: Structured markdown files preserving document hierarchy
- **Benefits**: 
  - Accurate text extraction with layout preservation
  - Table and figure detection
  - Mathematical formula conversion
  - Citation and reference handling

#### 2. Markdown Processing
- **Input**: Markdown files from conversion stage
- **Process**: Text preprocessing and structuring
- **Output**: Clean, structured text ready for NLP analysis
- **Features**:
  - Section identification
  - Metadata extraction
  - Text normalization

#### 3. NLP Model Selection
- **Available Models**:
  - **BioBERT**: Biomedical entity recognition
  - **SciBERT**: Scientific text understanding
  - **PubMedBERT**: PubMed article analysis
  - **Custom Models**: Domain-specific trained models
- **Purpose**: Select appropriate model for your domain and task

#### 4. Prompt Configuration
- **Entity Types**: Define biological entities to extract (genes, proteins, diseases, etc.)
- **Relationship Types**: Specify relationships to identify (regulates, interacts_with, etc.)
- **Context Settings**: Configure extraction parameters
- **Template Design**: Customize prompts for optimal extraction

#### 5. Trait Extraction
- **Process**: Apply NLP model with configured prompts
- **Output**: Structured entity-relationship triples
- **Validation**: Confidence scoring and filtering
- **Features**:
  - Entity linking to ontologies
  - Disambiguation and normalization
  - Quality assessment

#### 6. Knowledge Graph Creation
- **Input**: Validated triples from extraction
- **Process**: Graph construction and enrichment
- **Output**: Queryable knowledge graph
- **Integration**: Automatic import into HARVEST annotation database
- **Visualization**: Browse and refine extracted relationships

---

## Getting Started

1. **Convert PDFs**: Use the conversion script to process your document collection
2. **Configure Pipeline**: Select NLP model and define extraction parameters
3. **Run Extraction**: Execute automated triple extraction
4. **Review Results**: Validate and refine extracted knowledge
5. **Export Graph**: Generate knowledge graph for analysis and sharing

---

## Benefits

- **Automation**: Reduce manual annotation time
- **Scalability**: Process large document collections
- **Consistency**: Standardized extraction across documents
- **Integration**: Seamlessly merge with manual annotations
- **Flexibility**: Customize for different domains and use cases
