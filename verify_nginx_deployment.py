#!/usr/bin/env python3
"""
Nginx Deployment Verification Script

This script helps verify that HARVEST is correctly configured for nginx deployment.
Run this script to check common configuration issues.
"""

import os
import sys
import socket
import requests
import json
from pathlib import Path

# ANSI color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{BLUE}{text:^60}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓{RESET} {text}")

def print_warning(text):
    print(f"{YELLOW}⚠{RESET} {text}")

def print_error(text):
    print(f"{RED}✗{RESET} {text}")

def print_info(text):
    print(f"{BLUE}ℹ{RESET} {text}")

def check_config_file():
    """Check if config.py exists and is readable"""
    print_header("Step 1: Configuration File")
    
    config_path = Path("config.py")
    if not config_path.exists():
        print_error("config.py not found!")
        return False
    
    print_success("config.py found")
    
    try:
        with open(config_path) as f:
            config_content = f.read()
        
        # Extract key configuration values
        config = {}
        for line in config_content.split('\n'):
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in ['DEPLOYMENT_MODE', 'URL_BASE_PATHNAME', 'HOST', 'BE_PORT', 'PORT']:
                    # Extract value, handle quotes and comments
                    value = line.split('=', 1)[1].split('#')[0].strip().strip('"').strip("'")
                    config[key] = value
        
        print_info(f"DEPLOYMENT_MODE: {config.get('DEPLOYMENT_MODE', 'NOT SET')}")
        print_info(f"URL_BASE_PATHNAME: {config.get('URL_BASE_PATHNAME', 'NOT SET')}")
        print_info(f"Backend HOST: {config.get('HOST', 'NOT SET')}")
        print_info(f"Backend PORT: {config.get('BE_PORT', 'NOT SET')}")
        print_info(f"Frontend PORT: {config.get('PORT', 'NOT SET')}")
        
        if config.get('DEPLOYMENT_MODE') != 'nginx':
            print_warning("DEPLOYMENT_MODE is not set to 'nginx'")
            print_info("For nginx deployment, set: DEPLOYMENT_MODE = 'nginx'")
            return False
        
        if config.get('URL_BASE_PATHNAME', '/') != '/harvest/':
            print_warning(f"URL_BASE_PATHNAME is '{config.get('URL_BASE_PATHNAME')}', expected '/harvest/'")
        
        return True
        
    except Exception as e:
        print_error(f"Error reading config.py: {e}")
        return False

def check_backend_running():
    """Check if backend server is running"""
    print_header("Step 2: Backend Server")
    
    try:
        import config
        be_port = int(config.BE_PORT)
        host = config.HOST
    except:
        be_port = 5001
        host = "127.0.0.1"
    
    print_info(f"Checking if backend is running on {host}:{be_port}...")
    
    # Check if port is open
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, be_port))
    sock.close()
    
    if result == 0:
        print_success(f"Backend port {be_port} is open")
        
        # Try to reach a backend endpoint
        try:
            response = requests.get(f"http://{host}:{be_port}/api/choices", timeout=5)
            if response.ok:
                print_success("Backend API is responding")
                return True
            else:
                print_warning(f"Backend responded with status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print_error(f"Cannot reach backend API: {e}")
            return False
    else:
        print_error(f"Backend port {be_port} is not accessible")
        print_info("Start the backend with: python3 harvest_be.py")
        return False

def check_frontend_running():
    """Check if frontend server is running"""
    print_header("Step 3: Frontend Server")
    
    try:
        import config
        fe_port = int(config.PORT)
    except:
        fe_port = 8050
    
    print_info(f"Checking if frontend is running on port {fe_port}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("127.0.0.1", fe_port))
    sock.close()
    
    if result == 0:
        print_success(f"Frontend port {fe_port} is open")
        return True
    else:
        print_error(f"Frontend port {fe_port} is not accessible")
        print_info("Start the frontend with: python3 harvest_fe.py")
        return False

def check_nginx_config():
    """Check nginx configuration"""
    print_header("Step 4: Nginx Configuration")
    
    print_info("Checking for nginx configuration files...")
    
    nginx_paths = [
        "/etc/nginx/sites-available/",
        "/etc/nginx/sites-enabled/",
        "/etc/nginx/conf.d/",
        "/usr/local/etc/nginx/servers/"  # macOS
    ]
    
    found_configs = []
    for path in nginx_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if not file.startswith('.'):
                    full_path = os.path.join(path, file)
                    if os.path.isfile(full_path):
                        try:
                            with open(full_path) as f:
                                content = f.read()
                                if 'harvest' in content.lower() or 't2t' in content.lower():
                                    found_configs.append(full_path)
                        except:
                            pass
    
    if found_configs:
        print_success(f"Found {len(found_configs)} nginx config(s) mentioning harvest/t2t:")
        for config in found_configs:
            print_info(f"  - {config}")
        
        # Check for required location blocks
        print_info("\nChecking nginx configuration requirements...")
        
        all_configs = ""
        for config_path in found_configs:
            try:
                with open(config_path) as f:
                    all_configs += f.read() + "\n"
            except:
                pass
        
        has_harvest_location = "location /harvest/" in all_configs
        has_harvest_api_location = "location /harvest/api/" in all_configs
        has_rewrite = "rewrite" in all_configs and "/harvest/api/" in all_configs
        
        if has_harvest_location:
            print_success("Found 'location /harvest/' block")
        else:
            print_error("Missing 'location /harvest/' block")
        
        if has_harvest_api_location:
            print_success("Found 'location /harvest/api/' block")
        else:
            print_error("Missing 'location /harvest/api/' block - THIS IS CRITICAL!")
            print_info("API calls from frontend will fail without this block")
        
        if has_rewrite and has_harvest_api_location:
            print_success("Found rewrite rule in API location block")
        elif has_harvest_api_location:
            print_warning("API location block found but rewrite rule may be missing")
            print_info("Should include: rewrite ^/harvest/api/(.*) /api/$1 break;")
        
        return has_harvest_location and has_harvest_api_location
    else:
        print_warning("No nginx configuration files found for harvest/t2t")
        print_info("This script may not have permission to read nginx configs")
        print_info("Manual verification required")
        return None

def test_api_through_nginx(nginx_url):
    """Test if API is accessible through nginx"""
    print_header("Step 5: Test API Through Nginx")
    
    if not nginx_url:
        print_warning("No nginx URL provided, skipping nginx API test")
        print_info("To test, provide your nginx URL as argument:")
        print_info("  python3 verify_nginx_deployment.py https://yourdomain.com")
        return None
    
    # Remove trailing slash
    nginx_url = nginx_url.rstrip('/')
    
    api_url = f"{nginx_url}/harvest/api/choices"
    print_info(f"Testing: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.ok:
            print_success(f"API accessible through nginx! (Status: {response.status_code})")
            return True
        else:
            print_error(f"API returned error status: {response.status_code}")
            print_info(f"Response: {response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot reach API through nginx: {e}")
        print_info("Possible causes:")
        print_info("  1. Nginx not configured correctly")
        print_info("  2. Backend server not running")
        print_info("  3. Nginx location blocks missing or incorrect")
        return False

def print_summary(results):
    """Print summary of checks"""
    print_header("Summary")
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    print(f"Passed: {GREEN}{passed}{RESET}")
    print(f"Failed: {RED}{failed}{RESET}")
    print(f"Skipped: {YELLOW}{skipped}{RESET}")
    
    if failed > 0:
        print(f"\n{BOLD}Issues Found:{RESET}")
        print("See errors above for details.")
        print("\nRefer to docs/TROUBLESHOOTING_LOGIN.md for detailed troubleshooting steps.")
    elif skipped > 0:
        print(f"\n{BOLD}Some checks were skipped.{RESET}")
        print("Manual verification may be required.")
    else:
        print(f"\n{GREEN}{BOLD}All checks passed!{RESET}")
        print("Configuration appears correct.")

def main():
    print(f"\n{BOLD}HARVEST Nginx Deployment Verification{RESET}")
    print("This script checks common configuration issues.")
    
    # Get nginx URL if provided
    nginx_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    results = {}
    
    # Run checks
    results['config'] = check_config_file()
    results['backend'] = check_backend_running()
    results['frontend'] = check_frontend_running()
    results['nginx_config'] = check_nginx_config()
    results['nginx_api'] = test_api_through_nginx(nginx_url)
    
    # Print summary
    print_summary(results)
    
    # Exit code
    if any(r is False for r in results.values()):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Verification cancelled by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
