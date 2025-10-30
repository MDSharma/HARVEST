# Understanding Flask Routing in Nginx vs Internal Mode

## The Problem You Encountered

When you ran the app with `URL_BASE_PATHNAME = "/harvest/"` in nginx mode:
- Flask was listening at `http://0.0.0.0:8050/harvest/`
- Nginx was stripping `/harvest/` and forwarding to `http://127.0.0.1:8050/`
- Result: **404 errors** because Flask expected requests at `/harvest/` but received them at `/`

## The Fix

The fix separates where Flask listens from where URLs are generated:

### Nginx Mode (Your Deployment)

```
Browser                 Nginx                       Flask/Dash
  |                       |                             |
  |  GET /harvest/        |                             |
  |-------------------->  |                             |
  |                       |  Strips prefix              |
  |                       |  GET /                      |
  |                       |--------------------------> |
  |                       |                             | Flask listening at /
  |                       |                             | (routes_pathname_prefix = "/")
  |                       |                             |
  |                       |  Response with HTML         |
  |                       |  <script src="/harvest/.."> |
  |                       | <--------------------------|
  |  HTML with URLs       |                             |
  |  prefixed /harvest/   |                             |
  | <--------------------|                             |
  |                       |                             |
  |  GET /harvest/assets  |                             |
  |-------------------->  |                             |
  |                       |  Strips prefix              |
  |                       |  GET /assets                |
  |                       |--------------------------> |
  |                       |                             | Flask serves from /assets
  |                       | <--------------------------|
  | <--------------------|                             |
```

**Configuration:**
- `routes_pathname_prefix = "/"` - Flask listens at root
- `requests_pathname_prefix = "/harvest/"` - Browser requests with prefix
- Nginx config: `location /harvest/ { proxy_pass http://127.0.0.1:8050/; }`

### Internal Mode (No Nginx)

```
Browser                                           Flask/Dash
  |                                                   |
  |  GET /harvest/                                    |
  |------------------------------------------------> |
  |                                                   | Flask listening at /harvest/
  |                                                   | (routes_pathname_prefix = "/harvest/")
  |                                                   |
  |  Response with HTML                               |
  |  <script src="/harvest/..">                       |
  | <------------------------------------------------|
  |                                                   |
  |  GET /harvest/assets                              |
  |------------------------------------------------> |
  |                                                   | Flask serves from /harvest/assets
  | <------------------------------------------------|
```

**Configuration:**
- `routes_pathname_prefix = "/harvest/"` - Flask listens at subpath
- `requests_pathname_prefix = "/harvest/"` - Browser requests with prefix
- Direct access: `http://localhost:8050/harvest/`

## Your Config

With your configuration:
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://text2trait.com/api"
URL_BASE_PATHNAME = "/harvest/"
```

The app now automatically sets:
- `routes_pathname_prefix = "/"` (Flask listens at root)
- `requests_pathname_prefix = "/harvest/"` (URLs generated with prefix)

This matches your nginx configuration where:
- `location /harvest/` receives requests
- `proxy_pass http://127.0.0.1:8050/` forwards without the `/harvest/` prefix

## Expected Behavior After Fix

1. Run `python3 harvest_fe.py`
2. You'll see: `Dash is running on http://0.0.0.0:8050/`
   - Note: No `/harvest/` in the URL - Flask is listening at root
3. Access `https://text2trait.com/harvest/`
4. Browser requests go to `/harvest/...`
5. Nginx strips prefix and forwards to Flask at `/...`
6. Flask serves the content
7. HTML contains URLs like `/harvest/_dash-component-suites/...`
8. Browser requests those URLs
9. Nginx proxies them to Flask
10. Assets load successfully ✓

## Testing Your Fix

After restarting the app, verify:

1. **Flask startup message:**
   ```
   Dash is running on http://0.0.0.0:8050/
   ```
   (Not `http://0.0.0.0:8050/harvest/`)

2. **Browser can access:**
   ```
   https://text2trait.com/harvest/
   ```
   (Should load successfully)

3. **Assets load from:**
   ```
   https://text2trait.com/harvest/_dash-component-suites/...
   ```
   (Check Network tab in DevTools - should be 200, not 404)

4. **No 404 errors in:**
   - Browser console
   - Nginx access logs
   - Flask logs
