# Troubleshooting Login Issues

## Login Button Not Working in Nginx Deployment

If the login button doesn't respond when clicked in an nginx deployment, follow these debugging steps:

### Step 1: Check Browser Console for Errors

Open your browser's Developer Tools (F12) and check the Console tab for JavaScript errors:

1. Navigate to the Admin tab
2. Enter email and password
3. Click the Login button
4. Look for error messages in the console

Common errors:
- `Failed to fetch` or `Network error` - Backend API is not accessible
- `CORS error` - Cross-Origin Resource Sharing configuration issue
- `404 Not Found` - API endpoint routing problem in nginx
- No error but no response - Dash callback issue

### Step 2: Check Network Tab

In Developer Tools, go to the Network tab:

1. Clear the network log
2. Click the Login button
3. Look for the `/api/admin/auth` request

Check:
- **Request URL**: Should match your nginx configuration
- **Status Code**: 200 = success, 404 = routing problem, 500 = server error, 502/504 = backend unreachable
- **Response**: Check the JSON response body

### Step 3: Check Backend Logs

Check if the backend is receiving the authentication request:

```bash
# If using systemd:
sudo journalctl -u harvest-backend -f

# If running manually, check the terminal output
```

Look for:
- POST `/api/admin/auth` requests being logged
- Any error messages or exceptions

### Step 4: Check Frontend Logs

Check the frontend server logs:

```bash
# If using systemd:
sudo journalctl -u harvest-frontend -f

# If running manually, check the terminal output
```

### Step 5: Verify Configuration

#### config.py Settings

For nginx deployment at `/harvest/` subpath:

```python
DEPLOYMENT_MODE = "nginx"
URL_BASE_PATHNAME = "/harvest/"
BACKEND_PUBLIC_URL = ""  # This is for documentation only, not used by code
```

#### Nginx Configuration

For `/harvest/` subpath deployment, your nginx config should include:

```nginx
# Frontend at /harvest/ subpath
location /harvest/ {
    proxy_pass http://127.0.0.1:8050/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_redirect off;
}

# Backend API at /harvest/api/
location /harvest/api/ {
    # IMPORTANT: This rewrites /harvest/api/... to /api/...
    rewrite ^/harvest/api/(.*) /api/$1 break;
    proxy_pass http://127.0.0.1:5001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    proxy_http_version 1.1;
    proxy_redirect off;
}
```

**Critical**: The `rewrite` line is essential - it strips the `/harvest` prefix before proxying to the backend.

#### Test Nginx Configuration

```bash
# Test configuration syntax
sudo nginx -t

# If OK, reload nginx
sudo systemctl reload nginx
```

### Step 6: Test API Directly

Test if the API is accessible through nginx:

```bash
# Test from the server itself
curl -X POST http://localhost/harvest/api/admin/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword"}'

# Or test from your browser's domain
curl -X POST https://yourdomain.com/harvest/api/admin/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword"}'
```

Expected response:
```json
{"authenticated": true, "is_admin": true}
```

Or:
```json
{"authenticated": false, "is_admin": false}
```

### Common Issues and Solutions

#### Issue 1: Login button does nothing, no console errors

**Cause**: Dash callback not registered or prevent_initial_call blocking it

**Solution**: 
1. Clear browser cache (Ctrl+Shift+R)
2. Check if `HARVEST_CLEAR_CACHE=true` environment variable is set
3. Restart frontend server

#### Issue 2: 404 Not Found on `/api/admin/auth`

**Cause**: Nginx routing not configured correctly

**Solution**: 
- Add the `/harvest/api/` location block to nginx config (see Step 5)
- Include the `rewrite` directive to strip the subpath prefix
- Reload nginx

#### Issue 3: CORS errors in browser console

**Cause**: Frontend making client-side requests directly (shouldn't happen with current code)

**Solution**: 
- Verify `DEPLOYMENT_MODE = "nginx"` in config.py
- Check that Dash callbacks are using server-side `requests` library, not client-side fetch

#### Issue 4: 502 Bad Gateway

**Cause**: Backend server not running or not accessible

**Solution**:
- Check backend is running: `ps aux | grep harvest_be.py`
- Check backend port: `netstat -tlnp | grep 5001`
- Check backend logs for errors
- Ensure backend binds to correct interface (0.0.0.0 for nginx mode, or 127.0.0.1 for internal mode)

#### Issue 5: Wrong backend binding interface

**Cause**: Backend bound to wrong network interface

**Solution**:

For nginx deployment, backend should bind to 127.0.0.1 (localhost) since nginx proxies to localhost:

```python
# config.py
HOST = "127.0.0.1"  # Backend binds to localhost only
BE_PORT = 5001
```

The backend doesn't need to be externally accessible - only nginx needs to reach it on localhost.

### Step 7: Enable Debug Logging

For detailed debugging, enable debug logging:

```python
# config.py
ENABLE_DEBUG_LOGGING = True
```

Or via environment variable:
```bash
export HARVEST_DEBUG_LOGGING=true
```

Then restart both frontend and backend and check logs for detailed information.

**Important**: Disable debug logging in production!

### Still Having Issues?

If you've tried all the above steps and login still doesn't work, please provide:

1. Browser console output (any errors)
2. Network tab showing the `/api/admin/auth` request and response
3. Backend logs showing the request being received (or not)
4. Frontend logs
5. Your nginx configuration (sanitized)
6. Output of testing the API directly with curl

This information will help diagnose the specific issue in your deployment.
