# Literature Review - Quick Deployment Guide

This guide provides quick setup instructions for deploying the Literature Review feature with ASReview integration.

## Quick Setup (5 Minutes)

### Step 1: Deploy ASReview Service

**Option A: Docker (Easiest)**

```bash
# On GPU-enabled server
docker run -d \
  --name asreview \
  --gpus all \
  -p 5275:5275 \
  -v asreview-data:/data \
  --restart unless-stopped \
  asreview/asreview:latest \
  asreview lab --host 0.0.0.0 --port 5275
```

**Option B: Python (Alternative)**

```bash
# On GPU-enabled server
pip install asreview[all]
asreview lab --host 0.0.0.0 --port 5275 &
```

### Step 2: Configure HARVEST

Edit `config.py`:

```python
# Enable Literature Review feature
ENABLE_LITERATURE_REVIEW = True

# Configure ASReview service URL
ASREVIEW_SERVICE_URL = "http://your-gpu-server:5275"
```

Replace `your-gpu-server` with:
- IP address: `http://192.168.1.100:5275`
- Hostname: `http://gpu-server.local:5275`
- Same host: `http://localhost:5275`

### Step 3: Restart HARVEST

```bash
# Kill existing processes
pkill -f harvest_be.py
pkill -f harvest_fe.py

# Start HARVEST
python3 launch_harvest.py
```

### Step 4: Verify

```bash
# Check ASReview connectivity
curl http://localhost:5001/api/literature-review/health
```

Expected output:
```json
{
  "ok": true,
  "available": true,
  "configured": true,
  "version": "1.x.x"
}
```

## Usage (2 Minutes)

### 1. Search for Papers

1. Login to HARVEST admin panel
2. Go to **Literature Search** tab
3. Search for papers: e.g., "CRISPR gene editing"
4. Review results

### 2. Start Literature Review

1. Click **"Start Literature Review"** button
2. Enter project name: "CRISPR Review 2024"
3. Select ML model: "Naive Bayes" (default)
4. Click **"Create Project"**

### 3. Screen Papers

1. Review paper presented (title, abstract, authors)
2. Mark as:
   - ✅ **Relevant**: Meets your criteria
   - ❌ **Irrelevant**: Doesn't meet criteria
3. Repeat for next paper (shown in order of predicted relevance)
4. Stop when satisfied or all papers screened

### 4. Export Results

1. Click **"Export Results"**
2. Select export format:
   - Create new HARVEST project
   - Download CSV
   - Copy DOIs to clipboard
3. Use relevant papers for annotation

## Troubleshooting

### "Service not configured" Error

**Problem**: `ASREVIEW_SERVICE_URL` not set

**Solution**:
```bash
# Edit config.py
nano config.py

# Add/update line:
ASREVIEW_SERVICE_URL = "http://gpu-server:5275"

# Restart HARVEST
python3 launch_harvest.py
```

### "Connection refused" Error

**Problem**: Cannot reach ASReview service

**Solutions**:
1. Check ASReview is running:
   ```bash
   curl http://gpu-server:5275/api/health
   ```

2. Check firewall allows port 5275:
   ```bash
   sudo ufw allow 5275/tcp
   ```

3. Verify network connectivity:
   ```bash
   ping gpu-server
   telnet gpu-server 5275
   ```

### "Service unavailable" Error

**Problem**: ASReview service not responding

**Solutions**:
1. Restart ASReview:
   ```bash
   docker restart asreview
   # or
   pkill -f asreview
   asreview lab --host 0.0.0.0 --port 5275 &
   ```

2. Check ASReview logs:
   ```bash
   docker logs asreview
   ```

3. Increase timeout in config.py:
   ```python
   ASREVIEW_REQUEST_TIMEOUT = 600  # 10 minutes
   ```

## Nginx Configuration (Optional)

If using nginx proxy:

```nginx
# Add to nginx.conf
location /asreview/ {
    proxy_pass http://gpu-server:5275/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
    proxy_connect_timeout 10s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

Then configure HARVEST:
```python
ASREVIEW_SERVICE_URL = "https://yourdomain.com/asreview"
```

## Performance Tips

### GPU Acceleration

Ensure ASReview uses GPU:

```bash
# Check GPU available
nvidia-smi

# Run ASReview with GPU
docker run --gpus all ...
```

### Model Selection

- **Naive Bayes**: Fastest, good for <1000 papers
- **Logistic Regression**: Balanced, good for most cases
- **Random Forest**: Most accurate, slower
- **SVM**: Best for complex criteria, needs more training

### Batch Size

For large reviews:
- Upload papers in batches of 500
- Screen in sessions of 50-100
- Export results regularly

## Next Steps

- Read full documentation: [LITERATURE_REVIEW.md](LITERATURE_REVIEW.md)
- Learn ASReview: https://asreview.ai/tutorials
- Configure advanced features: GPU optimization, custom models
- Integrate with HARVEST projects and annotation workflow

## Support

- HARVEST issues: Open GitHub issue
- ASReview documentation: https://asreview.readthedocs.io
- ASReview community: https://github.com/asreview/asreview/discussions
