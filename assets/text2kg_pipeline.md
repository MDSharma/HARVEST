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
  - Optional LLM integration for enhanced extraction quality
- **LLM Services**: 
  - Supports OpenAI, Anthropic, Google Gemini, Google Vertex AI, Ollama, and other providers
  - Configurable via environment variables or CLI options
  - Improved extraction accuracy for complex documents
- **Environment Variables** (for API authentication):
  - `MARKER_OPENAI_API_KEY` - OpenAI API key
  - `MARKER_ANTHROPIC_API_KEY` - Anthropic API key
  - `MARKER_GEMINI_API_KEY` - Google Gemini API key
  - `MARKER_VERTEX_PROJECT_ID` - Google Vertex AI project ID
  - `MARKER_VERTEX_LOCATION` - Google Vertex AI location
  - `MARKER_VERTEX_MODEL` - Google Vertex AI model
  - `MARKER_OLLAMA_BASE_URL` - Ollama base URL
  - `MARKER_LLM_API_KEY` - Generic API key (backwards compatible)
- **Usage Examples**: 
  - Basic: `./scripts/convert_pdfs_with_marker.sh [project_name]`
  - OpenAI: `export MARKER_OPENAI_API_KEY="sk-..." && ./scripts/convert_pdfs_with_marker.sh my_project --llm_provider openai --llm_model gpt-4o`
  - Anthropic: `export MARKER_ANTHROPIC_API_KEY="sk-ant-..." && ./scripts/convert_pdfs_with_marker.sh my_project --llm_provider anthropic --llm_model claude-3-5-sonnet-20241022`
  - Vertex AI: `export MARKER_VERTEX_PROJECT_ID="my-project" && ./scripts/convert_pdfs_with_marker.sh --llm_provider google`

#### 2. Markdown Processing
- **Input**: Markdown files from conversion stage
- **Process**: Text preprocessing and structuring
- **Output**: Clean, structured text ready for NLP analysis
- **Features**:
  - Section identification
  - Metadata extraction
  - Text normalization

#### 3. NLP Model Selection (in development)
- **Available Models**:
  - **BioBERT**: Biomedical entity recognition
  - **SciBERT**: Scientific text understanding
  - **PubMedBERT**: PubMed article analysis
  - **lasUIE**: Universal Information Extraction for biomedical text
  - **Custom Models**: Domain-specific trained models
- **Purpose**: Select appropriate model for your domain and task

#### 4. Prompt Configuration (in development)
- **Entity Types**: Define biological entities to extract (genes, proteins, diseases, etc.)
- **Relationship Types**: Specify relationships to identify (regulates, interacts_with, etc.)
- **Context Settings**: Configure extraction parameters
- **Template Design**: Customize prompts for optimal extraction

#### 5. Trait Extraction (in development)
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
