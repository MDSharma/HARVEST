# Literature Review Feature - ASReview Integration

## Overview

The Literature Review feature integrates ASReview, an AI-powered systematic review tool, into HARVEST. This feature helps researchers efficiently screen and shortlist literature by using active learning to predict paper relevance and prioritize review efforts.

## What is ASReview?

[ASReview](https://asreview.ai) is an open-source active learning tool for systematic literature reviews. It uses machine learning to:

1. **Learn from your decisions**: The AI model trains on papers you mark as relevant or irrelevant
2. **Predict relevance**: Estimates which unscreened papers are most likely to be relevant
3. **Prioritize screening**: Shows you the most relevant papers first
4. **Reduce workload**: Can reduce manual screening effort by 95% or more

### Key Benefits

- **Efficient screening**: Focus on likely-relevant papers first
- **AI-assisted decisions**: ML model learns your criteria over time
- **Systematic approach**: Structured review process with progress tracking
- **Export results**: Get list of relevant papers for further analysis

## Architecture

The Literature Review feature uses a **remote service architecture** for optimal performance:

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│                 │         │                  │         │                  │
│  HARVEST        │  HTTP   │  HARVEST         │  HTTP   │  ASReview        │
│  Frontend       │────────▶│  Backend         │────────▶│  Service         │
│  (Browser)      │         │  (Flask)         │         │  (GPU Server)    │
│                 │         │                  │         │                  │
└─────────────────┘         └──────────────────┘         └──────────────────┘
```

### Why Remote Service?

ASReview requires:
- **GPU acceleration**: For fast ML model training and inference
- **ML dependencies**: TensorFlow/PyTorch and other heavy libraries
- **Computational resources**: CPU/RAM for large datasets

By deploying ASReview on a separate GPU-enabled host, HARVEST remains lightweight while leveraging powerful ML capabilities when needed.

## Setup Instructions

### Step 1: Deploy ASReview Service

ASReview can be deployed in several ways:

#### Option A: Using Docker (Recommended)

```bash
# Pull official ASReview Docker image
docker pull asreview/asreview:latest

# Run ASReview service on GPU-enabled host
docker run -d \
  --name asreview-service \
  --gpus all \
  -p 5275:5275 \
  -v asreview-data:/data \
  --restart unless-stopped \
  asreview/asreview:latest \
  asreview lab --host 0.0.0.0 --port 5275
```

#### Option B: Using Python Virtual Environment

```bash
# On GPU-enabled server
ssh gpu-server

# Create virtual environment
python3 -m venv asreview-env
source asreview-env/bin/activate

# Install ASReview with GPU support
pip install asreview[all]
pip install tensorflow-gpu  # or pytorch with GPU support

# Start ASReview service
asreview lab --host 0.0.0.0 --port 5275
```

#### Option C: Using systemd Service

Create `/etc/systemd/system/asreview.service`:

```ini
[Unit]
Description=ASReview Service for HARVEST
After=network.target

[Service]
Type=simple
User=asreview
WorkingDirectory=/opt/asreview
ExecStart=/opt/asreview/venv/bin/asreview lab --host 0.0.0.0 --port 5275
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable asreview
sudo systemctl start asreview
```

### Step 2: Configure HARVEST

Edit `/home/runner/work/HARVEST/HARVEST/config.py`:

```python
# Literature Review Configuration (ASReview Integration)
ENABLE_LITERATURE_REVIEW = True  # Enable the feature

# ASReview Service URL - Update this with your ASReview server URL
ASREVIEW_SERVICE_URL = "http://asreview-gpu-host:5275"

# Optional: API key if your ASReview service requires authentication
ASREVIEW_API_KEY = ""

# Timeout settings
ASREVIEW_REQUEST_TIMEOUT = 300  # 5 minutes for long operations
ASREVIEW_CONNECTION_TIMEOUT = 10  # 10 seconds to establish connection
```

#### Configuration Options

**Direct Connection:**
```python
ASREVIEW_SERVICE_URL = "http://192.168.1.100:5275"
```

**Via Nginx Proxy:**
```python
ASREVIEW_SERVICE_URL = "https://yourdomain.com/asreview"
```

**Same Host (for testing):**
```python
ASREVIEW_SERVICE_URL = "http://localhost:5275"
```

### Step 3: Configure Nginx (Optional)

If using nginx proxy for ASReview service:

Add to your nginx configuration:

```nginx
# ASReview service proxy
location /asreview/ {
    proxy_pass http://asreview-gpu-host:5275/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    
    # Timeouts for long-running operations
    proxy_connect_timeout 10s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

### Step 4: Verify Setup

Restart HARVEST and check the Literature Review feature:

```bash
# Restart HARVEST
python3 launch_harvest.py

# Check ASReview connectivity
curl http://localhost:5001/api/literature-review/health
```

Expected response:
```json
{
  "ok": true,
  "available": true,
  "configured": true,
  "service_url": "http://asreview-gpu-host:5275",
  "version": "1.x.x",
  "status": "ok"
}
```

## Usage Guide

### 1. Start from Literature Search

The Literature Review feature integrates with the existing Literature Search:

1. Navigate to **Literature Search** tab
2. Search for papers using semantic search
3. Review and select papers of interest
4. Click **"Start Literature Review"** button

### 2. Create Review Project

When starting a literature review:

1. **Project Name**: Enter a descriptive name (e.g., "CRISPR Gene Editing Review 2024")
2. **Description**: Optional notes about review criteria
3. **ML Model**: Choose algorithm (Naive Bayes is default, recommended)
   - **Naive Bayes** (nb): Fast, works well with small training sets
   - **SVM** (svm): Powerful, requires more training data
   - **Random Forest** (rf): Robust, good for complex criteria
   - **Logistic Regression** (logistic): Interpretable, balanced performance

4. **Prior Knowledge** (optional):
   - Mark papers you already know are relevant
   - Mark papers you know are irrelevant
   - Helps bootstrap the ML model

5. Click **"Create Project"** to upload papers to ASReview

### 3. Screen Papers

ASReview presents papers in order of predicted relevance:

1. **Review paper details**:
   - Title
   - Authors
   - Abstract
   - Relevance score (0-100%)

2. **Make decision**:
   - ✅ **Relevant**: Paper meets your criteria
   - ❌ **Irrelevant**: Paper doesn't meet criteria
   - 📝 **Note** (optional): Document reason for decision

3. **Model learns**: After each decision, the ML model updates and re-ranks remaining papers

4. **Progress tracking**: See how many papers reviewed, estimated remaining

### 4. Complete Review

Stop screening when:
- **All papers reviewed**: Systematic completion
- **Diminishing returns**: Several consecutive irrelevant papers
- **Confidence threshold**: Remaining papers below relevance threshold

### 5. Export Results

Export relevant papers to:
- **HARVEST Project**: Create new annotation project
- **Download CSV**: Export for external tools
- **Copy DOIs**: Paste into other systems

## Review Criteria Examples

ASReview learns your criteria from examples. For HARVEST use cases:

### Example 1: Validation Studies

**Relevant papers have:**
- Experimental validation (in vivo/in vitro)
- Statistical analysis
- Replication studies
- Peer-reviewed

**Irrelevant papers:**
- Pure computational predictions
- Review articles
- Opinion pieces
- Preliminary conference abstracts

### Example 2: Entity Relationships

**Relevant papers describe:**
- Gene-phenotype relationships
- Protein-protein interactions
- Drug-target associations
- Pathway mechanisms

**Irrelevant papers:**
- General overviews
- Taxonomy papers
- Tool descriptions
- Unrelated organisms/systems

### Example 3: Stress Response Studies

**Relevant papers:**
- Environmental stress experiments
- Molecular stress responses
- Survival/reproduction measurements
- Stress biomarkers

**Irrelevant papers:**
- Clinical/medical stress (wrong domain)
- Psychological stress
- Engineering stress analysis

## API Reference

### Health Check

```http
GET /api/literature-review/health
```

Returns ASReview service status.

### Create Project

```http
POST /api/literature-review/projects
Content-Type: application/json

{
  "project_name": "My Review",
  "description": "Optional description",
  "model_type": "nb"
}
```

### Upload Papers

```http
POST /api/literature-review/projects/{project_id}/upload
Content-Type: application/json

{
  "papers": [
    {
      "title": "Paper Title",
      "abstract": "Abstract text",
      "authors": ["Author 1", "Author 2"],
      "doi": "10.1234/example",
      "year": 2024
    }
  ]
}
```

### Start Review

```http
POST /api/literature-review/projects/{project_id}/start
Content-Type: application/json

{
  "prior_relevant": ["10.1234/relevant"],
  "prior_irrelevant": ["10.5678/irrelevant"]
}
```

### Get Next Paper

```http
GET /api/literature-review/projects/{project_id}/next
```

Returns next paper to screen.

### Record Decision

```http
POST /api/literature-review/projects/{project_id}/record
Content-Type: application/json

{
  "paper_id": "10.1234/example",
  "relevant": true,
  "note": "Has experimental validation"
}
```

### Get Progress

```http
GET /api/literature-review/projects/{project_id}/progress
```

Returns review statistics.

### Export Results

```http
GET /api/literature-review/projects/{project_id}/export
```

Returns list of relevant papers.

## Troubleshooting

### Service Not Available

**Symptom**: "ASReview service not configured" error

**Solutions**:
1. Check `ASREVIEW_SERVICE_URL` in config.py
2. Verify ASReview service is running
3. Test connectivity: `curl http://asreview-host:5275/api/health`
4. Check firewall rules allow connections

### Connection Timeout

**Symptom**: Request timeout errors

**Solutions**:
1. Increase `ASREVIEW_REQUEST_TIMEOUT` in config.py
2. Check network latency between HARVEST and ASReview
3. Verify ASReview service has adequate resources
4. Check nginx proxy timeout settings

### Slow Performance

**Symptom**: Slow paper screening, long waits

**Solutions**:
1. Ensure ASReview service has GPU access
2. Check GPU utilization: `nvidia-smi`
3. Reduce concurrent reviews
4. Upgrade to faster GPU
5. Consider lighter ML model (nb instead of rf/svm)

### Model Not Learning

**Symptom**: Poor relevance predictions, random ordering

**Solutions**:
1. Provide more prior knowledge examples (5-10 relevant, 5-10 irrelevant)
2. Be consistent in decision criteria
3. Try different ML model type
4. Ensure sufficient training data (>20 decisions)

## Security Considerations

### Authentication

- Literature Review requires admin authentication
- All API endpoints check admin status
- Session-based authentication via cookies

### Network Security

- ASReview service should be on trusted network
- Use HTTPS for production deployments
- Configure firewall to restrict ASReview access
- Consider VPN for remote ASReview service

### Data Privacy

- Papers uploaded to ASReview service
- Service may store metadata temporarily
- Configure ASReview data retention policies
- Use organization-controlled ASReview instance

## Best Practices

### Project Organization

1. **One review per topic**: Keep reviews focused
2. **Meaningful names**: Use descriptive project names
3. **Document criteria**: Note inclusion/exclusion criteria in description
4. **Export regularly**: Save results incrementally

### Screening Strategy

1. **Start with 10-20 decisions**: Train model with diverse examples
2. **Be consistent**: Apply same criteria throughout
3. **Add notes**: Document decision rationale
4. **Review in sessions**: Avoid decision fatigue
5. **Trust the model**: Papers are prioritized intelligently

### Quality Control

1. **Double-check borderline papers**: Review low-confidence decisions
2. **Sample irrelevant papers**: Periodically verify excluded papers
3. **Track agreement**: Monitor consistency over time
4. **Export for validation**: Have second reviewer check results

## Performance Tuning

### GPU Configuration

For optimal ASReview performance:

```bash
# Check GPU availability
nvidia-smi

# Set GPU memory growth (TensorFlow)
export TF_FORCE_GPU_ALLOW_GROWTH=true

# Limit GPU memory (if shared)
export CUDA_VISIBLE_DEVICES=0
```

### Model Selection Guide

| Model Type | Speed | Accuracy | Data Needed | Best For |
|------------|-------|----------|-------------|----------|
| Naive Bayes | ⚡⚡⚡ | ⭐⭐ | Low | Quick reviews, small datasets |
| Logistic | ⚡⚡ | ⭐⭐⭐ | Medium | Balanced performance |
| SVM | ⚡ | ⭐⭐⭐ | High | Complex criteria, large datasets |
| Random Forest | ⚡⚡ | ⭐⭐⭐⭐ | High | Best accuracy, slower |

### Batch Operations

For large reviews (>1000 papers):

1. Upload in batches of 500 papers
2. Screen in sessions of 50-100 decisions
3. Export results periodically
4. Monitor memory usage on ASReview host

## Integration with HARVEST Workflow

### Complete Workflow

1. **Search** → Literature Search tab
   - Query multiple sources
   - Gather initial candidate papers

2. **Review** → Literature Review feature
   - Upload papers to ASReview
   - AI-assisted screening
   - Shortlist relevant papers

3. **Annotate** → Annotate tab
   - Extract entity relationships
   - Add triples for relevant papers
   - Build knowledge base

4. **Analyze** → Browse tab
   - Query annotations
   - Visualize relationships
   - Export data

### Project Management

Link Literature Review with HARVEST Projects:

1. Create HARVEST project from Literature Search
2. Start Literature Review for same papers
3. Export relevant papers from review
4. Focus annotation efforts on reviewed papers

## Advanced Features

### Custom Model Configuration

For advanced users, ASReview can be configured with:

- Custom feature extraction
- Ensemble models
- Transfer learning from previous reviews
- Domain-specific embeddings

See [ASReview documentation](https://asreview.readthedocs.io) for details.

### Programmatic Access

Use ASReview client directly in Python:

```python
from asreview_client import get_asreview_client

client = get_asreview_client()

# Create project
result = client.create_project("My Review")
project_id = result['project_id']

# Upload papers
papers = [...]  # From literature search
client.upload_papers(project_id, papers)

# Start review
client.start_review(project_id)

# Screen papers
while True:
    result = client.get_next_paper(project_id)
    if result['paper'] is None:
        break
    
    paper = result['paper']
    # Make decision (relevant = True/False)
    relevant = decide_relevance(paper)
    client.record_decision(project_id, paper['doi'], relevant)

# Export results
results = client.export_results(project_id)
relevant_papers = results['relevant_papers']
```

## Deployment Architectures

### Single Server Setup

For small teams or testing:

```
┌─────────────────────────────────┐
│  Same Host                      │
│                                 │
│  ┌──────────┐  ┌────────────┐  │
│  │ HARVEST  │  │ ASReview   │  │
│  │ :8050    │  │ :5275      │  │
│  └──────────┘  └────────────┘  │
│                                 │
└─────────────────────────────────┘
```

### Multi-Server Setup

For production with GPU:

```
┌──────────────┐         ┌──────────────────┐
│ HARVEST      │         │ GPU Server       │
│ Server       │  HTTP   │                  │
│              │────────▶│ ASReview Service │
│ Web + API    │         │ :5275            │
└──────────────┘         └──────────────────┘
```

### Nginx Proxy Setup

For enterprise deployments:

```
                ┌─────────────────┐
                │  Nginx Proxy    │
                │  :443 (HTTPS)   │
                └────────┬────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────┐            ┌─────────────────┐
│ HARVEST         │            │ ASReview        │
│ /harvest/*      │            │ /asreview/*     │
│ :8050           │            │ :5275           │
└─────────────────┘            └─────────────────┘
```

## Future Enhancements

Planned features:

- [ ] **Collaborative reviews**: Multiple reviewers with conflict resolution
- [ ] **Review templates**: Pre-configured criteria for common review types
- [ ] **Citation network**: Visualize paper relationships
- [ ] **Automated exports**: Schedule exports to HARVEST projects
- [ ] **Progress dashboards**: Visualize review progress over time
- [ ] **Quality metrics**: Inter-rater reliability, decision confidence

## Support and Resources

### Documentation

- HARVEST README: `/README.md`
- ASReview Documentation: https://asreview.readthedocs.io
- ASReview GitHub: https://github.com/asreview/asreview

### Getting Help

1. Check this documentation
2. Review ASReview tutorials: https://asreview.ai/tutorials
3. Open GitHub issue for HARVEST integration problems
4. Contact ASReview community for ASReview-specific questions

### Citation

If you use this feature in research, please cite:

**HARVEST**: *(Add HARVEST citation here)*

**ASReview**:
```
van de Schoot, R., de Bruin, J., Schram, R., Zahedi, P., de Boer, J., Weijdema, F., ...
& Oberski, D. L. (2021). ASReview: Open Source Software for Efficient and Transparent
Active Learning for Systematic Reviews. Nature Machine Intelligence, 3(2), 125–133.
https://doi.org/10.1038/s42256-020-00287-7
```

## License

ASReview is licensed under Apache License 2.0. See ASReview project for details.
