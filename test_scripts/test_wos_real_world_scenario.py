#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite to verify the fix for the real-world WoS bug reported in the issue.

This simulates the exact scenario from the bug report where WoS returns XML
in static_data and records were being skipped with "static_data is not a dict".
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import literature_search


class TestWoSRealWorldScenario(unittest.TestCase):
    """Test the exact scenario from the bug report"""
    
    def setUp(self):
        """Clear the LRU cache before each test"""
        literature_search.search_web_of_science.cache_clear()
    
    @patch('requests.get')
    @patch('literature_search._get_wos_api_key')
    def test_wos_query_with_xml_response(self, mock_get_key, mock_requests):
        """
        Simulate the exact error from the bug report:
        - Query: AU=(Sharma M*) AND AB=(natural and sexual*)
        - API returns 7 records with XML in static_data
        - Before fix: All records skipped with "static_data is not a dict (type: str)"
        - After fix: Records should be parsed successfully
        """
        
        mock_get_key.return_value = 'test-api-key'
        
        # Create 7 mock records with XML in static_data (as reported in the bug)
        mock_records = []
        for i in range(7):
            xml_record = f"""
            <records>
                <summary>
                    <titles>
                        <title type="item">Paper {i+1}: Natural and Sexual Selection Study</title>
                    </titles>
                    <names>
                        <name role="author">
                            <display_name>Sharma, M.</display_name>
                            <full_name>Sharma, Mandeep</full_name>
                        </name>
                        <name role="author">
                            <display_name>Co-Author {i+1}</display_name>
                        </name>
                    </names>
                    <pub_info>
                        <pubyear>{2020 + i}</pubyear>
                    </pub_info>
                </summary>
                <fullrecord_metadata>
                    <abstracts>
                        <abstract>
                            <abstract_text>
                                <p>This study examines natural and sexual selection in context {i+1}.</p>
                            </abstract_text>
                        </abstract>
                    </abstracts>
                    <identifiers>
                        <identifier type="doi" value="10.1234/test.{i+1}"/>
                    </identifiers>
                </fullrecord_metadata>
            </records>
            """
            
            mock_records.append({
                'static_data': xml_record,  # XML string (not dict)
                'dynamic_data': {
                    'citation_related': {
                        'tc_list': {
                            'silo_tc': [
                                {'coll_id': 'WOS', 'local_count': str(10 + i)}
                            ]
                        }
                    }
                }
            })
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResult': {'RecordsFound': 7},
            'Data': {
                'Records': {
                    'records': {
                        'REC': mock_records
                    }
                }
            }
        }
        mock_requests.return_value = mock_response
        
        # Execute the query that was failing in the bug report
        query = "AU=(Sharma M*) AND AB=(natural and sexual*)"
        result = literature_search.search_web_of_science(query, limit=100)
        
        # Verify that all 7 records were successfully parsed
        self.assertEqual(result['total_results'], 7, 
                        "Should report 7 total results as in bug report")
        
        papers = result['papers']
        self.assertEqual(len(papers), 7, 
                        "Should successfully parse all 7 records (not skip them)")
        
        # Verify first paper has correct structure
        paper = papers[0]
        self.assertIn('title', paper)
        self.assertIn('Paper 1', paper['title'])
        self.assertIn('abstract', paper)
        self.assertIn('natural and sexual selection', paper['abstract'].lower())
        self.assertEqual(paper['doi'], '10.1234/test.1')
        self.assertEqual(paper['year'], 2020)
        self.assertEqual(paper['citations'], 10)
        self.assertIn('Sharma, M.', paper['authors'])
        
        # Verify all papers were parsed
        for i, paper in enumerate(papers):
            self.assertIsInstance(paper['title'], str)
            self.assertIsInstance(paper['abstract'], str)
            self.assertIsInstance(paper['authors'], list)
            self.assertGreater(len(paper['authors']), 0)
            self.assertIsNotNone(paper['doi'])
            self.assertIsNotNone(paper['year'])
            self.assertGreaterEqual(paper['citations'], 0)
        
        print(f"\n✓ Successfully parsed all {len(papers)} records from WoS XML response")
        print(f"✓ Fix verified: Records are no longer skipped with 'static_data is not a dict' error")
    
    @patch('requests.get')
    @patch('literature_search._get_wos_api_key')
    def test_wos_mixed_response_formats(self, mock_get_key, mock_requests):
        """
        Test that the code handles mixed response formats:
        - Some records with XML in static_data
        - Some records with dict in static_data (legacy format)
        """
        
        mock_get_key.return_value = 'test-api-key'
        
        # Mix of XML and dict formats
        xml_record = """
        <records>
            <summary>
                <titles>
                    <title type="item">XML Format Paper</title>
                </titles>
            </summary>
        </records>
        """
        
        dict_record = {
            'summary': {
                'titles': {
                    'title': [
                        {'type': 'item', 'content': 'Dict Format Paper'}
                    ]
                }
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResult': {'RecordsFound': 2},
            'Data': {
                'Records': {
                    'records': {
                        'REC': [
                            {'static_data': xml_record, 'dynamic_data': {}},
                            {'static_data': dict_record, 'dynamic_data': {}}
                        ]
                    }
                }
            }
        }
        mock_requests.return_value = mock_response
        
        result = literature_search.search_web_of_science("test query")
        
        # Both records should be parsed successfully
        self.assertEqual(len(result['papers']), 2)
        self.assertEqual(result['papers'][0]['title'], 'XML Format Paper')
        self.assertEqual(result['papers'][1]['title'], 'Dict Format Paper')
        
        print("\n✓ Successfully handled mixed XML and dict response formats")


if __name__ == '__main__':
    unittest.main()
