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

- `HARVEST_DB` - Database file path (optional override)
- `HARVEST_PORT` - Backend port (optional override)
- `HARVEST_HOST` - Backend host binding (optional override)
- `HARVEST_DEPLOYMENT_MODE` - Deployment mode (optional override)
- `HARVEST_BACKEND_PUBLIC_URL` - Public backend URL (optional override)

**Important:** Environment variables are **optional**. If you're happy with the paths defined in `config.py`, you don't need to set any environment variables.

### 2. Automatic Directory Creation
The backend now automatically creates the database directory if it doesn't exist, eliminating manual setup steps.

## Understanding Path Structure

### Typical Installation Layout
If you install by cloning into a user's home directory:
```
/opt/harvest/               # User home directory
└── harvest/                # Git repository (cloned)
    ├── harvest_be.py
    ├── harvest_fe.py
    ├── config.py
    ├── harvest.db          # Default DB location (from config.py: DB_PATH = "harvest.db")
    ├── project_pdfs/       # PDF storage directory
    └── assets/             # Static assets
```

In this case:
- `WorkingDirectory=/opt/harvest/harvest`
- `config.py` has `DB_PATH = "harvest.db"` (relative path)
- Actual database location: `/opt/harvest/harvest/harvest.db`
- **No environment variables needed** - config.py settings are sufficient

### When to Use Environment Variables

Use environment variables when you want to:
1. **Override config.py paths** (e.g., store database in a different location)
2. **Keep sensitive data out of config.py** (e.g., deployment URLs)
3. **Support multiple deployments** with different configurations from the same code

Example: If you want database in a separate directory:
- Set `Environment="HARVEST_DB=/var/lib/harvest/harvest.db"`
- The directory `/var/lib/harvest/` will be created automatically

## Usage with Systemd

### Recommended: Production-Grade with Gunicorn

For production deployments, it's strongly recommended to use Gunicorn instead of the Flask development server. Gunicorn is a production-grade WSGI server that handles multiple workers, timeouts, and graceful restarts.

**Install Gunicorn (already included in requirements.txt):**
```bash
pip install gunicorn>=21.2.0
```

#### Option A: Using config.py settings (Recommended for standard installations)

If you're using the default installation structure and config.py settings are sufficient:

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
ReadWritePaths=/opt/harvest/harvest

[Install]
WantedBy=multi-user.target
```

**Notes:**
- `WorkingDirectory=/opt/harvest/harvest` assumes you cloned the repo into `/opt/harvest/`
- Uses settings from `config.py`: `DB_PATH = "harvest.db"` → `/opt/harvest/harvest/harvest.db`
- `ReadWritePaths=/opt/harvest/harvest` allows writing to the repository directory

#### Option B: Using environment variable overrides (For custom paths)

If you want to store data in separate locations outside the repository:

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

# Override config.py settings with custom paths
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
ReadWritePaths=/var/lib/harvest
ReadWritePaths=/opt/harvest/harvest/project_pdfs

[Install]
WantedBy=multi-user.target
```

**Notes:**
- Database stored in `/var/lib/harvest/` (created automatically)
- `ReadWritePaths` must include all directories the service needs to write to
- Environment variables override `config.py` settings
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

### Key Points

1. **Environment variables are optional**: If `config.py` paths work for you, you don't need to set environment variables in the service file.

2. **Automatic directory creation**: Any database directory will be created automatically on first run (whether from `config.py` or environment variables).

3. **Environment variables override config.py**: When set, environment variables take precedence over `config.py` settings.

4. **Working directory matters**: Set `WorkingDirectory` to where the code is located (e.g., `/opt/harvest/harvest` if cloned into `/opt/harvest/`)

5. **Gunicorn is production-ready**: The Gunicorn configuration uses 4 worker processes, suitable for most deployments. Adjust `--workers` based on your server resources (typically 2-4 × CPU cores).

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

**New (if using environment overrides):**
```ini
Environment="HARVEST_DB=/opt/harvest/harvest/harvest.db"
Environment="HARVEST_DEPLOYMENT_MODE=nginx"
Environment="HARVEST_BACKEND_PUBLIC_URL=https://text2trait.com/harvest"
```

**Or simply omit environment variables and use config.py:**
No `Environment=` lines needed - the service will use values from `config.py`

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
