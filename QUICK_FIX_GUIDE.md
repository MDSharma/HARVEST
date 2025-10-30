# Quick Fix Guide for www.text2trait.com/harvest/

## Problem
The HARVEST app at https://www.text2trait.com/harvest/ shows "Loading..." forever with browser console errors about MIME type mismatches for JavaScript files.

## Root Cause
The Dash application wasn't configured to know it's deployed at the `/harvest/` subpath behind nginx, so it was generating incorrect URLs for its static assets.

## How It Works Now

With the fix applied:
1. **Nginx** receives requests at `/harvest/` and proxies to `http://127.0.0.1:8050/` (stripping the prefix)
2. **Flask/Dash** listens at root `/` on port 8050
3. **Dash** generates URLs with `/harvest/` prefix in HTML/JavaScript
4. **Browser** requests assets from `/harvest/_dash-component-suites/...`
5. **Nginx** proxies these requests back to Flask at `/_dash-component-suites/...`

This separation allows nginx to handle the path routing while Flask serves content from root.

## Solution (3 Steps)

### Step 1: Update Configuration

Edit `/home/runner/work/HARVEST/HARVEST/config.py` and set:

```python
# Change these settings:
DEPLOYMENT_MODE = "nginx"
URL_BASE_PATHNAME = "/harvest/"
```

**Critical Notes:** 
- `URL_BASE_PATHNAME` must start AND end with a forward slash.
- `BACKEND_PUBLIC_URL` is not used by the application (can be left empty or used for documentation).
- The frontend server connects to the backend via localhost (127.0.0.1:5001) for all server-side API requests.

### Step 2: Restart the Application

```bash
# Stop the current application (Ctrl+C if running in terminal)
# Or if running as a service:
sudo systemctl restart harvest-backend
sudo systemctl restart harvest-frontend

# Or if using the launcher:
cd /home/runner/work/HARVEST/HARVEST
python3 launch_t2t.py
```

### Step 3: Clear Browser Cache and Test

1. Open https://www.text2trait.com/harvest/ in a browser
2. Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac) to hard refresh
3. Open Developer Tools (F12) → Console tab
4. Verify no errors about MIME type mismatches
5. Verify the app loads successfully

## Alternative: Using Environment Variables

Instead of editing `config.py`, you can set environment variables:

```bash
export T2T_DEPLOYMENT_MODE="nginx"
export T2T_BACKEND_PUBLIC_URL="https://www.text2trait.com/harvest/api"
export T2T_URL_BASE_PATHNAME="/harvest/"
python3 launch_t2t.py
```

## Verification

After applying the fix, check:

1. **Browser Console (F12 → Console):**
   - Should see NO errors about MIME type mismatches
   - Should see NO 404 errors

2. **Browser Network Tab (F12 → Network):**
   - JavaScript files should be loaded from `/harvest/_dash-component-suites/...`
   - All should return status 200 (not 404)

3. **Page Source (Right-click → View Page Source):**
   - All `<script src="...">` tags should start with `/harvest/`
   - Example: `<script src="/harvest/_dash-component-suites/dash/deps/react@18..."></script>`

4. **Application:**
   - Should load completely (no infinite "Loading...")
   - All features should work normally

## Your Nginx Configuration

Your current nginx configuration is correct and doesn't need changes:

```nginx
location /harvest/ {
    proxy_pass http://harvest_frontend/;
    # ... (already correct)
}

location /harvest/api/ {
    rewrite ^/harvest/api/(.*) /api/$1 break;
    proxy_pass http://harvest_backend;
    # ... (already correct)
}
```

The issue was only on the application side, not nginx.

## Troubleshooting

### Still Seeing Errors?

1. **Clear browser cache:**
   - Chrome/Edge: Ctrl+Shift+Delete → Clear cached images and files
   - Firefox: Ctrl+Shift+Delete → Cached Web Content

2. **Verify configuration was applied:**
   ```bash
   cd /home/runner/work/HARVEST/HARVEST
   python3 -c "from config import URL_BASE_PATHNAME; print(f'URL_BASE_PATHNAME: {URL_BASE_PATHNAME}')"
   ```
   Should output: `URL_BASE_PATHNAME: /harvest/`

3. **Check application is running:**
   ```bash
   curl -I http://127.0.0.1:8050/
   curl -I http://127.0.0.1:5001/api/health
   ```

4. **Check nginx logs:**
   ```bash
   tail -f /var/log/nginx/harvest_error.log
   ```

### Configuration Validation Error?

If you see: `ValueError: URL_BASE_PATHNAME must start and end with '/'`

Make sure the value in config.py is:
- ✓ Correct: `"/harvest/"`
- ✗ Wrong: `"/harvest"` (missing trailing slash)
- ✗ Wrong: `"harvest/"` (missing leading slash)

### Assets (Images/Logos) Show 404 Errors?

If you see 404 errors for assets like `https://www.text2trait.com/assets/UM.jpg`:

1. **Verify the fix is applied:**
   Assets should be requested from `/harvest/assets/`, not `/assets/`
   
2. **Check browser Network tab:**
   Look for requests to logo files - they should go to `/harvest/assets/UM.jpg`

3. **Verify logo files exist:**
   ```bash
   ls -la assets/
   ```
   Logos should be in the `assets/` directory, not the root directory

### "Exceeded 30 redirects" Error?

This error should be resolved with the latest fix. The frontend now connects to the backend via localhost for all server-side requests.

**If you still see this error:**

1. **Verify backend is running:**
   ```bash
   curl -I http://127.0.0.1:5001/api/health
   ```
   Should return 200 OK

2. **Check nginx logs for issues:**
   ```bash
   tail -f /var/log/nginx/harvest_error.log
   ```

3. **Restart both services:**
   ```bash
   # Stop both services
   # Then restart:
   python3 t2t_training_be.py  # Terminal 1
   python3 t2t_training_fe.py  # Terminal 2
   ```

## Need Help?

See the comprehensive guides:
- [DEPLOYMENT_SUBPATH.md](DEPLOYMENT_SUBPATH.md) - Detailed deployment guide
- [BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md) - Understanding the fix
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Technical details

## Summary

The fix is simple:
1. Tell the app it's at `/harvest/` by setting `URL_BASE_PATHNAME`
2. Restart the application
3. Clear browser cache

That's it! The app will now generate correct URLs for all its assets.
