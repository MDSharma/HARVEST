# Deployment Quick Reference

Quick reference guide for deploying the T2T Training Application.

## Mode Selection

| Mode | When to Use | Complexity |
|------|-------------|------------|
| **Internal** | Development, single server, simple setup | Low |
| **Nginx** | Production, SSL, load balancing, scaling | Medium |

## Quick Start

### Internal Mode (Default)

```bash
# No configuration needed - just run
python3 launch_harvest.py
```

Access at `http://localhost:8050`

### Nginx Mode

**1. Configure:**
```python
# config.py
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://api.yourdomain.com"
HOST = "0.0.0.0"
```

**2. Setup nginx:**
```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/harvest
sudo nano /etc/nginx/sites-available/harvest  # Edit as needed
sudo ln -s /etc/nginx/sites-available/harvest /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**3. Run:**
```bash
python3 launch_harvest.py
```

## Configuration Options

### Required Settings

| Setting | Internal Mode | Nginx Mode |
|---------|---------------|------------|
| `DEPLOYMENT_MODE` | `"internal"` | `"nginx"` |
| `BACKEND_PUBLIC_URL` | Not used | **Required** |
| `HOST` | `"127.0.0.1"` | `"0.0.0.0"` |

### Environment Variables

```bash
# Override deployment mode
export HARVEST_DEPLOYMENT_MODE="nginx"

# Set backend public URL
export HARVEST_BACKEND_PUBLIC_URL="https://api.yourdomain.com"

# Backend host binding
export HARVEST_HOST="0.0.0.0"
```

## How It Works

### Internal Mode
```
Browser → Frontend :8050 → /proxy/* → Backend :5001 (localhost)
```

### Nginx Mode
```
Browser → Nginx :443 → Frontend :8050
                    └→ Backend :5001
```

## Common Configurations

### 1. Development (Internal)
```python
DEPLOYMENT_MODE = "internal"
HOST = "127.0.0.1"
```

### 2. Production Same-Server (Nginx)
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
HOST = "0.0.0.0"
```

### 3. Separate API Subdomain (Nginx)
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://api.yourdomain.com"
HOST = "0.0.0.0"
```

### 4. Docker with Nginx
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "http://nginx/api"
HOST = "0.0.0.0"
```

## Validation

The launcher validates your configuration:

```bash
python3 launch_harvest.py

# Output shows:
# - Deployment mode
# - Backend public URL (if nginx mode)
# - Warnings for misconfigurations
```

## Troubleshooting

### Configuration Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Invalid DEPLOYMENT_MODE | Wrong value | Set to "internal" or "nginx" |
| BACKEND_PUBLIC_URL must be set | Missing in nginx mode | Add URL in config.py |
| Port already in use | Service running | Stop existing service |

### Runtime Issues

| Issue | Mode | Solution |
|-------|------|----------|
| 502 Bad Gateway | Nginx | Check backend is running and accessible |
| CORS errors | Both | Verify deployment mode and restart services |
| PDF not loading | Both | Check browser console, verify URLs |
| Proxy 404 errors | Nginx | Expected - frontend uses direct URLs |

## Security Checklist

### Internal Mode
- [ ] Backend on 127.0.0.1
- [ ] Only frontend port exposed
- [ ] Firewall configured

### Nginx Mode
- [ ] SSL/TLS enabled
- [ ] Backend not directly accessible
- [ ] Rate limiting configured
- [ ] Firewall rules set
- [ ] Strong admin passwords
- [ ] Regular updates

## Files to Reference

- **DEPLOYMENT.md** - Comprehensive guide with examples
- **nginx.conf.example** - Nginx configuration template
- **INSTALLATION.md** - Installation and troubleshooting
- **README.md** - General information

## Support Commands

```bash
# Test configuration
python3 -c "from config import DEPLOYMENT_MODE, BACKEND_PUBLIC_URL; print(DEPLOYMENT_MODE)"

# Check backend health
curl http://localhost:5001/api/health

# Test nginx config
sudo nginx -t

# View nginx logs
sudo tail -f /var/log/nginx/error.log

# View application logs
python3 launch_harvest.py  # Logs to console
```

## Migration

### Internal → Nginx
1. Set `DEPLOYMENT_MODE = "nginx"`
2. Set `BACKEND_PUBLIC_URL`
3. Change `HOST = "0.0.0.0"`
4. Configure nginx
5. Restart application

### Nginx → Internal
1. Set `DEPLOYMENT_MODE = "internal"`
2. Change `HOST = "127.0.0.1"`
3. Restart application
4. Nginx no longer needed

## Performance Tips

### Internal Mode
- Single server performance
- Suitable for moderate load
- Consider nginx for scaling

### Nginx Mode
- Enable caching in nginx
- Use HTTP/2
- Implement rate limiting
- Consider multiple backend instances
- Use connection pooling

## Need More Help?

1. Check **DEPLOYMENT.md** for detailed examples
2. Review **nginx.conf.example** for configuration
3. Look at **INSTALLATION.md** troubleshooting section
4. Verify configuration with validation warnings
5. Check application and nginx logs

---

**Remember**: Default is internal mode - safe to start without configuration changes!
