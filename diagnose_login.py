#!/usr/bin/env python3
"""
Login Diagnostic Tool

This script helps diagnose why the login button isn't working in nginx deployment.
It simulates what happens when a user clicks the login button.
"""

import requests
import sys

def test_backend_directly():
    """Test backend authentication directly"""
    print("=" * 60)
    print("TEST 1: Backend Authentication (Direct)")
    print("=" * 60)
    
    backend_url = "http://127.0.0.1:5001/api/admin/auth"
    
    # Get credentials from command line or use defaults
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        email = input("Enter admin email: ")
        password = input("Enter admin password: ")
    
    print(f"\nTesting: POST {backend_url}")
    print(f"Payload: {{'email': '{email}', 'password': '***'}}")
    
    try:
        response = requests.post(
            backend_url,
            json={"email": email, "password": password},
            timeout=10
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.ok:
            result = response.json()
            if result.get("authenticated"):
                print("\n✓ Authentication SUCCESSFUL")
                print("Backend is working correctly.")
                return True
            else:
                print("\n✗ Authentication FAILED")
                print("Invalid credentials or user not found in database.")
                return False
        else:
            print(f"\n✗ HTTP Error {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n✗ CONNECTION ERROR")
        print("Cannot reach backend at http://127.0.0.1:5001")
        print("Is the backend server running?")
        print("Start with: python3 harvest_be.py")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

def test_through_nginx(nginx_url, email, password):
    """Test authentication through nginx"""
    print("\n" + "=" * 60)
    print("TEST 2: Backend Authentication (Through Nginx)")
    print("=" * 60)
    
    if not nginx_url:
        print("\nSkipping nginx test (no URL provided)")
        print("To test through nginx, run:")
        print("  python3 diagnose_login.py <email> <password> <nginx_url>")
        print("  Example: python3 diagnose_login.py admin@example.com pass123 https://yourdomain.com")
        return None
    
    # Remove trailing slash and construct API URL
    nginx_url = nginx_url.rstrip('/')
    api_url = f"{nginx_url}/harvest/api/admin/auth"
    
    print(f"\nTesting: POST {api_url}")
    print(f"Payload: {{'email': '{email}', 'password': '***'}}")
    
    try:
        response = requests.post(
            api_url,
            json={"email": email, "password": password},
            timeout=10,
            verify=True  # Change to False if using self-signed cert
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.ok:
            result = response.json()
            if result.get("authenticated"):
                print("\n✓ Authentication through nginx SUCCESSFUL")
                print("Nginx routing is working correctly.")
                return True
            else:
                print("\n✗ Authentication FAILED")
                print("Nginx routing works, but credentials are invalid.")
                return False
        else:
            print(f"\n✗ HTTP Error {response.status_code}")
            if response.status_code == 404:
                print("API endpoint not found through nginx.")
                print("Check nginx location blocks for /harvest/api/")
            elif response.status_code == 502 or response.status_code == 504:
                print("Backend unreachable from nginx.")
                print("Check if backend server is running.")
            return False
            
    except requests.exceptions.SSLError:
        print("\n✗ SSL/TLS ERROR")
        print("Cannot verify SSL certificate.")
        print("If using self-signed cert, modify this script to verify=False")
        return False
    except requests.exceptions.ConnectionError:
        print("\n✗ CONNECTION ERROR")
        print(f"Cannot reach {nginx_url}")
        print("Is nginx running? Is the domain correct?")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

def check_frontend_config():
    """Check frontend configuration"""
    print("\n" + "=" * 60)
    print("TEST 3: Frontend Configuration")
    print("=" * 60)
    
    try:
        import sys
        sys.path.insert(0, '.')
        from frontend import API_ADMIN_AUTH, DEPLOYMENT_MODE, URL_BASE_PATHNAME
        
        print(f"\nDEPLOYMENT_MODE: {DEPLOYMENT_MODE}")
        print(f"URL_BASE_PATHNAME: {URL_BASE_PATHNAME}")
        print(f"API_ADMIN_AUTH: {API_ADMIN_AUTH}")
        
        if DEPLOYMENT_MODE == "nginx":
            print("\n✓ Deployment mode is correctly set to 'nginx'")
        else:
            print(f"\n✗ Deployment mode is '{DEPLOYMENT_MODE}', expected 'nginx'")
            print("Set DEPLOYMENT_MODE = 'nginx' in config.py")
            return False
        
        if API_ADMIN_AUTH == "http://127.0.0.1:5001/api/admin/auth":
            print("✓ API_ADMIN_AUTH correctly points to localhost backend")
        else:
            print(f"✗ API_ADMIN_AUTH is '{API_ADMIN_AUTH}'")
            print("Expected: http://127.0.0.1:5001/api/admin/auth")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading frontend config: {e}")
        return False

def print_diagnostics():
    """Print diagnostic information"""
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    print("\nIf backend authentication works but login button doesn't:")
    print("1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)")
    print("2. Check browser console for JavaScript errors (F12)")
    print("3. Check browser Network tab to see if callback is triggered")
    print("4. Check frontend server logs for errors")
    print("5. Verify Dash callback is registered (restart frontend)")
    
    print("\nIf nginx authentication fails:")
    print("1. Verify nginx configuration has /harvest/api/ location block")
    print("2. Verify rewrite rule: rewrite ^/harvest/api/(.*) /api/$1 break;")
    print("3. Check nginx error logs: sudo tail -f /var/log/nginx/error.log")
    print("4. Test nginx config: sudo nginx -t")
    print("5. Reload nginx: sudo systemctl reload nginx")
    
    print("\nFor more help:")
    print("- See docs/TROUBLESHOOTING_LOGIN.md")
    print("- Run: python3 verify_nginx_deployment.py")

def main():
    print("\nHARVEST Login Diagnostic Tool")
    print("=" * 60)
    
    # Get parameters
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        nginx_url = sys.argv[3] if len(sys.argv) >= 4 else None
    else:
        email = None
        password = None
        nginx_url = None
    
    # Run tests
    test1 = test_backend_directly() if email and password else None
    test2 = test_through_nginx(nginx_url, email, password) if nginx_url and email and password else None
    test3 = check_frontend_config()
    
    # Print summary
    print_diagnostics()
    
    # Final verdict
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    
    if test1 and (test2 is None or test2) and test3:
        print("\n✓ All tests passed!")
        print("Backend and configuration are working correctly.")
        print("\nIf login button still doesn't work:")
        print("1. Clear browser cache completely")
        print("2. Check browser console for JavaScript errors")
        print("3. Restart frontend server")
        print("4. Check if button click is registering in Network tab")
    elif test1 is False:
        print("\n✗ Backend authentication failed")
        print("Check admin user credentials and database")
    elif test2 is False:
        print("\n✗ Nginx routing failed")
        print("Check nginx configuration and reload nginx")
    elif test3 is False:
        print("\n✗ Frontend configuration incorrect")
        print("Fix config.py and restart frontend")
    else:
        print("\n? Incomplete testing")
        print("Run with email and password to test authentication")
        print("Usage: python3 diagnose_login.py <email> <password> [nginx_url]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
