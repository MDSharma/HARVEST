# Login Button Not Working - Quick Fixes

## Most Common Cause: Browser Cache

The #1 cause of login buttons not responding in Dash applications is **stale browser cache** containing old JavaScript.

### Solution: Hard Refresh

**Windows/Linux:**
- Press `Ctrl + Shift + R` or `Ctrl + F5`

**Mac:**
- Press `Cmd + Shift + R`

**Alternative:**
1. Open browser DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Clear All Browser Data

If hard refresh doesn't work:

**Chrome/Edge:**
1. Press `Ctrl + Shift + Delete` (or `Cmd + Shift + Delete` on Mac)
2. Select "Cached images and files"
3. Time range: "All time"
4. Click "Clear data"

**Firefox:**
1. Press `Ctrl + Shift + Delete`
2. Select "Cache"
3. Time range: "Everything"
4. Click "Clear Now"

## Second Most Common: Dash Callback Not Registered

### Symptoms
- Button does nothing when clicked
- No network requests in browser DevTools
- No errors in console

### Solution: Restart Frontend Server

```bash
# Stop the frontend
pkill -f harvest_fe.py

# Clear Python bytecode cache (optional but recommended)
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find . -name '*.pyc' -delete 2>/dev/null

# Restart frontend
python3 harvest_fe.py
```

## Third: Check Browser Console

Open DevTools (F12) and check the Console tab for errors:

### Common Errors:

**"DashRenderer is not defined"**
- Dash JavaScript not loading
- Clear cache and hard refresh

**"Callback error"**
- Backend not accessible
- Check backend is running
- Check nginx configuration

**"Network Error" or "Failed to fetch"**
- API endpoint not reachable
- Check nginx `/harvest/api/` location block
- Verify backend is running

**No errors, button just doesn't work**
- Callback not registered
- Restart frontend server
- Clear browser cache

## Verification Steps

### 1. Test Backend Directly

```bash
curl -X POST http://localhost:5001/api/admin/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'
```

Should return:
```json
{"authenticated": true, "is_admin": true}
```

### 2. Test Through Nginx

```bash
curl -X POST https://yourdomain.com/harvest/api/admin/auth \
  -H "Content-Type: application/json" \
  -d '{"email":"your-email@example.com","password":"your-password"}'
```

Should return same response as above.

### 3. Use Diagnostic Script

```bash
python3 diagnose_login.py your-email@example.com your-password https://yourdomain.com
```

This will test both backend and nginx automatically.

## Still Not Working?

### Check These:

1. **Backend server is running:**
   ```bash
   ps aux | grep harvest_be.py
   netstat -tlnp | grep 5001
   ```

2. **Frontend server is running:**
   ```bash
   ps aux | grep harvest_fe.py
   netstat -tlnp | grep 8050
   ```

3. **Nginx is running and configured:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **Admin user exists in database:**
   ```bash
   python3 create_admin.py
   ```

5. **Check logs:**
   ```bash
   # Backend logs
   tail -f /path/to/backend.log
   
   # Frontend logs  
   tail -f /path/to/frontend.log
   
   # Nginx error logs
   sudo tail -f /var/log/nginx/error.log
   ```

### Debug Mode

Enable debug logging to see what's happening:

```python
# config.py
ENABLE_DEBUG_LOGGING = True
```

Restart both servers and check logs for detailed information.

**Remember to disable debug logging in production!**

## Need More Help?

See comprehensive troubleshooting guide:
- `docs/TROUBLESHOOTING_LOGIN.md` - Full diagnostic steps
- `python3 verify_nginx_deployment.py` - Automated checks
- `python3 diagnose_login.py` - Test authentication

## Quick Command Summary

```bash
# Hard refresh browser: Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# Restart frontend
pkill -f harvest_fe.py && python3 harvest_fe.py

# Test backend
curl -X POST http://localhost:5001/api/admin/auth -H "Content-Type: application/json" -d '{"email":"test@example.com","password":"test"}'

# Run diagnostics
python3 diagnose_login.py your-email@example.com your-password https://yourdomain.com

# Check what's running
ps aux | grep harvest
netstat -tlnp | grep -E '5001|8050'
```
