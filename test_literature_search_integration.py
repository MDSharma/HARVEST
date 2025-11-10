"""
Integration test to verify the literature search improvements work end-to-end.
This tests the actual workflow without requiring external API calls.
"""
import unittest
from unittest.mock import Mock, patch
import literature_search


class TestLiteratureSearchIntegration(unittest.TestCase):
    """Integration tests for the complete search workflow with improvements"""
    
    @patch('literature_search.search_semantic_scholar')
    @patch('literature_search.search_arxiv')
    @patch('literature_search.search_web_of_science')
    @patch('literature_search.search_openalex')
    def test_complete_search_workflow_with_custom_limits(self, mock_openalex, mock_wos, mock_arxiv, mock_s2):
        """Test a complete search workflow with custom per-source limits"""
        
        # Setup: Create mock papers from each source
        s2_papers = [
            {'title': f'S2 Paper {i}', 'abstract': f'S2 Abstract {i}', 'doi': f'10.1234/s2-{i}', 
             'authors': ['Author A'], 'year': 2023, 'citations': 10, 'source': 'Semantic Scholar'}
            for i in range(50)
        ]
        arxiv_papers = [
            {'title': f'arXiv Paper {i}', 'abstract': f'arXiv Abstract {i}', 'doi': f'arXiv:{i}',
             'authors': ['Author B'], 'year': 2023, 'citations': 0, 'source': 'arXiv'}
            for i in range(30)
        ]
        wos_papers = [
            {'title': f'WoS Paper {i}', 'abstract': f'WoS Abstract {i}', 'doi': f'WOS:00000{i}',
             'authors': ['Author C'], 'year': 2023, 'citations': 20, 'source': 'Web of Science'}
            for i in range(40)
        ]
        openalex_papers = [
            {'title': f'OpenAlex Paper {i}', 'abstract': f'OpenAlex Abstract {i}', 'doi': f'10.5678/oa-{i}',
             'authors': ['Author D'], 'year': 2023, 'citations': 5, 'source': 'OpenAlex'}
            for i in range(100)
        ]
        
        mock_s2.return_value = s2_papers
        mock_arxiv.return_value = arxiv_papers
        mock_wos.return_value = wos_papers
        mock_openalex.return_value = openalex_papers
        
        # Execute: Run search with custom per-source limits
        per_source_limit = {
            'semantic_scholar': 50,
            'arxiv': 30,
            'web_of_science': 40,
            'openalex': 100
        }
        
        result = literature_search.search_papers(
            query="machine learning in healthcare",
            top_k=30,
            sources=['semantic_scholar', 'arxiv', 'web_of_science', 'openalex'],
            per_source_limit=per_source_limit,
            enable_query_expansion=False,  # Disable for predictable testing
            enable_deduplication=True,
            enable_reranking=False  # Disable to avoid reordering
        )
        
        # Assert: Verify the search succeeded
        self.assertTrue(result['success'])
        
        # Assert: Verify each source was called with correct limits
        mock_s2.assert_called_once()
        self.assertEqual(mock_s2.call_args[1]['limit'], 50)
        
        mock_arxiv.assert_called_once()
        self.assertEqual(mock_arxiv.call_args[1]['limit'], 30)
        
        mock_wos.assert_called_once()
        self.assertEqual(mock_wos.call_args[1]['limit'], 40)
        
        mock_openalex.assert_called_once()
        self.assertEqual(mock_openalex.call_args[1]['limit'], 100)
        
        # Assert: Verify result counts
        total_papers = 50 + 30 + 40 + 100  # 220 total
        self.assertEqual(result['total_found'], total_papers)
        self.assertEqual(result['total_unique'], total_papers)  # No duplicates in our mock data
        self.assertEqual(result['returned'], 30)  # Limited by top_k
        self.assertEqual(len(result['papers']), 30)
        
        # Assert: Verify execution log exists
        self.assertIn('execution_log', result)
        self.assertGreater(len(result['execution_log']), 0)
        
        # Assert: Verify sources were used
        self.assertEqual(set(result['sources_used']), 
                        {'semantic_scholar', 'arxiv', 'web_of_science', 'openalex'})
    
    def test_wos_advanced_query_workflow(self):
        """Test that WoS advanced queries are handled correctly"""
        
        # Test 1: Natural language query should be converted
        natural_query = "machine learning"
        converted = literature_search.convert_to_wos_query(natural_query)
        self.assertEqual(converted, "TS=(machine learning)")
        self.assertFalse(literature_search.is_wos_advanced_query(natural_query))
        
        # Test 2: Advanced query should remain unchanged
        advanced_query = "AB=(genomic*) AND PY=(2020-2024)"
        converted = literature_search.convert_to_wos_query(advanced_query)
        self.assertEqual(converted, advanced_query)
        self.assertTrue(literature_search.is_wos_advanced_query(advanced_query))
        
        # Test 3: Mixed case should work
        mixed_query = "ti=(CRISPR) or ab=(gene editing)"
        self.assertTrue(literature_search.is_wos_advanced_query(mixed_query))
    
    @patch('literature_search.search_semantic_scholar')
    def test_result_display_limits(self, mock_s2):
        """Test that top_k properly limits displayed results"""
        
        # Setup: Create many mock papers
        mock_papers = [
            {'title': f'Paper {i}', 'abstract': f'Abstract {i}', 'doi': f'10.1234/{i}',
             'authors': ['Author'], 'year': 2023, 'citations': i, 'source': 'Semantic Scholar'}
            for i in range(100)
        ]
        mock_s2.return_value = mock_papers
        
        # Test different top_k values
        for top_k in [10, 20, 50, 100]:
            result = literature_search.search_papers(
                query="test query",
                top_k=top_k,
                sources=['semantic_scholar'],
                enable_query_expansion=False,
                enable_reranking=False
            )
            
            self.assertTrue(result['success'])
            self.assertEqual(len(result['papers']), top_k)
            self.assertEqual(result['returned'], top_k)
            self.assertEqual(result['total_found'], 100)
    
    def test_backwards_compatibility(self):
        """Test that old code calling search_papers without new params still works"""
        
        with patch('literature_search.search_semantic_scholar') as mock_s2:
            mock_s2.return_value = [
                {'title': 'Paper', 'abstract': 'Abstract', 'doi': '10.1234/test',
                 'authors': ['Author'], 'year': 2023, 'citations': 10, 'source': 'Semantic Scholar'}
            ]
            
            # Call with old signature (no per_source_limit, default top_k)
            result = literature_search.search_papers(
                query="test query",
                sources=['semantic_scholar']
            )
            
            # Should still work with defaults
            self.assertTrue(result['success'])
            self.assertGreater(len(result['papers']), 0)
            
            # Verify default limit was used (should be >=100 now)
            mock_s2.assert_called_once()
            used_limit = mock_s2.call_args[1]['limit']
            self.assertGreaterEqual(used_limit, 100)


if __name__ == '__main__':
    unittest.main()
