# Systemd Service Configuration Fix

## Problem
The HARVEST backend service failed to start when running as a systemd service with the error:
```
sqlite3.OperationalError: unable to open database file
```

## Root Causes
1. **Environment variables not fully supported**: When `config.py` existed, only `DEPLOYMENT_MODE` and `BACKEND_PUBLIC_URL` could be overridden by environment variables. Critical settings like `DB_PATH`, `PORT`, and `HOST` could not be configured via environment variables.

2. **Database directory not created**: The application did not create the parent directory for the database file, causing failures when the directory didn't exist.

## Solution
The fix implements two key improvements:

### 1. Full Environment Variable Override Support
All configuration settings can now be overridden via environment variables, even when `config.py` exists:

- `HARVEST_DB` - Database file path
- `HARVEST_PORT` - Backend port
- `HARVEST_HOST` - Backend host binding
- `HARVEST_DEPLOYMENT_MODE` - Deployment mode (internal/nginx)
- `HARVEST_BACKEND_PUBLIC_URL` - Public backend URL

### 2. Automatic Directory Creation
The backend now automatically creates the database directory if it doesn't exist, eliminating manual setup steps.

## Usage with Systemd

### Recommended: Production-Grade with Gunicorn

For production deployments, it's strongly recommended to use Gunicorn instead of the Flask development server. Gunicorn is a production-grade WSGI server that handles multiple workers, timeouts, and graceful restarts.

**Install Gunicorn (already included in requirements.txt):**
```bash
pip install gunicorn>=21.2.0
```

**Backend Service Configuration (Gunicorn):**

```ini
[Unit]
Description=HARVEST Backend API Service (Gunicorn)
After=network.target
Requires=network.target

[Service]
Type=notify
User=harvest
Group=harvest
WorkingDirectory=/opt/harvest

# All settings via environment variables
Environment="HARVEST_DB=/opt/harvest/data/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://yourdomain.com/api"
Environment="HARVEST_HOST=127.0.0.1"
Environment="HARVEST_PORT=5001"

# Use Gunicorn with 4 worker processes
ExecStart=/opt/harvest/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5001 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    wsgi:app

Restart=always
RestartSec=10

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

[Install]
WantedBy=multi-user.target
```

### Alternative: Development Server (Not Recommended for Production)

If you need to use the Flask development server (e.g., for testing), you can use this configuration:

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

# All settings via environment variables
Environment="HARVEST_DB=/opt/harvest/data/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://yourdomain.com/api"
Environment="HARVEST_HOST=127.0.0.1"
Environment="HARVEST_PORT=5001"

ExecStart=/opt/harvest/venv/bin/python3 /opt/harvest/harvest_be.py

Restart=always
RestartSec=10

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

[Install]
WantedBy=multi-user.target
```

**Note:** The Flask development server is single-threaded and not designed for production use. Gunicorn provides:
- Multiple worker processes for better performance
- Graceful worker restarts
- Better timeout handling
- Process monitoring and automatic recovery

### Key Points

1. **No manual directory creation needed**: The database directory (`/opt/harvest/data` in the example) is created automatically on first run.

2. **Environment variables take precedence**: Even if you have a `config.py` file, environment variables will override those settings.

3. **Backward compatible**: Existing deployments using only `config.py` continue to work without changes.

4. **Gunicorn is production-ready**: The Gunicorn configuration above uses 4 worker processes, which is suitable for most deployments. Adjust `--workers` based on your server resources (typically 2-4 × CPU cores).

## Migration from Old Configuration

If you were previously using environment variables with the `T2T_` prefix (from the older "Text2Trait" naming), update them to use the `HARVEST_` prefix:

**Old (no longer works):**
```ini
Environment="T2T_DB=/opt/harvest/harvest/t2t_training.db"
Environment="T2T_DEPLOYMENT_MODE=nginx"
Environment="T2T_BACKEND_PUBLIC_URL=https://text2trait.com/harvest"
Environment="T2T_HOST=127.0.0.1"
Environment="T2T_PORT=5001"
```

**New (correct):**
```ini
Environment="HARVEST_DB=/opt/harvest/data/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://text2trait.com/harvest"
Environment="HARVEST_HOST=127.0.0.1"
Environment="HARVEST_PORT=5001"
```

## Testing

A comprehensive test suite (`test_config_overrides.py`) validates:
- Environment variables correctly override config.py settings
- Database directory is created automatically
- Database initialization works in newly created directories

Run the tests:
```bash
python3 test_config_overrides.py
```

## Documentation

Full systemd service examples and configuration details are available in:
- [DEPLOYMENT.md](DEPLOYMENT.md) - Section "Running as a Systemd Service"

## Security

- All changes have been scanned with CodeQL (0 security alerts)
- No breaking changes to existing functionality
- Follow principle of least privilege in systemd service configuration
