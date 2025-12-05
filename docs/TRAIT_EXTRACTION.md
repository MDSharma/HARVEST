# Trait Extraction Guide

HARVEST includes a comprehensive NLP-based trait extraction system that automatically extracts biological entity-relation triples from scientific literature using state-of-the-art NLP models.

## Overview

The trait extraction module supports:

- **Multiple NLP Backends**: LasUIE, Hugging Face Transformers, spaCy, AllenNLP
- **Remote/Local Execution**: Run models locally or on a remote GPU server
- **Interactive Validation**: Review and validate extracted triples
- **Training Support**: Fine-tune models on your own data
- **Seamless Integration**: Works with existing HARVEST projects and workflows

## Architecture

### Components

1. **Adapters**: Interface to different NLP backends (spaCy, Hugging Face, LasUIE, AllenNLP)
2. **Service Layer**: Manages extraction jobs and switches between local/remote execution
3. **Storage**: Extends HARVEST database with extraction-specific tables
4. **API**: RESTful endpoints for upload, extraction, and triple management
5. **Remote Server** (optional): FastAPI server for GPU-intensive operations

### Database Schema

The trait extraction feature adds three new tables:

- **trait_documents**: Stores documents (PDFs/texts) for extraction
- **trait_extraction_jobs**: Tracks extraction job status and progress
- **trait_model_configs**: Stores model configuration profiles

The existing **triples** table is extended with:
- `model_profile`: Which model extracted the triple
- `confidence`: Confidence score (0.0 to 1.0)
- `status`: raw/accepted/rejected/edited
- `trait_name`, `trait_value`, `unit`: Structured trait information
- `job_id`, `document_id`: Links to extraction job and document

## Setup

### 1. Database Migration

After installing/upgrading, run the migration:

```bash
python migrate_trait_extraction.py
```

This adds the necessary tables and columns.

### 2. Configuration

Edit `config.py` to configure trait extraction:

```python
# Enable trait extraction
ENABLE_TRAIT_EXTRACTION = True

# Execution mode
TRAIT_EXTRACTION_LOCAL_MODE = True  # Set to False for remote server

# Remote server (if LOCAL_MODE=False)
TRAIT_EXTRACTION_URL = "http://gpu-server:8000"
TRAIT_EXTRACTION_API_KEY = "your-secret-key"  # Optional

# Settings
TRAIT_EXTRACTION_MIN_CONFIDENCE = 0.5  # Filter low-confidence triples
TRAIT_EXTRACTION_MODELS_CACHE = "trait_extraction/models_cache"
```

### 3. Install Dependencies

For **local execution**, install NLP libraries:

```bash
pip install spacy transformers torch allennlp allennlp-models
python -m spacy download en_core_web_sm
```

For **remote server only**, install FastAPI:

```bash
pip install fastapi uvicorn
```

### 4. Run Tests

Verify installation:

```bash
python test_scripts/test_trait_extraction.py
```

## Usage

### Local Execution Mode

In local mode, extraction runs directly in the HARVEST process. Best for:
- Development and testing
- Small-scale extractions
- When you have GPU available on the HARVEST server

To use local mode:

1. Set `TRAIT_EXTRACTION_LOCAL_MODE = True` in `config.py`
2. Install NLP libraries (see Setup above)
3. Use the API or UI to run extractions

### Remote Execution Mode

In remote mode, HARVEST calls a separate GPU server for extraction. Best for:
- Production deployments
- Large-scale extractions
- When HARVEST runs on a non-GPU server

To use remote mode:

#### On GPU Server:

1. Clone HARVEST repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set API key: `export TRAIT_EXTRACTION_API_KEY="your-secret-key"`
4. Start server:

```bash
python trait_extraction_server.py
# or with uvicorn:
uvicorn trait_extraction_server:app --host 0.0.0.0 --port 8000
```

#### On HARVEST Server:

1. Set in `config.py`:
```python
TRAIT_EXTRACTION_LOCAL_MODE = False
TRAIT_EXTRACTION_URL = "http://gpu-server:8000"
TRAIT_EXTRACTION_API_KEY = "your-secret-key"
```

2. Use API/UI normally - extraction requests are automatically forwarded to remote server

## API Endpoints

All endpoints require admin authentication.

### Upload PDFs

```
POST /api/trait-extraction/upload-pdfs
Content-Type: multipart/form-data

Form data:
  files: PDF file(s)
  project_id: (optional) Project ID
  admin_email: Admin email
  admin_password: Admin password
```

### List Documents

```
GET /api/trait-extraction/documents?project_id=1&page=1&per_page=50
```

### List Available Models

```
GET /api/trait-extraction/models
```

Returns:
```json
{
  "ok": true,
  "models": [
    {
      "id": "spacy_bio",
      "name": "spaCy Biological NER",
      "description": "Fast spaCy pipeline...",
      "backend": "spacy"
    },
    ...
  ],
  "execution_mode": "local"
}
```

### Create Extraction Job

```
POST /api/trait-extraction/jobs
Content-Type: application/json

{
  "document_ids": [1, 2, 3],
  "model_profile": "spacy_bio",
  "project_id": 1,
  "admin_email": "admin@example.com",
  "admin_password": "password"
}
```

### Get Job Status

```
GET /api/trait-extraction/jobs/123
```

Returns:
```json
{
  "ok": true,
  "job": {
    "id": 123,
    "status": "completed",
    "progress": 3,
    "total": 3,
    "results": {
      "total_triples": 45
    }
  }
}
```

### List Extracted Triples

```
GET /api/trait-extraction/triples?job_id=123&min_confidence=0.7&page=1
```

### Update Triple Status

```
PATCH /api/trait-extraction/triples/456
Content-Type: application/json

{
  "status": "accepted",
  "edits": {
    "relation_type": "regulates"
  },
  "admin_email": "admin@example.com",
  "admin_password": "password"
}
```

## Model Profiles

### spaCy Biological NER

- **Backend**: spaCy
- **ID**: `spacy_bio`
- **Use**: Fast, production-ready entity recognition
- **Features**: Custom biological entity rules
- **Training**: Supported

### Hugging Face NER

- **Backend**: Transformers
- **ID**: `huggingface_ner`
- **Use**: Pre-trained BERT-based NER
- **Features**: High accuracy, flexible
- **Training**: Supported

### LasUIE

- **Backend**: LasUIE (requires external installation)
- **ID**: `lasuie`
- **Use**: Universal information extraction
- **Features**: Generative approach, handles complex relations
- **Training**: Supported

### AllenNLP SRL

- **Backend**: AllenNLP
- **ID**: `allennlp_srl`
- **Use**: Semantic role labeling for relation extraction
- **Features**: Advanced linguistic analysis
- **Training**: Not implemented

## Workflow

### Basic Extraction Workflow

1. **Upload Documents**
   - Upload PDFs via API or UI
   - Text is automatically extracted

2. **Select Model**
   - Choose model profile based on your needs
   - Consider accuracy vs. speed tradeoffs

3. **Run Extraction**
   - Create extraction job
   - Monitor progress

4. **Review Triples**
   - Filter by confidence threshold
   - Review extracted triples
   - Accept, reject, or edit

5. **Use Results**
   - Accepted triples are available in HARVEST
   - Export or annotate further

### Training-Assisted Workflow

1. **Prepare Training Data**
   - Manually annotate a small set of documents
   - Export as training dataset

2. **Fine-tune Model**
   - Train model on your data
   - Evaluate performance

3. **Extract with Custom Model**
   - Use fine-tuned model for extraction
   - Higher accuracy on domain-specific texts

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'spacy'`

**Solution**: Install NLP dependencies:
```bash
pip install spacy transformers torch
python -m spacy download en_core_web_sm
```

### Remote Server Not Responding

**Problem**: `Connection refused` when using remote mode

**Solution**:
1. Check remote server is running: `curl http://gpu-server:8000/health`
2. Check firewall allows connection
3. Verify URL in `config.py` is correct
4. Check API key matches

### Low Confidence Scores

**Problem**: Many triples have low confidence

**Solutions**:
- Use a more sophisticated model (LasUIE or fine-tuned Hugging Face)
- Fine-tune model on domain-specific data
- Adjust `TRAIT_EXTRACTION_MIN_CONFIDENCE` threshold

### Out of Memory

**Problem**: CUDA out of memory errors

**Solutions**:
- Reduce batch size in model params
- Use remote server with more GPU memory
- Process fewer documents per job
- Use lighter model (spaCy instead of transformers)

## Advanced Configuration

### Custom Model Profiles

Add custom profiles in `trait_extraction/config.py`:

```python
model_profiles = {
    "my_custom_model": {
        "name": "My Custom Model",
        "description": "Fine-tuned for my domain",
        "backend": "huggingface",
        "params": {
            "model_name": "path/to/my/model",
            "task": "ner",
            "device": "cuda",
            "batch_size": 8
        }
    }
}
```

### LasUIE Integration

To use LasUIE:

1. Clone LasUIE repository:
```bash
git clone https://github.com/ChocoWu/LasUIE.git
export LASUIE_PATH=/path/to/LasUIE
```

2. Follow LasUIE setup instructions

3. Use `lasuie` model profile in HARVEST

## Performance Tips

- **For speed**: Use spaCy adapter
- **For accuracy**: Use LasUIE or fine-tuned Hugging Face models
- **For GPU utilization**: Use remote server mode
- **For batch processing**: Process multiple documents per job
- **For memory**: Reduce batch size, use gradient checkpointing

## Security Considerations

- Always use authentication for API endpoints
- Use HTTPS for remote server connections
- Set strong API keys for remote server
- Sanitize uploaded PDF content
- Validate extracted text before insertion
- Rate limit extraction requests

## See Also

- [HARVEST Main Documentation](../README.md)
- [API Reference](../docs/API.md)
- [Deployment Guide](../docs/DEPLOYMENT_GUIDE.md)
- [LasUIE Repository](https://github.com/ChocoWu/LasUIE)
- [spaCy Documentation](https://spacy.io)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers/)
