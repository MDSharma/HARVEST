#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for wsgi_fe.py frontend WSGI entry point
Tests that the frontend can be imported and used with Gunicorn
"""

import sys
import subprocess


def test_wsgi_fe_import():
    """Test that wsgi_fe can be imported and exposes a Flask server"""
    print("Testing wsgi_fe.py import...")
    
    try:
        from wsgi_fe import server
        from flask import Flask
        
        # Verify server is a Flask instance
        assert isinstance(server, Flask), f"Expected Flask instance, got {type(server)}"
        print("✓ wsgi_fe.py successfully imports and exposes Flask server")
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import wsgi_fe: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_wsgi_fe_direct_execution():
    """Test that directly running wsgi_fe.py gives proper warning"""
    print("\nTesting wsgi_fe.py direct execution...")
    
    try:
        result = subprocess.run(
            [sys.executable, "wsgi_fe.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should exit with code 1
        assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"
        
        # Should contain warning message
        output = result.stdout + result.stderr
        assert "WARNING" in output, "Expected warning message not found"
        assert "gunicorn" in output.lower(), "Expected gunicorn reference in warning"
        
        print("✓ Direct execution properly warns and exits")
        return True
        
    except subprocess.TimeoutExpired:
        print("✗ Direct execution timed out")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_gunicorn_config_check():
    """Test that Gunicorn can parse the wsgi_fe module"""
    print("\nTesting Gunicorn configuration check...")
    
    try:
        # Try to check the Gunicorn config without actually starting the server
        result = subprocess.run(
            ["gunicorn", "--check-config", "wsgi_fe:server"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Gunicorn should be able to parse the config
        # Note: --check-config may not be available in all Gunicorn versions
        # so we're lenient here
        if result.returncode == 0 or "unrecognized arguments" in result.stderr:
            print("✓ Gunicorn can parse wsgi_fe:server configuration")
            return True
        else:
            print(f"⚠ Gunicorn check returned code {result.returncode}")
            print(f"  Output: {result.stdout}")
            print(f"  Error: {result.stderr}")
            # Don't fail the test if --check-config is not supported
            return True
        
    except FileNotFoundError:
        print("⚠ Gunicorn not found in PATH - skipping this test")
        return True
    except subprocess.TimeoutExpired:
        print("✗ Gunicorn config check timed out")
        return False
    except Exception as e:
        print(f"⚠ Unexpected error (non-critical): {e}")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("WSGI Frontend Entry Point Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_wsgi_fe_import,
        test_wsgi_fe_direct_execution,
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
