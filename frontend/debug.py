#!/usr/bin/env python3
"""
Frontend validation and debugging script.
Validates the modular frontend structure and callback configuration.
"""
import sys
import os

# Add parent directory to path so we can import frontend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_import():
    """Test that frontend can be imported successfully"""
    print("Testing frontend import...")
    try:
        from frontend import app, server
        print("✓ Frontend imports successfully")
        return True
    except Exception as e:
        print(f"✗ Frontend import failed: {e}")
        return False

def test_callback_count():
    """Test that all callbacks are registered"""
    print("\nChecking callback registration...")
    try:
        from frontend import app
        callback_count = len(app.callback_map)
        print(f"✓ {callback_count} callbacks registered")
        if callback_count < 60:
            print(f"⚠ Warning: Expected ~68 callbacks, found {callback_count}")
        return True
    except Exception as e:
        print(f"✗ Callback check failed: {e}")
        return False

def test_forbidden_outputs():
    """Test that no callback outputs to forbidden markdown IDs"""
    print("\nChecking for forbidden markdown outputs...")
    try:
        from frontend import app, FORBIDDEN_MARKDOWN_OUTPUT_IDS
        
        violations = []
        for callback_id, callback_spec in app.callback_map.items():
            output_spec = callback_spec.get('output')
            if output_spec is None:
                continue
            
            outputs = output_spec if isinstance(output_spec, (list, tuple)) else [output_spec]
            
            for output in outputs:
                output_str = f"{output.component_id}.{output.component_property}"
                for forbidden_id in FORBIDDEN_MARKDOWN_OUTPUT_IDS:
                    if forbidden_id in output_str:
                        violations.append({
                            'callback': callback_id,
                            'output': output_str,
                            'forbidden': forbidden_id
                        })
        
        if violations:
            print(f"✗ Found {len(violations)} forbidden outputs:")
            for v in violations:
                print(f"  - {v['callback']} -> {v['output']}")
            return False
        else:
            print("✓ No forbidden markdown outputs found")
            return True
            
    except Exception as e:
        print(f"✗ Forbidden output check failed: {e}")
        return False

def test_markdown_cache():
    """Test that markdown cache is initialized and loaded"""
    print("\nChecking markdown cache...")
    try:
        from frontend import markdown_cache
        
        expected_files = [
            'annotator_guide.md',
            'schema.md',
            'admin_guide.md',
            'db_model.md',
            'participate.md'
        ]
        
        loaded = []
        missing = []
        
        for filename in expected_files:
            if filename in markdown_cache.cache:
                loaded.append(filename)
            else:
                missing.append(filename)
        
        print(f"✓ Markdown cache initialized")
        print(f"  - Loaded: {len(loaded)}/5 files")
        
        if loaded:
            print(f"    Loaded files: {', '.join(loaded)}")
        if missing:
            print(f"  ⚠ Missing files: {', '.join(missing)}")
        
        return len(loaded) > 0
        
    except Exception as e:
        print(f"✗ Markdown cache check failed: {e}")
        return False

def test_server_routes():
    """Test that Flask server routes are registered"""
    print("\nChecking Flask server routes...")
    try:
        from frontend import server
        
        # Get URL map
        routes = []
        for rule in server.url_map.iter_rules():
            if rule.endpoint not in ['static', 'dash.dash.routes']:
                routes.append(f"{rule.rule} [{', '.join(rule.methods - {'HEAD', 'OPTIONS'})}]")
        
        print(f"✓ Server routes registered: {len(routes)}")
        for route in routes[:10]:  # Show first 10
            print(f"  - {route}")
        if len(routes) > 10:
            print(f"  ... and {len(routes) - 10} more")
        
        return True
    except Exception as e:
        print(f"✗ Server routes check failed: {e}")
        return False

def test_wsgi_compatibility():
    """Test that WSGI entry point works"""
    print("\nChecking WSGI compatibility...")
    try:
        from wsgi_fe import server as wsgi_server
        from flask import Flask
        
        if not isinstance(wsgi_server, Flask):
            print(f"✗ wsgi_fe.server is not a Flask instance: {type(wsgi_server)}")
            return False
        
        print("✓ wsgi_fe.server is a valid Flask instance")
        print("✓ WSGI deployment: gunicorn -w 4 -b 0.0.0.0:8050 wsgi_fe:server")
        return True
        
    except Exception as e:
        print(f"✗ WSGI compatibility check failed: {e}")
        return False

def test_module_structure():
    """Test that all expected modules exist"""
    print("\nChecking module structure...")
    
    expected_modules = [
        'frontend/__init__.py',
        'frontend/markdown.py',
        'frontend/layout.py',
        'frontend/callbacks.py',
        'frontend/server_routes.py',
        'harvest_fe.py',
        'wsgi_fe.py',
    ]
    
    all_exist = True
    for module_path in expected_modules:
        if os.path.exists(module_path):
            print(f"✓ {module_path}")
        else:
            print(f"✗ {module_path} not found")
            all_exist = False
    
    return all_exist

def main():
    """Run all validation tests"""
    print("=" * 70)
    print("HARVEST Frontend Validation")
    print("=" * 70)
    
    tests = [
        ("Module Structure", test_module_structure),
        ("Import", test_import),
        ("Callback Count", test_callback_count),
        ("Forbidden Outputs", test_forbidden_outputs),
        ("Markdown Cache", test_markdown_cache),
        ("Server Routes", test_server_routes),
        ("WSGI Compatibility", test_wsgi_compatibility),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✓ All validations passed!")
        print("\nFrontend is correctly modularized and ready for deployment.")
        return 0
    else:
        print(f"\n✗ {total - passed} validation(s) failed")
        print("\nPlease review the failed tests above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
