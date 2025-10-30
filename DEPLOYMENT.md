# Deployment Guide

This guide explains how to deploy the T2T Training Application in different environments using the flexible deployment configuration system.

## Table of Contents

- [Deployment Modes](#deployment-modes)
- [Internal Mode (Default)](#internal-mode-default)
- [Nginx Mode](#nginx-mode)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Deployment Modes

The application supports two deployment modes, configurable via `config.py` or environment variables:

### 1. Internal Mode (Default)

**Best for:**
- Development environments
- Single-server deployments
- Simplified setup without reverse proxy

**How it works:**
- Frontend proxies all backend requests through `/proxy/*` routes
- Backend runs on `127.0.0.1` (localhost only)
- Backend is not directly accessible from external clients
- All communication stays on localhost

**Security:**
- Backend is protected from direct external access
- Only the frontend is exposed to users
- Simpler security configuration

### 2. Nginx Mode

**Best for:**
- Production deployments
- Multiple application instances
- Load balancing scenarios
- SSL/TLS termination
- Advanced routing requirements

**How it works:**
- Frontend makes direct requests to backend API
- Backend must be accessible at `BACKEND_PUBLIC_URL`
- Reverse proxy (nginx, Apache, etc.) handles routing
- Supports distributed deployments

**Security:**
- Requires proper firewall rules
- Backend should be protected by reverse proxy
- SSL/TLS recommended
- Rate limiting can be implemented at proxy level

## Internal Mode (Default)

### Configuration

In `config.py`:

```python
DEPLOYMENT_MODE = "internal"  # Default
BACKEND_PUBLIC_URL = ""  # Not used in internal mode
HOST = "127.0.0.1"  # Backend binds to localhost only
```

### Starting the Application

```bash
# Using the launcher (recommended)
python3 launch_harvest.py

# Or manually
python3 harvest_be.py  # Terminal 1
python3 harvest_fe.py  # Terminal 2
```

Access the application at `http://localhost:8050`

### How Requests Flow

```
Client Browser
    ↓
Frontend (Dash) :8050
    ↓ (internal /proxy/ routes)
Backend (Flask) :5001 (localhost only)
```

### Advantages

- Simple setup, no reverse proxy needed
- Backend automatically protected from external access
- Ideal for development and testing
- Works out of the box

### Limitations

- Single server deployment only
- No load balancing
- No SSL termination at application level
- Harder to scale horizontally

## Nginx Mode

### Configuration

In `config.py`:

```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://api.yourdomain.com"  # Required
HOST = "0.0.0.0"  # Backend binds to all interfaces
```

Or use environment variables:

```bash
export HARVEST_DEPLOYMENT_MODE="nginx"
export HARVEST_BACKEND_PUBLIC_URL="https://api.yourdomain.com"
export HARVEST_HOST="0.0.0.0"
```

### Nginx Setup

1. **Copy the example configuration:**

```bash
sudo cp nginx.conf.example /etc/nginx/sites-available/harvest
```

2. **Edit the configuration:**

```bash
sudo nano /etc/nginx/sites-available/harvest
```

Update:
- `server_name` to your domain
- Upstream server addresses if needed
- SSL certificate paths (for HTTPS)

3. **Enable the site:**

```bash
sudo ln -s /etc/nginx/sites-available/harvest /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

4. **Start the application:**

```bash
python3 launch_harvest.py
```

### How Requests Flow

```
Client Browser
    ↓ (HTTPS)
Nginx :443
    ├─→ Frontend (Dash) :8050
    └─→ Backend (Flask) :5001
```

### Advantages

- Production-ready deployment
- SSL/TLS termination at nginx
- Load balancing support
- Rate limiting and caching
- Multiple instances possible
- Better performance under load

### Limitations

- More complex setup
- Requires reverse proxy knowledge
- More configuration to maintain

## Configuration

### Configuration File (config.py)

```python
# Deployment Mode Configuration
DEPLOYMENT_MODE = "internal"  # or "nginx"

# Backend Public URL (nginx mode only)
BACKEND_PUBLIC_URL = ""  # Example: "https://api.yourdomain.com"

# Server Configuration
HOST = "127.0.0.1"  # Use "0.0.0.0" for nginx mode
PORT = 8050  # Frontend port
BE_PORT = 5001  # Backend port
```

### Environment Variables

Override configuration at runtime:

```bash
# Set database path
export HARVEST_DB="/path/to/database.db"

# Set deployment mode
export HARVEST_DEPLOYMENT_MODE="nginx"

# Set backend public URL
export HARVEST_BACKEND_PUBLIC_URL="https://api.yourdomain.com"

# Backend host binding
export HARVEST_HOST="0.0.0.0"

# Ports
export HARVEST_PORT="5001"  # Backend
export PORT="8050"  # Frontend
```

**Note:** The database directory will be automatically created if it doesn't exist.

### Validation

The launcher script validates your configuration:

```bash
python3 launch_harvest.py
```

It will:
- Check that `DEPLOYMENT_MODE` is valid
- Verify `BACKEND_PUBLIC_URL` is set for nginx mode
- Warn about potential misconfigurations
- Display deployment mode on startup

## Examples

### Example 1: Development Setup (Internal Mode)

**config.py:**
```python
DEPLOYMENT_MODE = "internal"
HOST = "127.0.0.1"
PORT = 8050
BE_PORT = 5001
```

**Run:**
```bash
python3 launch_harvest.py
```

**Access:**
`http://localhost:8050`

---

### Example 2: Production with Nginx (Same Server)

**config.py:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
HOST = "0.0.0.0"
PORT = 8050
BE_PORT = 5001
```

**nginx.conf:**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8050;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
    }
}
```

**Run:**
```bash
python3 launch_harvest.py
```

**Access:**
`https://yourdomain.com`

---

### Example 3: Separate API Subdomain

**config.py:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://api.yourdomain.com"
HOST = "0.0.0.0"
```

**nginx.conf:**
```nginx
# Frontend
server {
    listen 443 ssl;
    server_name yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:8050;
    }
}

# Backend
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:5001;
    }
}
```

---

### Example 4: Load Balanced Backend

**config.py:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
```

**nginx.conf:**
```nginx
upstream harvest_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    location /api/ {
        proxy_pass http://harvest_backend;
    }
}
```

**Run multiple backend instances:**
```bash
HARVEST_PORT=5001 python3 harvest_be.py &
HARVEST_PORT=5002 python3 harvest_be.py &
HARVEST_PORT=5003 python3 harvest_be.py &
python3 harvest_fe.py
```

---

### Example 5: Docker with Environment Variables

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  backend:
    build: .
    command: python3 harvest_be.py
    environment:
      - HARVEST_DEPLOYMENT_MODE=nginx
      - HARVEST_HOST=0.0.0.0
      - HARVEST_PORT=5001
    ports:
      - "5001:5001"

  frontend:
    build: .
    command: python3 harvest_fe.py
    environment:
      - HARVEST_DEPLOYMENT_MODE=nginx
      - HARVEST_BACKEND_PUBLIC_URL=http://nginx/api
      - PORT=8050
    ports:
      - "8050:8050"

  nginx:
    image: nginx:latest
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    ports:
      - "80:80"
    depends_on:
      - backend
      - frontend
```

## Troubleshooting

### Error: "Invalid DEPLOYMENT_MODE"

**Cause:** `DEPLOYMENT_MODE` is not set to "internal" or "nginx"

**Solution:**
```python
# In config.py
DEPLOYMENT_MODE = "internal"  # or "nginx"
```

---

### Error: "BACKEND_PUBLIC_URL must be set when DEPLOYMENT_MODE is 'nginx'"

**Cause:** Nginx mode requires `BACKEND_PUBLIC_URL` to be configured

**Solution:**
```python
# In config.py
BACKEND_PUBLIC_URL = "https://api.yourdomain.com"
```

---

### Warning: "Backend is configured to run on localhost in nginx mode"

**Cause:** Backend is binding to `127.0.0.1` but nginx mode expects external accessibility

**Solution:**
```python
# In config.py
HOST = "0.0.0.0"  # Bind to all interfaces
```

Or ensure your reverse proxy can reach `127.0.0.1:5001` on the same machine.

---

### 502 Bad Gateway Errors

**Cause:** Nginx cannot reach backend

**Check:**
1. Backend is running: `curl http://localhost:5001/api/health`
2. Nginx configuration is correct
3. Firewall allows connections
4. `BACKEND_PUBLIC_URL` matches nginx routing

---

### CORS Errors in Nginx Mode

**Cause:** Frontend cannot access backend due to CORS restrictions

**Solution:** The application automatically configures CORS for nginx mode. Ensure:
1. `DEPLOYMENT_MODE = "nginx"` is set
2. Backend was restarted after changing config
3. Check backend logs for CORS configuration message

---

### PDF Viewer Not Loading

**Cause:** Wrong deployment mode or proxy configuration

**Check:**
1. Deployment mode is correctly set
2. PDF URLs are being generated correctly (check browser console)
3. In internal mode, proxy routes should work
4. In nginx mode, direct backend URLs should work

---

### Rate Limiting in Nginx

If you see 429 (Too Many Requests) errors, adjust nginx rate limiting:

```nginx
# In nginx.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=20r/s;

location /api/ {
    limit_req zone=api_limit burst=40 nodelay;
    # ... other settings
}
```

## Security Considerations

### Internal Mode

- Backend is automatically protected (localhost only)
- Only frontend port needs to be exposed
- Suitable for trusted networks

### Nginx Mode

- Backend should not be directly accessible from internet
- Use firewall rules to restrict backend access
- SSL/TLS strongly recommended
- Implement rate limiting at nginx level
- Use fail2ban or similar for brute force protection
- Keep nginx and application updated

## Running as a Systemd Service

For production deployments, you can run HARVEST as a systemd service. This allows automatic startup on boot and easier management.

### Backend Service

Create `/etc/systemd/system/harvest-backend.service`:

```ini
[Unit]
Description=HARVEST Backend API Service
After=network.target
Requires=network.target

[Service]
Type=simple
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest

# Environment variables - all settings can be configured via environment
Environment="HARVEST_DB=/opt/harvest/data/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://yourdomain.com/api"
Environment="HARVEST_HOST=127.0.0.1"
Environment="HARVEST_PORT=5001"

# Use the virtual environment
ExecStart=/opt/harvest/venv/bin/python3 /opt/harvest/harvest_be.py

# Restart on failure
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=harvest-backend

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/harvest/data
ReadWritePaths=/opt/harvest/project_pdfs
ReadWritePaths=/opt/harvest/assets

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### Frontend Service

Create `/etc/systemd/system/harvest-frontend.service`:

```ini
[Unit]
Description=HARVEST Frontend Service
After=network.target harvest-backend.service
Requires=network.target
Wants=harvest-backend.service

[Service]
Type=simple
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest

# Environment variables
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://yourdomain.com/api"
Environment="HARVEST_API_BASE=http://127.0.0.1:5001"
Environment="PORT=8050"

# Use the virtual environment
ExecStart=/opt/harvest/venv/bin/python3 /opt/harvest/harvest_fe.py

# Restart on failure
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=harvest-frontend

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### Enable and Start Services

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable harvest-backend harvest-frontend

# Start services
sudo systemctl start harvest-backend harvest-frontend

# Check status
sudo systemctl status harvest-backend harvest-frontend

# View logs
sudo journalctl -u harvest-backend -f
sudo journalctl -u harvest-frontend -f
```

**Note:** The database directory (`/opt/harvest/data` in this example) will be automatically created by the backend service if it doesn't exist.

### Best Practices

1. **Use SSL/TLS in production**
2. **Implement rate limiting**
3. **Set up proper firewall rules**
4. **Use strong passwords for admin accounts**
5. **Regular security updates**
6. **Monitor logs for suspicious activity**
7. **Backup database regularly**
8. **Use environment variables for secrets**

## Migration Between Modes

### From Internal to Nginx Mode

1. Update `config.py`:
   ```python
   DEPLOYMENT_MODE = "nginx"
   BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
   HOST = "0.0.0.0"
   ```

2. Set up nginx with provided example config

3. Restart application:
   ```bash
   python3 launch_harvest.py
   ```

### From Nginx to Internal Mode

1. Update `config.py`:
   ```python
   DEPLOYMENT_MODE = "internal"
   HOST = "127.0.0.1"
   ```

2. Restart application (nginx no longer needed):
   ```bash
   python3 launch_harvest.py
   ```

## Support

For issues or questions:
- Check this guide first
- Review `nginx.conf.example` for configuration examples
- Check application logs
- Verify configuration with `python3 launch_harvest.py`
