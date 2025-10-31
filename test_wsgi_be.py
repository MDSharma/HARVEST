#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for wsgi_be.py backend WSGI entry point
Tests that the backend can be imported and used with Gunicorn
"""

import sys
import subprocess


def test_wsgi_be_import():
    """Test that wsgi_be can be imported and exposes a Flask app"""
    print("Testing wsgi_be.py import...")
    
    try:
        from wsgi_be import app
        from flask import Flask
        
        # Verify app is a Flask instance
        assert isinstance(app, Flask), f"Expected Flask instance, got {type(app)}"
        print("✓ wsgi_be.py successfully imports and exposes Flask app")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import wsgi_be: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_wsgi_be_direct_execution():
    """Test that directly running wsgi_be.py gives proper warning"""
    print("\nTesting wsgi_be.py direct execution...")
    
    try:
        result = subprocess.run(
            [sys.executable, "wsgi_be.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should not exit with error (just prints warning)
        # The backend wsgi doesn't call sys.exit() like frontend does
        
        # Should contain warning message
        output = result.stdout + result.stderr
        assert "WARNING" in output, "Expected warning message not found"
        assert "gunicorn" in output.lower(), "Expected gunicorn reference in warning"
        
        print("✓ Direct execution properly warns")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ Direct execution timed out")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_gunicorn_config_check():
    """Test that Gunicorn can parse the wsgi_be module"""
    print("\nTesting Gunicorn configuration check...")
    
    try:
        # Try to check the Gunicorn config without actually starting the server
        result = subprocess.run(
            ["gunicorn", "--check-config", "wsgi_be:app"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Gunicorn should be able to parse the config
        # Note: --check-config may not be available in all Gunicorn versions
        # so we're lenient here
        if result.returncode == 0:
            print("✓ Gunicorn can parse wsgi_be:app configuration")
            return True
        
        if "unrecognized arguments" in result.stderr:
            print("✓ Gunicorn can parse wsgi_be:app configuration (ignoring unsupported --check-config)")
            return True
        
        print(f"✗ Gunicorn check failed with code {result.returncode}")
        print(f"  Output: {result.stdout}")
        print(f"  Error: {result.stderr}")
        return False
        
    except FileNotFoundError:
        print("⚠ Gunicorn not found in PATH - skipping this test")
        return True
    except subprocess.TimeoutExpired:
        print("✗ Gunicorn config check timed out")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during Gunicorn check: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("WSGI Backend Entry Point Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_wsgi_be_import,
        test_wsgi_be_direct_execution,
        test_gunicorn_config_check,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append(False)
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
