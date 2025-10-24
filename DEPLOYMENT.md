# Deployment Guide

This guide covers deploying the Text2Trait Training Data Builder in production with nginx as a reverse proxy.

## Architecture Notes

The application uses a client-side PDF loading architecture:
- Backend API discovers PDF URLs from open access sources (Unpaywall, CrossRef)
- Frontend receives the PDF URL and loads it directly in the browser
- PDFs are NOT proxied through the application server
- This reduces server bandwidth and improves performance
- Users' browsers load PDFs directly from publisher servers

## Quick Start (Development)

```bash
# Install dependencies
pip install -r requirements.txt
# or
poetry install

# Run the unified application
python3 app.py
```

The application will start both backend (port 5001) and frontend (port 8050) in a single process.

## Production Deployment

### Prerequisites

- Python 3.12 or higher
- nginx
- systemd (for service management)
- SSL certificate (recommended, e.g., via Let's Encrypt)

### Step 1: Install Dependencies

```bash
# Clone or copy the application
cd /opt/t2t-training

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

Create or update `.env` file:

```bash
# Database
T2T_DB=/opt/t2t-training/data/t2t.db

# Ports
T2T_BACKEND_PORT=5001
T2T_FRONTEND_PORT=8050

# Host (keep as 127.0.0.1 when behind nginx)
T2T_HOST=127.0.0.1

# Admin users (comma-separated)
T2T_ADMIN_EMAILS=admin@example.com,admin2@example.com

# Production settings
T2T_DEBUG=false
T2T_USE_PROXY_FIX=true

# Gunicorn settings (optional)
T2T_WORKERS=4
T2T_LOG_LEVEL=info
```

### Step 3: Set Permissions

```bash
# Create data directory
sudo mkdir -p /opt/t2t-training/data

# Set ownership
sudo chown -R www-data:www-data /opt/t2t-training

# Set permissions
sudo chmod -R 755 /opt/t2t-training
sudo chmod 775 /opt/t2t-training/data
```

### Step 4: Configure systemd Service

```bash
# Copy service file
sudo cp t2t-training.service /etc/systemd/system/

# Edit the service file with correct paths
sudo nano /etc/systemd/system/t2t-training.service

# Update these lines:
# WorkingDirectory=/opt/t2t-training
# Environment="PATH=/opt/t2t-training/venv/bin"
# EnvironmentFile=/opt/t2t-training/.env
# ExecStart=/opt/t2t-training/venv/bin/python3 app.py
# ReadWritePaths=/opt/t2t-training

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable t2t-training

# Start service
sudo systemctl start t2t-training

# Check status
sudo systemctl status t2t-training
```

### Step 5: Configure nginx

```bash
# Copy nginx configuration
sudo cp nginx.conf.example /etc/nginx/sites-available/t2t-training

# Edit the configuration
sudo nano /etc/nginx/sites-available/t2t-training

# Update server_name to your domain
# Update paths if necessary

# Create symbolic link
sudo ln -s /etc/nginx/sites-available/t2t-training /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 6: Configure SSL (Optional but Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure nginx for HTTPS
# Or manually uncomment the HTTPS server block in nginx.conf.example
```

## Alternative: Using Gunicorn

For better performance in production, you can use Gunicorn:

### Update systemd Service

Edit `/etc/systemd/system/t2t-training.service`:

```ini
# Replace ExecStart line with:
ExecStart=/opt/t2t-training/venv/bin/gunicorn -c gunicorn.conf.py app:frontend_app.server
```

Note: When using Gunicorn, the backend still needs to run separately. You'll need two services:

**t2t-backend.service:**
```ini
[Unit]
Description=Text2Trait Backend API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/t2t-training
Environment="PATH=/opt/t2t-training/venv/bin"
EnvironmentFile=/opt/t2t-training/.env
ExecStart=/opt/t2t-training/venv/bin/python3 t2t_training_be.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**t2t-frontend.service:**
```ini
[Unit]
Description=Text2Trait Frontend
After=network.target t2t-backend.service
Requires=t2t-backend.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/t2t-training
Environment="PATH=/opt/t2t-training/venv/bin"
EnvironmentFile=/opt/t2t-training/.env
ExecStart=/opt/t2t-training/venv/bin/gunicorn -c gunicorn.conf.py t2t_training_fe:server
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Check Application Logs

```bash
# systemd logs
sudo journalctl -u t2t-training -f

# nginx logs
sudo tail -f /var/log/nginx/t2t-access.log
sudo tail -f /var/log/nginx/t2t-error.log
```

### Health Check

```bash
# Backend health
curl http://localhost:5001/api/health

# Through nginx
curl http://your-domain.com/health
```

## Maintenance

### Update Application

```bash
# Stop service
sudo systemctl stop t2t-training

# Pull updates
cd /opt/t2t-training
git pull  # or copy new files

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations if needed
python3 migrate_db.py

# Restart service
sudo systemctl start t2t-training
```

### Backup Database

```bash
# Create backup directory
sudo mkdir -p /opt/t2t-training/backups

# Backup database
sudo cp /opt/t2t-training/data/t2t.db \
  /opt/t2t-training/backups/t2t_$(date +%Y%m%d_%H%M%S).db

# Automated backup with cron
# Add to crontab: sudo crontab -e
0 2 * * * cp /opt/t2t-training/data/t2t.db /opt/t2t-training/backups/t2t_$(date +\%Y\%m\%d_\%H\%M\%S).db && find /opt/t2t-training/backups -name "t2t_*.db" -mtime +30 -delete
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status t2t-training

# Check logs
sudo journalctl -u t2t-training -n 50

# Check permissions
ls -la /opt/t2t-training/data/
```

### nginx 502 Bad Gateway

```bash
# Check if application is running
sudo systemctl status t2t-training

# Check ports
sudo netstat -tlnp | grep -E '5001|8050'

# Check nginx error log
sudo tail -f /var/log/nginx/t2t-error.log
```

### Database Locked Errors

```bash
# Check file permissions
ls -la /opt/t2t-training/data/t2t.db

# Ensure www-data can write
sudo chown www-data:www-data /opt/t2t-training/data/t2t.db
```

## Security Considerations

1. **Firewall**: Only expose ports 80 and 443. Block direct access to 5001 and 8050.
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw deny 5001/tcp
   sudo ufw deny 8050/tcp
   ```

2. **Database**: Keep database file outside web root and ensure proper permissions.

3. **Environment Variables**: Never commit `.env` file to version control.

4. **Updates**: Regularly update dependencies and system packages.

5. **Backups**: Implement automated database backups.

6. **SSL**: Always use HTTPS in production.

## Performance Tuning

### nginx

```nginx
# Add to nginx.conf
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
```

### Gunicorn

Adjust worker count in `.env`:
```bash
# Formula: (2 x CPU cores) + 1
T2T_WORKERS=9
```

### Database

For high-traffic deployments, consider using PostgreSQL instead of SQLite by updating the database connection code.
