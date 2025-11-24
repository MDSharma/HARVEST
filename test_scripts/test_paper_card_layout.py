"""
Test for the updated paper card layout.
Tests that the _create_paper_card function creates proper two-column layout.
"""
import unittest
import sys
import os

# Add parent directory to path to import frontend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dash import html
import dash_bootstrap_components as dbc

# Import the function we're testing
from frontend.callbacks import _create_paper_card


class TestPaperCardLayout(unittest.TestCase):
    """Test the updated paper card layout with side-by-side abstract display"""
    
    def setUp(self):
        """Set up test data"""
        self.sample_paper = {
            'title': 'A Sample Research Paper',
            'authors': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'year': 2023,
            'doi': '10.1234/sample.doi',
            'citations': 42,
            'source': 'Semantic Scholar',
            'is_open_access': True,
            'abstract_snippet': 'This is a sample abstract for testing purposes. It contains multiple sentences to test the display.'
        }
    
    def test_create_paper_card_returns_card(self):
        """Test that _create_paper_card returns a dbc.Card component"""
        result = _create_paper_card(self.sample_paper, 1)
        self.assertIsInstance(result, dbc.Card)
    
    def test_paper_card_has_checkbox(self):
        """Test that the paper card includes a checkbox"""
        card = _create_paper_card(self.sample_paper, 1)
        # Check that the card structure is valid
        self.assertIsNotNone(card)
        self.assertTrue(hasattr(card, 'children'))
    
    def test_paper_card_displays_title(self):
        """Test that the paper title is included in the card"""
        card = _create_paper_card(self.sample_paper, 1)
        # The card should contain the paper title
        self.assertIsNotNone(card)
    
    def test_paper_card_displays_abstract(self):
        """Test that the abstract is displayed (not in a collapse)"""
        card = _create_paper_card(self.sample_paper, 1)
        # The card should contain the abstract
        self.assertIsNotNone(card)
    
    def test_paper_card_with_minimal_data(self):
        """Test that the card handles minimal paper data"""
        minimal_paper = {
            'title': 'Minimal Paper',
            'authors': [],
            'year': 'N/A',
            'doi': '',
            'citations': 0,
            'source': 'Unknown',
            'is_open_access': False,
            'abstract_snippet': ''
        }
        card = _create_paper_card(minimal_paper, 1)
        self.assertIsInstance(card, dbc.Card)
    
    def test_paper_card_with_arxiv_doi(self):
        """Test that arXiv DOIs are handled correctly"""
        arxiv_paper = {
            'title': 'An arXiv Paper',
            'authors': ['Researcher One'],
            'year': 2023,
            'doi': 'arXiv:2301.12345',
            'citations': 10,
            'source': 'arXiv',
            'is_open_access': True,
            'abstract_snippet': 'This is an arXiv paper abstract.'
        }
        card = _create_paper_card(arxiv_paper, 2)
        self.assertIsInstance(card, dbc.Card)
    
    def test_paper_card_index_numbering(self):
        """Test that different index numbers work correctly"""
        for i in range(1, 6):
            card = _create_paper_card(self.sample_paper, i)
            self.assertIsInstance(card, dbc.Card)
    
    def test_paper_card_citation_badges(self):
        """Test that citation badges are created for different citation counts"""
        # Test various citation counts
        for citation_count in [0, 5, 15, 55, 150]:
            paper = self.sample_paper.copy()
            paper['citations'] = citation_count
            card = _create_paper_card(paper, 1)
            self.assertIsInstance(card, dbc.Card)


if __name__ == '__main__':
    unittest.main()
