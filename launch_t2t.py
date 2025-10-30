#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrapper script to launch both the Text2Trait frontend and backend services.

This script:
1. Starts the backend API server (Flask on port 5001)
2. Starts the frontend UI server (Dash on port 8050)
3. Verifies both services started successfully
4. Handles graceful shutdown on exit
"""

import os
import sys
import time
import signal
import subprocess
import requests
from typing import Optional, Tuple

# Configuration
BACKEND_SCRIPT = "t2t_training_be.py"
FRONTEND_SCRIPT = "t2t_training_fe.py"
BACKEND_PORT = int(os.getenv("T2T_PORT", "5001"))
FRONTEND_PORT = int(os.getenv("PORT", "8050"))
BACKEND_HOST = os.getenv("T2T_HOST", "127.0.0.1")
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "127.0.0.1")

# Load deployment configuration
try:
    from config import DEPLOYMENT_MODE, BACKEND_PUBLIC_URL
except ImportError:
    DEPLOYMENT_MODE = os.getenv("T2T_DEPLOYMENT_MODE", "internal")
    BACKEND_PUBLIC_URL = os.getenv("T2T_BACKEND_PUBLIC_URL", "")

# Override with environment variables if present
DEPLOYMENT_MODE = os.getenv("T2T_DEPLOYMENT_MODE", DEPLOYMENT_MODE)
BACKEND_PUBLIC_URL = os.getenv("T2T_BACKEND_PUBLIC_URL", BACKEND_PUBLIC_URL)

# Health check settings
HEALTH_CHECK_TIMEOUT = 30  # seconds
HEALTH_CHECK_INTERVAL = 1  # seconds

# Process handles
backend_process: Optional[subprocess.Popen] = None
frontend_process: Optional[subprocess.Popen] = None


def validate_deployment_config():
    """Validate deployment configuration and print warnings if needed."""
    if DEPLOYMENT_MODE not in ["internal", "nginx"]:
        print(f"✗ Error: Invalid DEPLOYMENT_MODE: {DEPLOYMENT_MODE}")
        print("  Must be 'internal' or 'nginx'")
        return False

    if DEPLOYMENT_MODE == "nginx":
        # Warn if backend host is localhost in nginx mode
        if BACKEND_HOST in ["127.0.0.1", "localhost"]:
            print()
            print("⚠ Warning: Backend is configured to run on localhost (127.0.0.1)")
            print("  In 'nginx' deployment mode, the backend should be accessible externally.")
            print("  Consider setting T2T_HOST=0.0.0.0 for external access through nginx.")
            print()

    if DEPLOYMENT_MODE == "internal":
        # Recommend localhost binding for internal mode
        if BACKEND_HOST == "0.0.0.0":
            print()
            print("⚠ Warning: Backend is configured to bind to 0.0.0.0 (all interfaces)")
            print("  In 'internal' deployment mode, binding to 127.0.0.1 is more secure")
            print("  as the backend should only accept connections from localhost.")
            print()

    return True


def print_banner():
    """Print a welcome banner."""
    print("=" * 60)
    print("Text2Trait: Training data builder")
    print("=" * 60)
    print(f"Deployment Mode: {DEPLOYMENT_MODE}")
    if DEPLOYMENT_MODE == "nginx":
        print(f"Backend Public URL: {BACKEND_PUBLIC_URL}")
    print("=" * 60)
    print()


def check_port_available(port: int) -> bool:
    """Check if a port is available for use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def wait_for_service(url: str, service_name: str, timeout: int = HEALTH_CHECK_TIMEOUT) -> bool:
    """
    Wait for a service to become available by polling its health endpoint.
    
    Args:
        url: The health check URL to poll
        service_name: Name of the service for logging
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if service is available, False otherwise
    """
    print(f"Waiting for {service_name} to start...", end="", flush=True)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(" ✓")
                return True
        except requests.RequestException:
            pass
        
        print(".", end="", flush=True)
        time.sleep(HEALTH_CHECK_INTERVAL)
    
    print(" ✗")
    return False


def start_backend() -> Tuple[bool, Optional[subprocess.Popen]]:
    """
    Start the backend Flask server.
    
    Returns:
        Tuple of (success: bool, process: Optional[subprocess.Popen])
    """
    print(f"\n[1/2] Starting backend server on {BACKEND_HOST}:{BACKEND_PORT}...")
    
    if not check_port_available(BACKEND_PORT):
        print(f"✗ Error: Port {BACKEND_PORT} is already in use!")
        print(f"  Please stop the process using port {BACKEND_PORT} or set T2T_PORT environment variable.")
        return False, None
    
    try:
        # Start backend process
        process = subprocess.Popen(
            [sys.executable, BACKEND_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait a moment for the process to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"✗ Backend failed to start!")
            print(f"  stdout: {stdout}")
            print(f"  stderr: {stderr}")
            return False, None
        
        # Verify backend is responding
        health_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/health"
        if wait_for_service(health_url, "backend", HEALTH_CHECK_TIMEOUT):
            print(f"✓ Backend is running at http://{BACKEND_HOST}:{BACKEND_PORT}")
            return True, process
        else:
            print(f"✗ Backend did not respond to health check within {HEALTH_CHECK_TIMEOUT} seconds")
            process.terminate()
            return False, None
            
    except FileNotFoundError:
        print(f"✗ Error: Could not find {BACKEND_SCRIPT}")
        return False, None
    except Exception as e:
        print(f"✗ Error starting backend: {e}")
        return False, None


def start_frontend() -> Tuple[bool, Optional[subprocess.Popen]]:
    """
    Start the frontend Dash server.
    
    Returns:
        Tuple of (success: bool, process: Optional[subprocess.Popen])
    """
    print(f"\n[2/2] Starting frontend server on {FRONTEND_HOST}:{FRONTEND_PORT}...")
    
    if not check_port_available(FRONTEND_PORT):
        print(f"✗ Error: Port {FRONTEND_PORT} is already in use!")
        print(f"  Please stop the process using port {FRONTEND_PORT} or set PORT environment variable.")
        return False, None
    
    try:
        # Start frontend process
        process = subprocess.Popen(
            [sys.executable, FRONTEND_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait a moment for the process to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"✗ Frontend failed to start!")
            print(f"  stdout: {stdout}")
            print(f"  stderr: {stderr}")
            return False, None
        
        # Verify frontend is responding (Dash doesn't have a health endpoint, so we check the root)
        frontend_url = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}/"
        if wait_for_service(frontend_url, "frontend", HEALTH_CHECK_TIMEOUT):
            print(f"✓ Frontend is running at http://{FRONTEND_HOST}:{FRONTEND_PORT}")
            return True, process
        else:
            print(f"✗ Frontend did not respond to health check within {HEALTH_CHECK_TIMEOUT} seconds")
            process.terminate()
            return False, None
            
    except FileNotFoundError:
        print(f"✗ Error: Could not find {FRONTEND_SCRIPT}")
        return False, None
    except Exception as e:
        print(f"✗ Error starting frontend: {e}")
        return False, None


def cleanup_processes():
    """Terminate backend and frontend processes gracefully."""
    global backend_process, frontend_process
    
    print("\n\nShutting down services...")
    
    if frontend_process and frontend_process.poll() is None:
        print("  Stopping frontend...", end="", flush=True)
        frontend_process.terminate()
        try:
            frontend_process.wait(timeout=5)
            print(" ✓")
        except subprocess.TimeoutExpired:
            frontend_process.kill()
            print(" ✓ (forced)")
    
    if backend_process and backend_process.poll() is None:
        print("  Stopping backend...", end="", flush=True)
        backend_process.terminate()
        try:
            backend_process.wait(timeout=5)
            print(" ✓")
        except subprocess.TimeoutExpired:
            backend_process.kill()
            print(" ✓ (forced)")
    
    print("\nAll services stopped. Goodbye!")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    cleanup_processes()
    sys.exit(0)


def monitor_processes():
    """Monitor backend and frontend processes, restart if they crash."""
    global backend_process, frontend_process
    
    print("\n" + "=" * 60)
    print("✓ All services started successfully!")
    print("=" * 60)
    print(f"\nAccess the application at: http://{FRONTEND_HOST}:{FRONTEND_PORT}")
    print(f"Backend API available at: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print("\nPress Ctrl+C to stop all services...\n")
    
    try:
        while True:
            # Check if backend is still running
            if backend_process and backend_process.poll() is not None:
                print("✗ Backend process has stopped unexpectedly!")
                stdout, stderr = backend_process.communicate()
                print(f"  stdout: {stdout[-500:]}")  # Last 500 chars
                print(f"  stderr: {stderr[-500:]}")
                cleanup_processes()
                sys.exit(1)
            
            # Check if frontend is still running
            if frontend_process and frontend_process.poll() is not None:
                print("✗ Frontend process has stopped unexpectedly!")
                stdout, stderr = frontend_process.communicate()
                print(f"  stdout: {stdout[-500:]}")  # Last 500 chars
                print(f"  stderr: {stderr[-500:]}")
                cleanup_processes()
                sys.exit(1)
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        cleanup_processes()
        sys.exit(0)


def main():
    """Main entry point for the launcher."""
    global backend_process, frontend_process

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Validate deployment configuration
    if not validate_deployment_config():
        print("\n✗ Configuration validation failed. Please fix the errors above and try again.")
        sys.exit(1)

    print_banner()
    
    # Start backend
    success, backend_process = start_backend()
    if not success:
        print("\n✗ Failed to start backend. Exiting.")
        cleanup_processes()
        sys.exit(1)
    
    # Start frontend
    success, frontend_process = start_frontend()
    if not success:
        print("\n✗ Failed to start frontend. Exiting.")
        cleanup_processes()
        sys.exit(1)
    
    # Monitor processes
    monitor_processes()


if __name__ == "__main__":
    main()
