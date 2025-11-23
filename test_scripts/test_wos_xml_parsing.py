#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test suite for Web of Science XML parsing.

This test validates that the XML parsing function correctly converts
WoS API XML responses to the expected dictionary structure.

Background:
When viewField='fullRecord' is specified, the WoS API returns XML data
in the 'static_data' field instead of JSON. This test suite verifies
that the _parse_wos_xml_record function properly handles various XML
formats returned by the WoS API, including:
- Simple records with basic metadata
- Records with multiple authors
- Different abstract text formats (nested vs direct)
- Empty and malformed XML

Related to bug fix for issue where records were skipped with error:
"static_data is not a dict (type: str)"
"""

import sys
import os
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import literature_search


class TestWoSXMLParsing(unittest.TestCase):
    """Test Web of Science XML parsing functionality"""
    
    def test_parse_simple_xml_record(self):
        """Test parsing a simple WoS XML record"""
        xml_string = """
        <records>
            <summary>
                <titles>
                    <title type="item">Test Paper Title</title>
                </titles>
                <names>
                    <name role="author">
                        <display_name>John Doe</display_name>
                        <full_name>Doe, John</full_name>
                    </name>
                </names>
                <pub_info>
                    <pubyear>2023</pubyear>
                </pub_info>
            </summary>
            <fullrecord_metadata>
                <abstracts>
                    <abstract>
                        <abstract_text>
                            <p>This is a test abstract.</p>
                        </abstract_text>
                    </abstract>
                </abstracts>
                <identifiers>
                    <identifier type="doi" value="10.1234/test.doi"/>
                </identifiers>
            </fullrecord_metadata>
        </records>
        """
        
        result = literature_search._parse_wos_xml_record(xml_string)
        
        self.assertIsNotNone(result)
        self.assertIn('summary', result)
        self.assertIn('fullrecord_metadata', result)
        
        # Check title
        self.assertIn('titles', result['summary'])
        titles = result['summary']['titles']['title']
        self.assertEqual(len(titles), 1)
        self.assertEqual(titles[0]['type'], 'item')
        self.assertEqual(titles[0]['content'], 'Test Paper Title')
        
        # Check author
        self.assertIn('names', result['summary'])
        names = result['summary']['names']['name']
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0]['role'], 'author')
        self.assertEqual(names[0]['display_name'], 'John Doe')
        
        # Check year
        self.assertIn('pub_info', result['summary'])
        self.assertEqual(result['summary']['pub_info']['pubyear'], '2023')
        
        # Check abstract
        self.assertIn('abstracts', result['fullrecord_metadata'])
        abstracts = result['fullrecord_metadata']['abstracts']['abstract']
        self.assertEqual(len(abstracts), 1)
        self.assertEqual(abstracts[0]['abstract_text']['p'], 'This is a test abstract.')
        
        # Check DOI
        self.assertIn('identifiers', result['fullrecord_metadata'])
        identifiers = result['fullrecord_metadata']['identifiers']['identifier']
        self.assertEqual(len(identifiers), 1)
        self.assertEqual(identifiers[0]['type'], 'doi')
        self.assertEqual(identifiers[0]['value'], '10.1234/test.doi')
    
    def test_parse_xml_with_multiple_authors(self):
        """Test parsing XML with multiple authors"""
        xml_string = """
        <records>
            <summary>
                <titles>
                    <title type="item">Multi-Author Paper</title>
                </titles>
                <names>
                    <name role="author">
                        <display_name>John Doe</display_name>
                    </name>
                    <name role="author">
                        <display_name>Jane Smith</display_name>
                    </name>
                    <name role="author">
                        <display_name>Bob Johnson</display_name>
                    </name>
                </names>
                <pub_info>
                    <pubyear>2024</pubyear>
                </pub_info>
            </summary>
            <fullrecord_metadata>
            </fullrecord_metadata>
        </records>
        """
        
        result = literature_search._parse_wos_xml_record(xml_string)
        
        self.assertIsNotNone(result)
        self.assertIn('names', result['summary'])
        names = result['summary']['names']['name']
        self.assertEqual(len(names), 3)
        self.assertEqual(names[0]['display_name'], 'John Doe')
        self.assertEqual(names[1]['display_name'], 'Jane Smith')
        self.assertEqual(names[2]['display_name'], 'Bob Johnson')
    
    def test_parse_xml_with_direct_abstract_text(self):
        """Test parsing XML where abstract_text is direct text, not nested in p tag"""
        xml_string = """
        <records>
            <summary>
                <titles>
                    <title type="item">Direct Abstract Test</title>
                </titles>
            </summary>
            <fullrecord_metadata>
                <abstracts>
                    <abstract>
                        <abstract_text>This is a direct abstract text without p tag.</abstract_text>
                    </abstract>
                </abstracts>
            </fullrecord_metadata>
        </records>
        """
        
        result = literature_search._parse_wos_xml_record(xml_string)
        
        self.assertIsNotNone(result)
        self.assertIn('abstracts', result['fullrecord_metadata'])
        abstracts = result['fullrecord_metadata']['abstracts']['abstract']
        self.assertEqual(len(abstracts), 1)
        # When abstract_text is direct text, it should be stored as string
        self.assertEqual(abstracts[0]['abstract_text'], 'This is a direct abstract text without p tag.')
    
    def test_parse_invalid_xml(self):
        """Test that invalid XML returns None"""
        xml_string = "<invalid><xml>"
        
        result = literature_search._parse_wos_xml_record(xml_string)
        
        self.assertIsNone(result)
    
    def test_parse_empty_xml(self):
        """Test parsing empty/minimal XML"""
        xml_string = "<records></records>"
        
        result = literature_search._parse_wos_xml_record(xml_string)
        
        self.assertIsNotNone(result)
        self.assertIn('summary', result)
        self.assertIn('fullrecord_metadata', result)
        # Should have empty dicts for summary and fullrecord_metadata
        self.assertEqual(result['summary'], {})
        self.assertEqual(result['fullrecord_metadata'], {})


class TestWoSXMLIntegration(unittest.TestCase):
    """Test integration of XML parsing with search_web_of_science function"""
    
    def test_search_handles_xml_static_data(self):
        """Test that search_web_of_science correctly handles XML in static_data"""
        from unittest.mock import Mock, patch
        
        # Create a mock record with XML in static_data
        xml_record = """
        <records>
            <summary>
                <titles>
                    <title type="item">XML Parsed Paper</title>
                </titles>
                <names>
                    <name role="author">
                        <display_name>Test Author</display_name>
                    </name>
                </names>
                <pub_info>
                    <pubyear>2023</pubyear>
                </pub_info>
            </summary>
            <fullrecord_metadata>
                <abstracts>
                    <abstract>
                        <abstract_text>
                            <p>This abstract was in XML format.</p>
                        </abstract_text>
                    </abstract>
                </abstracts>
                <identifiers>
                    <identifier type="doi" value="10.1234/xml.test"/>
                </identifiers>
            </fullrecord_metadata>
        </records>
        """
        
        # Clear cache
        literature_search.search_web_of_science.cache_clear()
        
        with patch('requests.get') as mock_get, \
             patch('literature_search._get_wos_api_key') as mock_key:
            
            mock_key.return_value = 'test-api-key'
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'QueryResult': {'RecordsFound': 1},
                'Data': {
                    'Records': {
                        'records': {
                            'REC': [
                                {
                                    'static_data': xml_record,  # XML string
                                    'dynamic_data': {
                                        'citation_related': {
                                            'tc_list': {
                                                'silo_tc': [
                                                    {'coll_id': 'WOS', 'local_count': '10'}
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
            mock_get.return_value = mock_response
            
            # Execute search
            result = literature_search.search_web_of_science("test query")
            
            # Verify results
            self.assertIsInstance(result, dict)
            self.assertIn('papers', result)
            self.assertIn('total_results', result)
            self.assertEqual(result['total_results'], 1)
            
            papers = result['papers']
            self.assertEqual(len(papers), 1)
            
            paper = papers[0]
            self.assertEqual(paper['title'], 'XML Parsed Paper')
            self.assertEqual(paper['abstract'], 'This abstract was in XML format.')
            self.assertEqual(paper['doi'], '10.1234/xml.test')
            self.assertEqual(paper['year'], 2023)
            self.assertEqual(paper['citations'], 10)
            self.assertIn('Test Author', paper['authors'])


if __name__ == '__main__':
    unittest.main()
