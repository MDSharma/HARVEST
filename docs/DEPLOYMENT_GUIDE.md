# HARVEST Deployment Guide

Complete guide for deploying HARVEST in various environments and configurations.

## Table of Contents

- [Deployment Modes](#deployment-modes)
- [Internal Mode Setup](#internal-mode-setup)
- [Nginx Reverse Proxy Mode](#nginx-reverse-proxy-mode)
- [Subpath Deployment](#subpath-deployment)
- [Architecture Diagrams](#architecture-diagrams)
- [Production Considerations](#production-considerations)
- [Troubleshooting](#troubleshooting)

---

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
    build: ..
    command: python3 harvest_be.py
    environment:
      - HARVEST_DEPLOYMENT_MODE=nginx
      - HARVEST_HOST=0.0.0.0
      - HARVEST_PORT=5001
    ports:
      - "5001:5001"

  frontend:
    build: ..
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

### Path Configuration

**Important:** Choose the approach that matches your installation:

1. **Standard installation** (repo cloned into user's home):
   - Path: `/opt/harvest/harvest/` (user home + repo name)
   - Use `config.py` settings, no environment variables needed
   
2. **Custom installation** (separate data directory):
   - Use environment variables to override paths

### Recommended: Backend Service with Gunicorn

**Gunicorn is the recommended production WSGI server.** It provides better performance, multiple workers, and proper process management compared to the Flask development server.

#### Standard Installation (Using config.py)

Create `/etc/systemd/system/harvest-backend.service`:

```ini
[Unit]
Description=HARVEST Backend API Service (Gunicorn)
After=network.target
Requires=network.target

[Service]
Type=simple
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest/harvest

# Use Gunicorn with 4 worker processes
ExecStart=/opt/harvest/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5001 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi_be:app

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
ReadWritePaths=/opt/harvest/harvest

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**This configuration:**
- Uses paths from `config.py`: `DB_PATH = "harvest.db"` → `/opt/harvest/harvest/harvest.db`
- Allows writes to the entire repository directory
- No environment variables needed

#### Custom Paths (Override with Environment Variables)

If you want to store data outside the repository:

```ini
[Unit]
Description=HARVEST Backend API Service (Gunicorn)
After=network.target
Requires=network.target

[Service]
Type=notify
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest/harvest

# Override config.py with custom paths
Environment="HARVEST_DB=/var/lib/harvest/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://yourdomain.com/api"

# Use Gunicorn with 4 worker processes
ExecStart=/opt/harvest/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5001 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi_be:app

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
ReadWritePaths=/var/lib/harvest
ReadWritePaths=/opt/harvest/harvest/project_pdfs
ReadWritePaths=/opt/harvest/harvest/assets

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**Note:** 
- Gunicorn is included in `requirements.txt`
- Adjust `--workers` based on your server (typically 2-4 × CPU cores)
- Environment variables are **optional** - only use them if you need to override `config.py`

### Alternative: Backend Service with Flask Development Server

**Not recommended for production** - Use Gunicorn instead. This is for testing only:

```ini
[Unit]
Description=HARVEST Backend API Service
After=network.target
Requires=network.target

[Service]
Type=simple
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest/harvest

# Use the virtual environment
ExecStart=/opt/harvest/venv/bin/python3 harvest_be.py

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
ReadWritePaths=/opt/harvest/harvest

# Resource limits
LimitNOFILE=65535
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**Note:** Uses `config.py` settings. Add environment variables only if you need to override paths.

### Frontend Service

**Recommended: Use Gunicorn for production deployments.** Gunicorn provides better performance, multiple workers, and proper process management compared to the Dash development server.

Create `/etc/systemd/system/harvest-frontend.service`:

```ini
[Unit]
Description=HARVEST Frontend Service (Gunicorn)
After=network.target harvest-backend.service
Requires=network.target
Wants=harvest-backend.service

[Service]
Type=simple
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest/harvest

# Prevent Python bytecode generation to avoid stale callback issues
Environment="PYTHONDONTWRITEBYTECODE=1"

# Use Gunicorn with 4 worker processes
ExecStart=/opt/harvest/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:8050 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi_fe:server

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

**Note:** Uses `config.py` settings by default. Add environment variables like `HARVEST_DEPLOYMENT_MODE` or `HARVEST_BACKEND_PUBLIC_URL` only if you need to override config.py values.

#### Alternative: Development Server (Not Recommended for Production)

If you need to use the Dash development server (e.g., for testing):

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
WorkingDirectory=/opt/harvest/harvest

# Use the virtual environment
ExecStart=/opt/harvest/venv/bin/python3 harvest_fe.py

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

**Note:** Database directories will be automatically created if they don't exist, whether paths come from `config.py` or environment variables.

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


---

## Subpath Deployment

# Deploying HARVEST at a Subpath with Nginx

This guide explains how to deploy the HARVEST application at a subpath (e.g., `/harvest/`) behind an nginx reverse proxy, which is useful when you want to host the application alongside other services on the same domain.

## Problem

When deploying Dash applications behind a reverse proxy at a subpath, the application needs to know its base path to correctly serve static assets (JavaScript, CSS) and handle routing. Without proper configuration, you'll see errors like:

```
The resource from "https://example.com/_dash-component-suites/..." was blocked due to MIME type mismatch
```

This happens because the app tries to load assets from the root (`/_dash-component-suites/...`) instead of from the subpath (`/harvest/_dash-component-suites/...`).

## Solution

### Understanding the Configuration

The key to deploying at a subpath is understanding how nginx and Dash work together:

1. **Nginx** receives requests at `/harvest/` and forwards them to Flask at root `/`
2. **Flask/Dash** listens at root `/` but generates URLs with `/harvest/` prefix for the browser
3. **Browser** makes requests to `/harvest/...` which nginx proxies to Flask at `/...`

In **nginx mode**, the application automatically configures:
- Flask server listens at root `/` (because nginx strips the path prefix)
- Dash generates URLs with the `/harvest/` prefix (so browser requests go through nginx)

In **internal mode** (without nginx), the application configures:
- Flask server listens at `/harvest/` (direct access without nginx)
- Dash generates URLs with the `/harvest/` prefix

### 1. Configure the Application

Edit `config.py` to set the deployment mode and base pathname:

```python
# Set deployment mode to nginx
DEPLOYMENT_MODE = "nginx"

# Set the URL base pathname (must start and end with /)
URL_BASE_PATHNAME = "/harvest/"
```

**Important:** 
- `URL_BASE_PATHNAME` must start and end with forward slashes (`/`)
- `BACKEND_PUBLIC_URL` is not used by the application code (frontend connects to backend via localhost)
- The frontend server always makes server-side requests to `http://127.0.0.1:5001` regardless of deployment mode

### 2. Configure Nginx

Add the following configuration to your nginx server block:

```nginx
server {
    listen 443 ssl http2;
    server_name www.yourdomain.com;
    
    # SSL configuration (recommended)
    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    
    # Maximum upload size for PDF uploads
    client_max_body_size 100M;
    
    # Timeouts for long-running requests
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # HARVEST frontend at /harvest/ subpath
    location /harvest/ {
        proxy_pass http://127.0.0.1:8050/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Script-Name /harvest;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
    }
    
    # HARVEST backend API at /harvest/api/
    location /harvest/api/ {
        rewrite ^/harvest/api/(.*) /api/$1 break;
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Handle CORS preflight
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "*";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_redirect off;
    }
    
    # Other locations for your main site
    location / {
        root /var/www/yourdomain;
        index index.html;
    }
}
```

**Key nginx configuration points:**

1. **Frontend location** (`/harvest/`):
   - Trailing slash is important: `location /harvest/` 
   - `proxy_pass` must end with `/`: `http://127.0.0.1:8050/`
   - This ensures paths are correctly rewritten

2. **Backend location** (`/harvest/api/`):
   - Use `rewrite` to strip the `/harvest` prefix before passing to backend
   - Backend expects requests at `/api/*`, not `/harvest/api/*`

3. **Headers**:
   - `X-Script-Name` helps the application understand its mount point
   - WebSocket headers are needed for real-time features

### 3. Start the Application

```bash
# Using the launcher script
python3 launch_harvest.py

# Or manually
python3 harvest_be.py  # Terminal 1
python3 harvest_fe.py  # Terminal 2
```

### 4. Verify the Configuration

1. Access your application at `https://www.yourdomain.com/harvest/`
2. Open browser developer tools (F12) and check the Console tab
3. Verify that assets are loaded from `/harvest/_dash-component-suites/...`
4. Check that API calls go to `/harvest/api/...`

## Environment Variables

You can also configure these settings using environment variables instead of editing `config.py`:

```bash
export HARVEST_DEPLOYMENT_MODE="nginx"
export HARVEST_BACKEND_PUBLIC_URL="https://www.yourdomain.com/harvest/api"
export HARVEST_URL_BASE_PATHNAME="/harvest/"
python3 launch_harvest.py
```

## Troubleshooting

### Assets fail to load with MIME type errors

**Problem:** Browser console shows errors like:
```
The resource from "https://example.com/_dash-component-suites/..." was blocked due to MIME type mismatch
```

**Solution:** 
1. Verify `URL_BASE_PATHNAME="/harvest/"` is set in `config.py`
2. Restart the frontend service
3. Clear browser cache
4. Check that assets are requested from `/harvest/_dash-component-suites/...` (not from root)

### Backend API calls fail (404 or timeout)

**Problem:** Frontend can load but API calls fail

**Solution:**
1. Verify `BACKEND_PUBLIC_URL` points to the correct backend URL through nginx
2. Check nginx logs: `tail -f /var/log/nginx/error.log`
3. Verify the rewrite rule in nginx configuration is correct
4. Test backend directly: `curl http://127.0.0.1:5001/api/health`

### Application loads but shows "Loading..." forever

**Problem:** App is stuck in loading state

**Solution:**
1. Check browser console for JavaScript errors
2. Verify all assets loaded successfully (no 404s)
3. Check that `DEPLOYMENT_MODE="nginx"` is set
4. Ensure backend is running and accessible

### Pages or redirects don't work correctly

**Problem:** Internal links or redirects go to wrong URLs

**Solution:**
1. Verify `URL_BASE_PATHNAME` ends with a trailing slash (`/`)
2. Check nginx `proxy_redirect off` is set
3. Clear browser cache and try again

## Multiple Subpath Deployments

You can host multiple instances at different subpaths:

```nginx
# First instance at /harvest/
location /harvest/ {
    proxy_pass http://127.0.0.1:8050/;
    # ... config
}

location /harvest/api/ {
    rewrite ^/harvest/api/(.*) /api/$1 break;
    proxy_pass http://127.0.0.1:5001;
    # ... config
}

# Second instance at /research/
location /research/ {
    proxy_pass http://127.0.0.1:8051/;
    # ... config
}

location /research/api/ {
    rewrite ^/research/api/(.*) /api/$1 break;
    proxy_pass http://127.0.0.1:5002;
    # ... config
}
```

Just make sure each instance has:
- Unique port numbers
- Unique `URL_BASE_PATHNAME` in its config
- Corresponding `BACKEND_PUBLIC_URL`

## Security Considerations

1. **SSL/TLS**: Always use HTTPS in production
2. **Firewall**: Ensure backend port (5001) is not accessible from outside
3. **Rate limiting**: Consider adding nginx rate limiting for API endpoints
4. **CORS**: Adjust CORS headers based on your security requirements

## Additional Resources

- [nginx.conf.example](nginx.conf.example) - More nginx configuration examples
- [DEPLOYMENT.md](DEPLOYMENT.md) - General deployment guide
- [config.py](../config.py) - All configuration options


---

## Architecture Diagrams

# Deployment Architecture Diagrams

Visual guide to understand how the T2T Training Application works in different deployment modes.

## Table of Contents
- [Internal Mode Architecture](#internal-mode-architecture)
- [Nginx Mode Architecture](#nginx-mode-architecture)
- [Request Flow Comparison](#request-flow-comparison)
- [Component Interaction](#component-interaction)

---

## Internal Mode Architecture

### Network Diagram

```
┌─────────────────────────────────────────────────┐
│                 User's Browser                  │
│              (http://localhost:8050)            │
└────────────────────┬────────────────────────────┘
                     │
                     │ HTTP Requests
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│        Frontend (Dash) - Port 8050              │
│             Host: 0.0.0.0                       │
│                                                 │
│  Routes:                                        │
│  • / → Dash Application                         │
│  • /proxy/pdf/<id>/<file> → Proxy Route        │
│  • /proxy/highlights/<id>/<file> → Proxy Route │
└────────────────────┬────────────────────────────┘
                     │
                     │ Internal HTTP (127.0.0.1)
                     │ Proxied Requests Only
                     ▼
┌─────────────────────────────────────────────────┐
│        Backend (Flask) - Port 5001              │
│           Host: 127.0.0.1 (localhost)           │
│           NOT ACCESSIBLE EXTERNALLY              │
│                                                 │
│  API Endpoints:                                 │
│  • /api/health                                  │
│  • /api/projects/<id>/pdf/<file>               │
│  • /api/projects/<id>/pdf/<file>/highlights    │
│  • ... (all other API endpoints)                │
└─────────────────────────────────────────────────┘
```

### Key Characteristics

**Security:**
- Backend bound to `127.0.0.1` (localhost only)
- Backend not accessible from outside the server
- Only frontend is exposed to users

**Request Flow:**
1. User requests PDF → Frontend at `/proxy/pdf/...`
2. Frontend receives request
3. Frontend makes internal request to backend at `127.0.0.1:5001`
4. Backend serves PDF
5. Frontend streams PDF back to user

**Configuration:**
```python
DEPLOYMENT_MODE = "internal"
HOST = "127.0.0.1"  # Backend localhost only
```

---

## Nginx Mode Architecture

### Network Diagram (Single Server)

```
┌─────────────────────────────────────────────────┐
│                 User's Browser                  │
│           (https://yourdomain.com)              │
└────────────────────┬────────────────────────────┘
                     │
                     │ HTTPS Requests
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│           Nginx Reverse Proxy - Port 443        │
│                                                 │
│  Routes:                                        │
│  • / → Frontend                                 │
│  • /api/* → Backend                            │
│                                                 │
│  Features:                                      │
│  • SSL/TLS Termination                         │
│  • Load Balancing                              │
│  • Rate Limiting                               │
│  • Caching                                     │
└──────────┬─────────────────────┬────────────────┘
           │                     │
           │                     │
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │   Frontend   │      │   Backend    │
    │  (Dash)      │      │   (Flask)    │
    │  Port 8050   │      │  Port 5001   │
    │              │      │              │
    │ Host: 0.0.0.0│      │ Host: 0.0.0.0│
    └──────────────┘      └──────────────┘
```

### Network Diagram (Separate API Subdomain)

```
┌─────────────────────────────────────────────────┐
│               User's Browser                    │
└──────────┬─────────────────────┬────────────────┘
           │                     │
           │                     │
           ▼                     ▼
    ┌─────────────┐      ┌──────────────┐
    │   Nginx     │      │    Nginx     │
    │   (Main)    │      │    (API)     │
    │   Port 443  │      │   Port 443   │
    │             │      │              │
    │ yourdomain  │      │api.yourdomain│
    └──────┬──────┘      └──────┬───────┘
           │                     │
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │   Frontend   │      │   Backend    │
    │   Port 8050  │      │  Port 5001   │
    └──────────────┘      └──────────────┘
```

### Key Characteristics

**Security:**
- Backend bound to `0.0.0.0` (accessible on network)
- Nginx handles SSL/TLS termination
- Firewall should restrict direct backend access
- Rate limiting at nginx level

**Request Flow:**
1. User requests PDF → Nginx at `https://yourdomain.com/api/...`
2. Nginx routes to backend at `127.0.0.1:5001`
3. Backend serves PDF
4. Nginx returns to user

**Configuration:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
HOST = "0.0.0.0"  # Backend accessible on network
```

---

## Request Flow Comparison

### Internal Mode - PDF Request

```
Browser                Frontend                Backend
   │                      │                      │
   │ GET /proxy/pdf/1/x.pdf                     │
   ├──────────────────────>│                     │
   │                      │                      │
   │                      │ GET http://127.0.0.1:5001/
   │                      │     api/projects/1/pdf/x.pdf
   │                      ├─────────────────────>│
   │                      │                      │
   │                      │    PDF Data          │
   │                      │<─────────────────────┤
   │                      │                      │
   │    PDF Data          │                      │
   │<─────────────────────┤                      │
   │                      │                      │
```

### Nginx Mode - PDF Request

```
Browser                 Nginx               Backend
   │                      │                      │
   │ GET https://domain.com/api/projects/1/pdf/x.pdf
   ├──────────────────────>│                     │
   │                      │                      │
   │                      │ GET http://127.0.0.1:5001/
   │                      │     api/projects/1/pdf/x.pdf
   │                      ├─────────────────────>│
   │                      │                      │
   │                      │    PDF Data          │
   │                      │<─────────────────────┤
   │                      │                      │
   │    PDF Data (HTTPS)  │                      │
   │<─────────────────────┤                      │
   │                      │                      │
```

---

## Component Interaction

### Internal Mode Components

```
┌─────────────────────────────────────────────────┐
│                  config.py                      │
│  DEPLOYMENT_MODE = "internal"                   │
│  BACKEND_PUBLIC_URL = ""                        │
│  HOST = "127.0.0.1"                            │
└────────────┬────────────────────────────────────┘
             │
             │ Configuration Read
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
  ┌─────────┐  ┌─────────┐
  │Frontend │  │Backend  │
  │         │  │         │
  │Proxy ON │  │CORS:    │
  │API: int.│  │localhost│
  └─────────┘  └─────────┘
```

### Nginx Mode Components

```
┌─────────────────────────────────────────────────┐
│                  config.py                      │
│  DEPLOYMENT_MODE = "nginx"                      │
│  BACKEND_PUBLIC_URL = "https://api.domain.com"  │
│  HOST = "0.0.0.0"                              │
└────────────┬────────────────────────────────────┘
             │
             │ Configuration Read
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
  ┌─────────┐  ┌─────────┐
  │Frontend │  │Backend  │
  │         │  │         │
  │Proxy OFF│  │CORS:    │
  │API: pub.│  │allow all│
  └─────────┘  └─────────┘
       │           │
       │           │
       └─────┬─────┘
             │
             ▼
     ┌───────────────┐
     │     Nginx     │
     │  Port: 443    │
     │  SSL/TLS      │
     └───────────────┘
```

---

## CORS Configuration

### Internal Mode CORS

```
Backend CORS Configuration:
┌──────────────────────────────────────┐
│ Allowed Origins:                     │
│  • http://localhost:*                │
│  • http://127.0.0.1:*               │
│  • http://0.0.0.0:*                 │
│                                      │
│ Security: Restrictive                │
│ Reason: Backend only accessed        │
│         internally via proxy         │
└──────────────────────────────────────┘
```

### Nginx Mode CORS

```
Backend CORS Configuration:
┌──────────────────────────────────────┐
│ Allowed Origins:                     │
│  • * (all origins)                   │
│                                      │
│ Security: Permissive                 │
│ Reason: Nginx handles origin         │
│         restrictions, backend        │
│         trusts proxy                 │
└──────────────────────────────────────┘
```

---

## Scaling Patterns

### Internal Mode (Limited Scaling)

```
┌─────────┐
│ Server  │
│  ┌───┐  │
│  │FE │  │
│  └───┘  │
│  ┌───┐  │
│  │BE │  │
│  └───┘  │
└─────────┘

Limitation: Single server only
```

### Nginx Mode (Horizontal Scaling)

```
                ┌──────────┐
                │  Nginx   │
                │  (LB)    │
                └────┬─────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
      ┌───────┐  ┌───────┐  ┌───────┐
      │Server1│  │Server2│  │Server3│
      │ ┌──┐  │  │ ┌──┐  │  │ ┌──┐  │
      │ │BE│  │  │ │BE│  │  │ │BE│  │
      │ └──┘  │  │ └──┘  │  │ └──┘  │
      └───────┘  └───────┘  └───────┘

Capability: Multiple backend instances
           with load balancing
```

---

## Security Boundaries

### Internal Mode Security

```
┌───────────────────────────────────────┐
│           Firewall                    │
│  ┌─────────────────────────────────┐  │
│  │ Exposed: Frontend :8050         │  │
│  │ ┌────────────────────────────┐  │  │
│  │ │Protected: Backend :5001    │  │  │
│  │ │(localhost only)            │  │  │
│  │ └────────────────────────────┘  │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
```

### Nginx Mode Security

```
┌───────────────────────────────────────┐
│           Firewall                    │
│  ┌─────────────────────────────────┐  │
│  │ Exposed: Nginx :443 (SSL)       │  │
│  │ ┌────────────────────────────┐  │  │
│  │ │Internal Network            │  │  │
│  │ │  Frontend :8050            │  │  │
│  │ │  Backend :5001             │  │  │
│  │ └────────────────────────────┘  │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
```

---

## Decision Flow

### Choosing Deployment Mode

```
Start
  │
  ▼
Development or        YES    ┌──────────────┐
Simple Deployment? ────────> │ Internal Mode│
  │                           └──────────────┘
  │ NO
  ▼
Need SSL/TLS,         YES    ┌──────────────┐
Load Balancing, or   ────────> │ Nginx Mode   │
Multiple Instances?           └──────────────┘
  │
  │ NO
  ▼
┌────────────────────┐
│ Start with         │
│ Internal Mode,     │
│ Migrate Later      │
└────────────────────┘
```

---

## Migration Path

### Internal → Nginx

```
Step 1: Current State (Internal)
┌─────────────────────────────┐
│  Frontend ──> Backend        │
│  (proxy)    (localhost)      │
└─────────────────────────────┘

Step 2: Add Nginx
┌─────────────────────────────┐
│         Nginx                │
│           │                  │
│   ┌───────┴───────┐          │
│   ▼               ▼          │
│Frontend         Backend      │
└─────────────────────────────┘

Step 3: Update Config
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "..."
HOST = "0.0.0.0"

Step 4: Restart
Frontend now uses direct API
Proxy routes disabled
CORS updated automatically
```

---

## Performance Characteristics

### Internal Mode

```
┌────────────────────────────────────┐
│ Latency: Low (local only)         │
│ Throughput: Moderate               │
│ Bottleneck: Single server          │
│ Caching: Application level only    │
└────────────────────────────────────┘
```

### Nginx Mode

```
┌────────────────────────────────────┐
│ Latency: Low to Medium             │
│ Throughput: High (with scaling)    │
│ Bottleneck: Nginx capacity         │
│ Caching: Nginx + Application       │
│ Optimization: Load balancing       │
└────────────────────────────────────┘
```

---

## Summary

### Internal Mode
✓ Simple setup
✓ Secure by default
✓ Perfect for development
✗ No horizontal scaling
✗ No SSL at app level

### Nginx Mode
✓ Production ready
✓ Horizontal scaling
✓ SSL/TLS termination
✓ Advanced features
✗ More complex setup
✗ Requires proxy knowledge

**Recommendation**: Start with internal mode for development, migrate to nginx mode for production.


---


## Troubleshooting SystemD Services




---

## Additional Resources

- See [NGINX_VS_INTERNAL_MODE.md](NGINX_VS_INTERNAL_MODE.md) for detailed comparison
- See [nginx.conf.example](nginx.conf.example) for complete nginx configuration
- See [INSTALLATION.md](INSTALLATION.md) for installation instructions
