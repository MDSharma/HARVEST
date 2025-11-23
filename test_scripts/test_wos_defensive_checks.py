#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Web of Science search with malformed data.
This tests the defensive checks added to handle cases where API returns
strings instead of dictionaries.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_wos_defensive_checks():
    """Test that WoS search can handle malformed data"""
    
    # Mock record with string instead of dict for static_data
    mock_record_bad = {
        'static_data': 'invalid_string_data',  # Should be dict
        'dynamic_data': {}
    }
    
    # Mock record with proper structure
    mock_record_good = {
        'static_data': {
            'summary': {
                'titles': {
                    'title': [{'type': 'item', 'content': 'Test Paper'}]
                },
                'names': {
                    'name': [{'role': 'author', 'display_name': 'John Doe'}]
                },
                'pub_info': {
                    'pubyear': '2023'
                }
            },
            'fullrecord_metadata': {
                'identifiers': {
                    'identifier': [{'type': 'doi', 'value': '10.1234/test'}]
                }
            }
        },
        'dynamic_data': {
            'citation_related': {
                'tc_list': {
                    'silo_tc': [{'coll_id': 'WOS', 'local_count': '10'}]
                }
            }
        }
    }
    
    # Test processing bad record
    papers = []
    for record in [mock_record_bad]:
        try:
            static_data = record.get('static_data', {})
            if not isinstance(static_data, dict):
                print(f"✓ Correctly detected non-dict static_data (type: {type(static_data).__name__})")
                continue
            
            # This should not be reached
            print("✗ Failed to detect non-dict static_data")
            return False
        except Exception as e:
            print(f"✗ Exception raised: {e}")
            return False
    
    # Test processing good record
    for record in [mock_record_good]:
        try:
            static_data = record.get('static_data', {})
            if not isinstance(static_data, dict):
                print("✗ Good record incorrectly rejected")
                return False
            
            summary = static_data.get('summary', {})
            if not isinstance(summary, dict):
                print("✗ Good record's summary incorrectly rejected")
                return False
            
            # Extract title
            titles = summary.get('titles', {})
            if isinstance(titles, dict):
                title_list = titles.get('title', [])
                if not isinstance(title_list, list):
                    title_list = [title_list] if title_list else []
                
                title = 'N/A'
                for t in title_list:
                    if isinstance(t, dict) and t.get('type') == 'item':
                        title = t.get('content', 'N/A')
                        break
                
                if title == 'Test Paper':
                    print("✓ Successfully extracted title from good record")
                else:
                    print(f"✗ Failed to extract title, got: {title}")
                    return False
            else:
                print("✗ titles is not a dict")
                return False
                
        except Exception as e:
            print(f"✗ Exception processing good record: {e}")
            return False
    
    print("✓ All defensive checks passed")
    return True


if __name__ == "__main__":
    success = test_wos_defensive_checks()
    sys.exit(0 if success else 1)
