"""
Test for literature search improvements.
Tests the new per-source limit functionality and query format detection.
"""
import unittest
from unittest.mock import Mock, patch
import literature_search


class TestLiteratureSearchImprovements(unittest.TestCase):
    """Test the improvements to literature search functionality"""
    
    def test_query_format_detection(self):
        """Test that WoS advanced queries are properly detected"""
        # WoS advanced queries
        self.assertTrue(literature_search.is_wos_advanced_query("AB=(genomic*)"))
        self.assertTrue(literature_search.is_wos_advanced_query("TS=(machine learning) AND PY=(2020-2024)"))
        self.assertTrue(literature_search.is_wos_advanced_query("TI=(CRISPR) OR AB=(gene editing)"))
        
        # Natural language queries
        self.assertFalse(literature_search.is_wos_advanced_query("machine learning"))
        self.assertFalse(literature_search.is_wos_advanced_query("AI in drug discovery"))
        self.assertFalse(literature_search.is_wos_advanced_query("climate change"))
    
    def test_wos_query_conversion(self):
        """Test that natural language queries are converted to WoS format"""
        # Natural language should be wrapped
        result = literature_search.convert_to_wos_query("machine learning")
        self.assertEqual(result, "TS=(machine learning)")
        
        # Advanced queries should remain unchanged
        advanced_query = "AB=(genomic*) AND PY=(2020-2024)"
        result = literature_search.convert_to_wos_query(advanced_query)
        self.assertEqual(result, advanced_query)
        
        # Test with different default field
        result = literature_search.convert_to_wos_query("AI ethics", default_field="AB")
        self.assertEqual(result, "AB=(AI ethics)")
    
    @patch('literature_search.search_semantic_scholar')
    @patch('literature_search.search_arxiv')
    @patch('literature_search.search_openalex')
    def test_per_source_limits(self, mock_openalex, mock_arxiv, mock_s2):
        """Test that per-source limits are properly applied"""
        # Setup mocks to return empty lists
        mock_s2.return_value = []
        mock_arxiv.return_value = []
        mock_openalex.return_value = []
        
        # Test with custom per-source limits
        per_source_limit = {
            'semantic_scholar': 50,
            'arxiv': 30,
            'openalex': 100
        }
        
        result = literature_search.search_papers(
            query="test query",
            sources=['semantic_scholar', 'arxiv', 'openalex'],
            per_source_limit=per_source_limit,
            enable_query_expansion=False,
            enable_reranking=False
        )
        
        # Verify that each source was called with the correct limit
        mock_s2.assert_called_once()
        self.assertEqual(mock_s2.call_args[1]['limit'], 50)
        
        mock_arxiv.assert_called_once()
        self.assertEqual(mock_arxiv.call_args[1]['limit'], 30)
        
        mock_openalex.assert_called_once()
        self.assertEqual(mock_openalex.call_args[1]['limit'], 100)
    
    @patch('literature_search.search_semantic_scholar')
    @patch('literature_search.search_arxiv')
    def test_default_limits_increased(self, mock_arxiv, mock_s2):
        """Test that default limits have been increased from original values"""
        # Setup mocks to return empty lists
        mock_s2.return_value = []
        mock_arxiv.return_value = []
        
        # Call without specifying per_source_limit (should use defaults)
        result = literature_search.search_papers(
            query="test query",
            sources=['semantic_scholar', 'arxiv'],
            enable_query_expansion=False,
            enable_reranking=False
        )
        
        # Verify that default limits are used and they're higher than original
        mock_s2.assert_called_once()
        s2_limit = mock_s2.call_args[1]['limit']
        self.assertGreaterEqual(s2_limit, 100)  # Should be >= 100 (increased from 40)
        
        mock_arxiv.assert_called_once()
        arxiv_limit = mock_arxiv.call_args[1]['limit']
        self.assertGreaterEqual(arxiv_limit, 50)  # Should be >= 50 (increased from 10)
    
    @patch('literature_search.search_semantic_scholar')
    def test_search_papers_respects_top_k(self, mock_s2):
        """Test that top_k parameter controls how many results are returned"""
        # Create mock papers
        mock_papers = [
            {'title': f'Paper {i}', 'abstract': f'Abstract {i}', 'doi': f'10.1234/{i}'}
            for i in range(50)
        ]
        mock_s2.return_value = mock_papers
        
        # Test with top_k=20
        result = literature_search.search_papers(
            query="test query",
            top_k=20,
            sources=['semantic_scholar'],
            enable_query_expansion=False,
            enable_reranking=False
        )
        
        # Should return exactly 20 results
        self.assertTrue(result['success'])
        self.assertEqual(len(result['papers']), 20)
        self.assertEqual(result['returned'], 20)
    
    def test_get_available_sources(self):
        """Test that available sources are properly reported"""
        sources = literature_search.get_available_sources()
        
        # Should have all four sources
        self.assertIn('semantic_scholar', sources)
        self.assertIn('arxiv', sources)
        self.assertIn('web_of_science', sources)
        self.assertIn('openalex', sources)
        
        # OpenAlex should always be available (no API key needed)
        self.assertTrue(sources['openalex']['available'])
        
        # Each source should have metadata
        for source_name, source_info in sources.items():
            self.assertIn('name', source_info)
            self.assertIn('available', source_info)
            self.assertIn('description', source_info)
            self.assertIn('requires', source_info)


if __name__ == '__main__':
    unittest.main()
