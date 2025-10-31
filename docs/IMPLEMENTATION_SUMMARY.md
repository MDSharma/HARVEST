# Fix Summary: Dash App Subpath Deployment with Nginx

## Problem
When deploying the HARVEST Dash application behind an nginx reverse proxy at a subpath (e.g., `/harvest/`), the browser console showed errors like:

```
The resource from "https://www.text2trait.com/_dash-component-suites/dash/deps/react@18.v3_2_0m1761823965.3.1.min.js" was blocked due to MIME type ("text/html") mismatch (X-Content-Type-Options: nosniff).
```

This occurred because Dash was trying to load assets from the root path (`/_dash-component-suites/...`) instead of from the subpath (`/harvest/_dash-component-suites/...`).

## Root Cause
Dash applications need to be explicitly configured with their base pathname when deployed at a subpath. Without this configuration, Dash assumes it's deployed at the root and generates incorrect URLs for static assets.

## Solution Implemented

### 1. Added URL_BASE_PATHNAME Configuration
**File: `config.py`**

Added a new configuration option:
```python
# URL Base Pathname (required when app is served at a subpath)
# This is the base path where the application is mounted in the URL structure
# Examples:
#   - "/" (default, app at root)
#   - "/harvest/" (app at https://domain.com/harvest/)
#   - "/t2t/" (app at https://domain.com/t2t/)
# IMPORTANT: Must start and end with forward slashes
URL_BASE_PATHNAME = "/"  # Default: "/" for root deployment
```

### 2. Updated Frontend to Use url_base_pathname
**File: `harvest_fe.py`**

Modified the Dash app initialization to:
- Import `URL_BASE_PATHNAME` from config
- Support environment variable override via `HARVEST_URL_BASE_PATHNAME`
- Validate that the pathname starts and ends with `/`
- Pass the pathname to Dash's `url_base_pathname` parameter

```python
# Import configuration
from config import URL_BASE_PATHNAME

# Override with environment variable if present
URL_BASE_PATHNAME = os.getenv("HARVEST_URL_BASE_PATHNAME", URL_BASE_PATHNAME)

# Validate URL_BASE_PATHNAME
if not URL_BASE_PATHNAME.startswith("/") or not URL_BASE_PATHNAME.endswith("/"):
    raise ValueError(f"URL_BASE_PATHNAME must start and end with '/'. Got: {URL_BASE_PATHNAME}")

# Initialize Dash app with url_base_pathname
app: Dash = dash.Dash(
    __name__, 
    external_stylesheets=external_stylesheets, 
    suppress_callback_exceptions=True,
    url_base_pathname=URL_BASE_PATHNAME
)
```

### 3. Updated Nginx Configuration Example
**File: `nginx.conf.example`**

Added a comprehensive example for subpath deployment showing the exact configuration needed:

```nginx
# Frontend at /harvest/ subpath
location /harvest/ {
    proxy_pass http://harvest_frontend/;
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

# Backend API at /harvest/api/
location /harvest/api/ {
    rewrite ^/harvest/api/(.*) /api/$1 break;
    proxy_pass http://harvest_backend;
    # ... other proxy settings
}
```

### 4. Created Comprehensive Documentation
**File: `DEPLOYMENT_SUBPATH.md`**

Created a detailed guide covering:
- Problem description and symptoms
- Step-by-step configuration instructions
- Complete nginx configuration example
- Troubleshooting section for common issues
- Multiple deployment scenarios
- Security considerations

### 5. Updated Main Documentation
**File: `README.md`**

- Added reference to the new DEPLOYMENT_SUBPATH.md guide
- Added `HARVEST_URL_BASE_PATHNAME` to the environment variables list

## How to Use

### For the User's Specific Case

To fix the issue on www.text2trait.com with the app at `/harvest/`:

1. **Update config.py:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://www.text2trait.com/harvest/api"
URL_BASE_PATHNAME = "/harvest/"
```

2. **Or set environment variables:**
```bash
export HARVEST_DEPLOYMENT_MODE="nginx"
export HARVEST_BACKEND_PUBLIC_URL="https://www.text2trait.com/harvest/api"
export HARVEST_URL_BASE_PATHNAME="/harvest/"
```

3. **Restart the application:**
```bash
python3 launch_harvest.py
```

The nginx configuration provided by the user is already correct and compatible with this solution.

### Key Points

- `URL_BASE_PATHNAME` must start and end with `/` (e.g., `/harvest/`, not `/harvest`)
- The value should match the location path in your nginx configuration
- Environment variable `HARVEST_URL_BASE_PATHNAME` can override the config file
- Works with any subpath, including nested paths like `/app/harvest/`

## Testing

Comprehensive tests were run to verify:
1. ✅ Default configuration (root path `/`) works correctly
2. ✅ Subpath configuration (`/harvest/`) works correctly
3. ✅ Nested subpath configuration (`/app/harvest/`) works correctly
4. ✅ Invalid paths (no trailing slash) are properly rejected
5. ✅ Invalid paths (no leading slash) are properly rejected
6. ✅ Dash app receives correct configuration values
7. ✅ All Python files compile without syntax errors
8. ✅ Code review passed with no issues
9. ✅ CodeQL security scan found no vulnerabilities

## Files Changed

1. `config.py` - Added URL_BASE_PATHNAME configuration
2. `harvest_fe.py` - Updated to use url_base_pathname
3. `nginx.conf.example` - Added subpath deployment example
4. `DEPLOYMENT_SUBPATH.md` - New comprehensive deployment guide
5. `README.md` - Updated with new documentation links

## Security Summary

**CodeQL Analysis:** No vulnerabilities found

All changes were reviewed for security implications:
- Input validation added for URL_BASE_PATHNAME (must start/end with `/`)
- No new external dependencies introduced
- No changes to authentication or authorization logic
- Configuration follows security best practices
- nginx configuration examples include security headers

## Backward Compatibility

This change is 100% backward compatible:
- Default value of `URL_BASE_PATHNAME` is `/` (root deployment)
- Existing deployments at root path continue to work without changes
- Only affects deployments that explicitly set a different base pathname
- No database migrations required
- No breaking changes to API or functionality

## Additional Benefits

1. **Flexibility**: App can now be deployed at any subpath
2. **Multiple Instances**: Multiple app instances can run on the same domain
3. **Better Documentation**: Clear guidance for nginx subpath deployments
4. **Environment Variable Support**: Easy configuration without editing files
5. **Validation**: Prevents common configuration mistakes with clear error messages

## Next Steps for User

1. Update `config.py` or set environment variables as shown above
2. Restart the application
3. Clear browser cache
4. Access the app at `https://www.text2trait.com/harvest/`
5. Verify assets load correctly in browser developer console
6. Test all functionality to ensure everything works as expected

If you encounter any issues, refer to the troubleshooting section in DEPLOYMENT_SUBPATH.md.
