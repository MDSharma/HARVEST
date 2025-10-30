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

# Set the backend public URL (base URL without /api suffix)
# The application will append /api/... automatically
BACKEND_PUBLIC_URL = "https://www.yourdomain.com/harvest"

# Set the URL base pathname (must start and end with /)
URL_BASE_PATHNAME = "/harvest/"
```

**Important:** 
- `URL_BASE_PATHNAME` must start and end with forward slashes (`/`)
- `BACKEND_PUBLIC_URL` is the base URL WITHOUT `/api` suffix
  - The application automatically adds `/api/...` to form complete API URLs
  - ✓ Correct: `"https://yourdomain.com/harvest"` → API calls to `/harvest/api/...`
  - ✗ Wrong: `"https://yourdomain.com/harvest/api"` → Results in `/harvest/api/api/...`

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
python3 launch_t2t.py

# Or manually
python3 t2t_training_be.py  # Terminal 1
python3 t2t_training_fe.py  # Terminal 2
```

### 4. Verify the Configuration

1. Access your application at `https://www.yourdomain.com/harvest/`
2. Open browser developer tools (F12) and check the Console tab
3. Verify that assets are loaded from `/harvest/_dash-component-suites/...`
4. Check that API calls go to `/harvest/api/...`

## Environment Variables

You can also configure these settings using environment variables instead of editing `config.py`:

```bash
export T2T_DEPLOYMENT_MODE="nginx"
export T2T_BACKEND_PUBLIC_URL="https://www.yourdomain.com/harvest/api"
export T2T_URL_BASE_PATHNAME="/harvest/"
python3 launch_t2t.py
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
- [config.py](config.py) - All configuration options
