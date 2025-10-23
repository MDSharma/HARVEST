"""
Gunicorn configuration file for production deployment.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('T2T_FRONTEND_PORT', '8050')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('T2T_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 5

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = os.environ.get('T2T_ACCESS_LOG', '-')
errorlog = os.environ.get('T2T_ERROR_LOG', '-')
loglevel = os.environ.get('T2T_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 't2t-training'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment if using SSL)
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("Starting Text2Trait Training Data Builder")

def on_reload(server):
    """Called to recycle workers during a reload."""
    print("Reloading workers")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    print(f"Worker {worker.pid} received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    print(f"Worker {worker.pid} received SIGABRT signal")
