"""
Test suite to verify Web of Science abstract retrieval fix.

This test validates that the viewField parameter is correctly included
in Web of Science API requests to ensure abstracts are retrieved.
"""
import unittest
from unittest.mock import Mock, patch
import literature_search


class TestWoSAbstractFix(unittest.TestCase):
    """Test that Web of Science API requests include viewField parameter"""
    
    def setUp(self):
        """Clear the LRU cache before each test to avoid cached responses"""
        literature_search.search_web_of_science.cache_clear()
    
    @patch('requests.get')
    @patch('literature_search._get_wos_api_key')
    def test_wos_includes_optionview_parameter(self, mock_get_key, mock_requests):
        """Verify that optionView='FR' is included in API request"""
        
        # Setup
        mock_get_key.return_value = 'test-api-key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResult': {'RecordsFound': 0},
            'Data': {'Records': {'records': {'REC': []}}}
        }
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        # Execute
        result = literature_search.search_web_of_science("test query", limit=10)
        
        # Verify the API was called
        self.assertTrue(mock_requests.called)
        
        # Get the actual call arguments
        call_args = mock_requests.call_args
        
        # Verify viewField parameter is present
        params = call_args[1]['params']
        self.assertIn('optionView', params, 
                     "optionView parameter must be included in WoS API request")
        self.assertEqual(params['optionView'], 'FR',
                        "optionView must be set to 'FR' (Full Record) to retrieve abstracts")
        
        # Verify other required parameters are still present
        self.assertEqual(params['databaseId'], 'WOS')
        self.assertIn('usrQuery', params)
        self.assertEqual(params['count'], 10)
    
    @patch('requests.get')
    @patch('literature_search._get_wos_api_key')
    def test_wos_abstract_extraction(self, mock_get_key, mock_requests):
        """Verify that abstracts are properly extracted from API response"""
        
        # Setup - Mock API response with abstract data
        mock_get_key.return_value = 'test-api-key'
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Create a realistic WoS API response structure with abstract
        mock_response.json.return_value = {
            'QueryResult': {'RecordsFound': 1},
            'Data': {
                'Records': {
                    'records': {
                        'REC': [
                            {
                                'static_data': {
                                    'summary': {
                                        'titles': {
                                            'title': [
                                                {'type': 'item', 'content': 'Test Paper Title'}
                                            ]
                                        },
                                        'names': {
                                            'name': [
                                                {'role': 'author', 'display_name': 'Test Author'}
                                            ]
                                        },
                                        'pub_info': {
                                            'pubyear': '2023'
                                        }
                                    },
                                    'fullrecord_metadata': {
                                        'abstracts': {
                                            'abstract': [
                                                {
                                                    'abstract_text': {
                                                        'p': 'This is a test abstract for validating WoS API integration.'
                                                    }
                                                }
                                            ]
                                        },
                                        'identifiers': {
                                            'identifier': [
                                                {'type': 'doi', 'value': '10.1234/test.doi'}
                                            ]
                                        }
                                    }
                                },
                                'dynamic_data': {
                                    'citation_related': {
                                        'tc_list': {
                                            'silo_tc': [
                                                {'coll_id': 'WOS', 'local_count': '42'}
                                            ]
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        # Execute
        result = literature_search.search_web_of_science("test query", limit=10)
        
        # Verify results
        self.assertEqual(result['total_results'], 1)
        papers = result['papers']
        self.assertEqual(len(papers), 1)
        
        paper = papers[0]
        
        # Verify all expected fields are present
        self.assertEqual(paper['title'], 'Test Paper Title')
        self.assertEqual(paper['abstract'], 'This is a test abstract for validating WoS API integration.')
        self.assertEqual(paper['doi'], '10.1234/test.doi')
        self.assertEqual(paper['year'], 2023)
        self.assertEqual(paper['citations'], 42)
        self.assertEqual(paper['source'], 'Web of Science')
        self.assertIn('Test Author', paper['authors'])
    
    @patch('requests.get')
    @patch('literature_search._get_wos_api_key')
    def test_wos_pagination_includes_optionview(self, mock_get_key, mock_requests):
        """Verify that optionView is included in paginated requests"""
        
        # Setup
        mock_get_key.return_value = 'test-api-key'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResult': {'RecordsFound': 0},
            'Data': {'Records': {'records': {'REC': []}}}
        }
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_requests.return_value = mock_response
        
        # Execute - Request page 2
        result = literature_search.search_web_of_science("test query", limit=20, page=2)
        
        # Verify optionView is still present in paginated request
        call_args = mock_requests.call_args
        params = call_args[1]['params']
        
        self.assertIn('optionView', params)
        self.assertEqual(params['optionView'], 'FR')
        
        # Verify pagination parameters
        # For page 2 with limit 20: firstRecord = (page - 1) * limit + 1 = (2 - 1) * 20 + 1 = 21
        expected_first_record = (2 - 1) * 20 + 1
        self.assertEqual(params['firstRecord'], expected_first_record)
        self.assertEqual(params['count'], 20)


if __name__ == '__main__':
    unittest.main()
