# Literature Review Feature - Deployment Checklist

This checklist helps deploy the Literature Review feature to production.

## Pre-Deployment Checklist

### ☐ 1. ASReview Service Setup

**Choose deployment method:**
- [ ] Docker (recommended for production)
- [ ] Python virtual environment
- [ ] Systemd service

**GPU Host Requirements:**
- [ ] NVIDIA GPU available (check with `nvidia-smi`)
- [ ] Docker installed (if using Docker)
- [ ] Python 3.8+ (if using Python install)
- [ ] Network connectivity to HARVEST

**Deploy ASReview:**

```bash
# Option A: Docker
docker run -d \
  --name asreview \
  --gpus all \
  -p 5275:5275 \
  -v asreview-data:/data \
  --restart unless-stopped \
  asreview/asreview:latest \
  asreview lab --host 0.0.0.0 --port 5275

# Option B: Python
pip install asreview[all]
asreview lab --host 0.0.0.0 --port 5275 &
```

**Verify service:**
```bash
curl http://gpu-server:5275/api/health
# Should return: {"version": "...", "status": "ok"}
```

### ☐ 2. Network Configuration

**Firewall rules:**
- [ ] Allow port 5275 on GPU server
- [ ] Allow HARVEST → ASReview connectivity

```bash
# On GPU server
sudo ufw allow 5275/tcp
sudo ufw status
```

**Test connectivity:**
```bash
# From HARVEST server
telnet gpu-server 5275
curl http://gpu-server:5275/api/health
```

### ☐ 3. HARVEST Configuration

**Edit config.py:**
```python
# Enable feature
ENABLE_LITERATURE_REVIEW = True

# Configure service URL
ASREVIEW_SERVICE_URL = "http://gpu-server:5275"

# Optional: API key
ASREVIEW_API_KEY = ""

# Timeouts
ASREVIEW_REQUEST_TIMEOUT = 300
ASREVIEW_CONNECTION_TIMEOUT = 10
```

**Or use environment variables:**
```bash
export ASREVIEW_SERVICE_URL="http://gpu-server:5275"
export ASREVIEW_API_KEY=""
```

### ☐ 4. Nginx Configuration (if using nginx mode)

**Add to nginx.conf:**
```nginx
# ASReview service proxy
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

**Test nginx config:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Update HARVEST config:**
```python
ASREVIEW_SERVICE_URL = "https://yourdomain.com/asreview"
```

### ☐ 5. Testing

**Test ASReview health:**
```bash
curl http://localhost:5001/api/literature-review/health
```

Expected response:
```json
{
  "ok": true,
  "available": true,
  "configured": true,
  "service_url": "http://gpu-server:5275",
  "version": "1.x.x",
  "status": "ok"
}
```

**Run integration tests (optional):**
```bash
# Start mock service
python3 asreview_mock_service.py &

# Run tests
python3 test_literature_review_integration.py
```

### ☐ 6. Restart HARVEST

```bash
# Kill existing processes
pkill -f harvest_be.py
pkill -f harvest_fe.py

# Start HARVEST
python3 launch_harvest.py

# Or if using systemd
sudo systemctl restart harvest
```

### ☐ 7. Verify Deployment

**Check logs:**
```bash
# HARVEST logs
tail -f harvest.log

# ASReview logs (Docker)
docker logs -f asreview

# ASReview logs (systemd)
sudo journalctl -u asreview -f
```

**Test workflow:**
1. Login to HARVEST as admin
2. Go to Literature Search tab
3. Search for papers
4. Click "Start Literature Review" (if frontend implemented)
5. Or use API directly:

```bash
# Test API endpoint
curl -X GET \
  http://localhost:5001/api/literature-review/health \
  -H 'Cookie: session=...'
```

## Post-Deployment Checklist

### ☐ 8. Monitoring

**Setup monitoring:**
- [ ] ASReview service uptime
- [ ] GPU utilization
- [ ] API response times
- [ ] Error rates

**Monitor ASReview:**
```bash
# Check service status
curl http://gpu-server:5275/api/health

# Check GPU usage
nvidia-smi

# Check Docker stats
docker stats asreview
```

### ☐ 9. Documentation

**Update internal docs:**
- [ ] Document ASReview service URL
- [ ] Document admin procedures
- [ ] Create runbook for common issues
- [ ] Train users on new feature

### ☐ 10. Backup and Recovery

**Backup procedures:**
- [ ] ASReview data directory (`/data` in Docker)
- [ ] HARVEST database (includes project metadata)
- [ ] Configuration files

```bash
# Backup ASReview data
docker cp asreview:/data /backup/asreview-data-$(date +%Y%m%d)

# Backup HARVEST config
cp config.py /backup/config.py.$(date +%Y%m%d)
```

## Troubleshooting Guide

### Issue: "Service not configured"

**Symptoms:**
- Error in UI: "ASReview service not configured"
- Health check returns: `"configured": false`

**Solutions:**
1. Check `ASREVIEW_SERVICE_URL` in config.py
2. Restart HARVEST to load new config
3. Verify environment variables not overriding config

### Issue: "Connection refused"

**Symptoms:**
- Error: "Cannot connect to ASReview service"
- Timeout on health check

**Solutions:**
1. Verify ASReview service is running:
   ```bash
   curl http://gpu-server:5275/api/health
   ```

2. Check firewall rules:
   ```bash
   sudo ufw status
   telnet gpu-server 5275
   ```

3. Check service logs:
   ```bash
   docker logs asreview
   ```

### Issue: "Service unavailable"

**Symptoms:**
- Service responds but returns errors
- Slow response times

**Solutions:**
1. Check GPU availability:
   ```bash
   nvidia-smi
   ```

2. Check resource usage:
   ```bash
   docker stats asreview
   ```

3. Restart ASReview:
   ```bash
   docker restart asreview
   ```

4. Check disk space:
   ```bash
   df -h
   ```

### Issue: "Authentication failed"

**Symptoms:**
- "Unauthorized" errors
- Admin check fails

**Solutions:**
1. Verify admin user in HARVEST:
   ```bash
   python3 create_admin.py
   ```

2. Check session cookies are set
3. Verify admin email in config

## Rollback Procedure

If deployment fails:

### 1. Disable Feature

```python
# In config.py
ENABLE_LITERATURE_REVIEW = False
```

### 2. Restart HARVEST

```bash
pkill -f harvest_be.py
pkill -f harvest_fe.py
python3 launch_harvest.py
```

### 3. Stop ASReview Service

```bash
docker stop asreview
# or
pkill -f asreview
```

### 4. Restore Config

```bash
cp /backup/config.py.YYYYMMDD config.py
```

## Upgrade Procedure

When upgrading ASReview version:

### 1. Backup Data

```bash
docker cp asreview:/data /backup/asreview-data-upgrade
```

### 2. Stop Service

```bash
docker stop asreview
docker rm asreview
```

### 3. Pull New Image

```bash
docker pull asreview/asreview:latest
```

### 4. Start New Version

```bash
docker run -d \
  --name asreview \
  --gpus all \
  -p 5275:5275 \
  -v asreview-data:/data \
  --restart unless-stopped \
  asreview/asreview:latest \
  asreview lab --host 0.0.0.0 --port 5275
```

### 5. Verify

```bash
curl http://gpu-server:5275/api/health
```

## Security Checklist

### ☐ Network Security

- [ ] ASReview service not exposed to public internet
- [ ] Firewall rules restrict access to HARVEST only
- [ ] Use VPN for remote ASReview service
- [ ] HTTPS enabled for production (nginx)

### ☐ Authentication

- [ ] Admin authentication required
- [ ] Session management working correctly
- [ ] API key configured (if needed)

### ☐ Data Privacy

- [ ] ASReview service organization-controlled
- [ ] Data retention policy configured
- [ ] Backup encryption enabled
- [ ] Access logs enabled

## Performance Optimization

### ☐ GPU Configuration

```bash
# Check GPU memory
nvidia-smi --query-gpu=memory.used,memory.free --format=csv

# Limit GPU memory (if needed)
docker run ... -e TF_FORCE_GPU_ALLOW_GROWTH=true ...
```

### ☐ Resource Limits

```bash
# Docker resource limits
docker run ... \
  --memory=8g \
  --cpus=4 \
  ...
```

### ☐ Monitoring

- [ ] Setup Prometheus/Grafana for metrics
- [ ] Monitor GPU utilization
- [ ] Track API response times
- [ ] Alert on errors

## Completion

- [ ] All pre-deployment steps completed
- [ ] Service deployed and verified
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Team trained
- [ ] Backup procedures in place
- [ ] Rollback procedure tested

**Deployment Date:** _______________

**Deployed By:** _______________

**Service URL:** _______________

**Notes:**
```
______________________________________________________________
______________________________________________________________
______________________________________________________________
```

## Support Contacts

- **HARVEST Support:** _______________
- **ASReview Documentation:** https://asreview.readthedocs.io
- **IT Support:** _______________
- **GPU Server Admin:** _______________
