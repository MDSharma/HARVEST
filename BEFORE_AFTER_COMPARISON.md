# Before and After: Fixing Dash Subpath Deployment

## Before (Broken State)

### Browser Console Errors:
```
The resource from "https://www.text2trait.com/_dash-component-suites/dash/deps/react@18.v3_2_0m1761823965.3.1.min.js" 
was blocked due to MIME type ("text/html") mismatch (X-Content-Type-Options: nosniff).

The resource from "https://www.text2trait.com/_dash-component-suites/dash/deps/react-dom@18.v3_2_0m1761823965.3.1.min.js" 
was blocked due to MIME type ("text/html") mismatch (X-Content-Type-Options: nosniff).

Loading failed for the <script> with source "https://www.text2trait.com/_dash-component-suites/dash/deps/polyfill@7.v3_2_0m1761823965.12.1.min.js"
```

### What Was Happening:
```
User accesses: https://www.text2trait.com/harvest/
                                              ↓
Nginx proxies to: http://127.0.0.1:8050/
                                              ↓
Dash serves HTML with: <script src="/_dash-component-suites/...">
                                              ↓
Browser requests: https://www.text2trait.com/_dash-component-suites/...
                                              ↓
Nginx location / tries to serve from: /var/www/text2trait.com/_dash-component-suites/...
                                              ↓
❌ File not found → Returns HTML error page with MIME type text/html
❌ Browser rejects: Expected JavaScript, got HTML
❌ App stuck on "Loading..."
```

### Code State:
```python
# config.py
DEPLOYMENT_MODE = "internal"  # or "nginx" without subpath support
BACKEND_PUBLIC_URL = ""

# t2t_training_fe.py
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
# No url_base_pathname configured → Dash assumes root deployment
```

### Nginx Configuration:
```nginx
location /harvest/ {
    proxy_pass http://127.0.0.1:8050/;
    # ... proxy settings
}

location / {
    root /var/www/text2trait.com;
    # This catches /_dash-component-suites/ requests → Wrong!
}
```

---

## After (Fixed State)

### Browser Console:
```
✓ All JavaScript files load successfully
✓ No MIME type errors
✓ Application loads and functions correctly
```

### What Happens Now:
```
User accesses: https://www.text2trait.com/harvest/
                                              ↓
Nginx proxies to: http://127.0.0.1:8050/
                                              ↓
Dash (configured with url_base_pathname="/harvest/") serves:
    <script src="/harvest/_dash-component-suites/...">
                                              ↓
Browser requests: https://www.text2trait.com/harvest/_dash-component-suites/...
                                              ↓
Nginx location /harvest/ proxies to: http://127.0.0.1:8050/_dash-component-suites/...
                                              ↓
✓ Dash serves the JavaScript file
✓ Browser receives JavaScript with correct MIME type
✓ App loads successfully!
```

### Code State:
```python
# config.py
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://www.text2trait.com/harvest/api"
URL_BASE_PATHNAME = "/harvest/"  # NEW! Tells Dash about the subpath

# t2t_training_fe.py
from config import URL_BASE_PATHNAME

# Validate pathname
if not URL_BASE_PATHNAME.startswith("/") or not URL_BASE_PATHNAME.endswith("/"):
    raise ValueError(f"URL_BASE_PATHNAME must start and end with '/'. Got: {URL_BASE_PATHNAME}")

# Configure Dash with url_base_pathname
app = dash.Dash(
    __name__, 
    external_stylesheets=external_stylesheets,
    url_base_pathname=URL_BASE_PATHNAME  # NEW! Dash now knows it's at /harvest/
)
```

### Nginx Configuration (Already Correct):
```nginx
location /harvest/ {
    proxy_pass http://127.0.0.1:8050/;
    # Now correctly proxies all /harvest/* requests including assets
    # ... proxy settings
}

location /harvest/api/ {
    rewrite ^/harvest/api/(.*) /api/$1 break;
    proxy_pass http://127.0.0.1:5001;
    # ... proxy settings
}

location / {
    root /var/www/text2trait.com;
    # Only serves your main site, not Dash assets
}
```

---

## Key Differences

| Aspect | Before | After |
|--------|--------|-------|
| **Asset URLs in HTML** | `/_dash-component-suites/...` | `/harvest/_dash-component-suites/...` |
| **Browser Requests** | Root path (wrong) | Subpath (correct) |
| **Nginx Handling** | Falls through to location / | Proxied via location /harvest/ |
| **MIME Type** | text/html (error page) | application/javascript (correct) |
| **App State** | Stuck on "Loading..." | ✓ Loads successfully |
| **Configuration** | No subpath awareness | URL_BASE_PATHNAME configured |

---

## The Fix in One Line

**Problem:** Dash didn't know it was deployed at `/harvest/`, so it generated asset URLs at the root.

**Solution:** Configure Dash with `url_base_pathname="/harvest/"` so it generates correct URLs.

---

## How Dash's url_base_pathname Works

When you set `url_base_pathname="/harvest/"`, Dash automatically:

1. **Prefixes all asset URLs:**
   - Before: `/_dash-component-suites/dash/deps/react.js`
   - After: `/harvest/_dash-component-suites/dash/deps/react.js`

2. **Prefixes all callback URLs:**
   - Before: `/_dash-update-component`
   - After: `/harvest/_dash-update-component`

3. **Prefixes all route URLs:**
   - Before: `/`
   - After: `/harvest/`

4. **Handles redirects correctly:**
   - All internal redirects respect the base pathname

This ensures that every URL generated by Dash includes the `/harvest/` prefix, making all requests go through the correct nginx location block.

---

## Why This Matters

Without proper subpath configuration:
- ❌ Static assets fail to load (JavaScript, CSS)
- ❌ Callbacks don't work (AJAX requests go to wrong URLs)
- ❌ Navigation breaks (internal links go to wrong paths)
- ❌ App is completely unusable

With proper subpath configuration:
- ✓ All assets load from correct paths
- ✓ Callbacks work correctly
- ✓ Navigation works as expected
- ✓ App functions normally at any subpath

---

## Verification Checklist

After applying the fix, verify:

1. **Assets Load:**
   - Open browser DevTools → Network tab
   - Check that all requests to `/_dash-component-suites/` now go to `/harvest/_dash-component-suites/`
   - Verify status 200 (not 404) for all asset requests

2. **No Console Errors:**
   - Open browser DevTools → Console tab
   - Should see no MIME type errors
   - Should see no 404 errors

3. **App Functions:**
   - App should load completely (no infinite "Loading...")
   - All features should work normally
   - Navigation should work correctly

4. **Correct URLs:**
   - View page source
   - All `<script>` and `<link>` tags should have `/harvest/` prefix
   - Example: `<script src="/harvest/_dash-component-suites/..."></script>`
