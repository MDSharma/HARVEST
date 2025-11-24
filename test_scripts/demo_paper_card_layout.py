"""
Visual demonstration script for the updated paper card layout.
Creates a standalone HTML page showing the new two-column design.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dash import Dash, html
import dash_bootstrap_components as dbc
from frontend.callbacks import _create_paper_card

# Create a simple Dash app for demonstration
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

# Sample papers with varying content
sample_papers = [
    {
        'title': 'Machine Learning Applications in Genomics: A Comprehensive Review',
        'authors': ['Smith, J.', 'Johnson, A.', 'Williams, B.', 'Brown, C.'],
        'year': 2023,
        'doi': '10.1234/ml.genomics.2023',
        'citations': 156,
        'source': 'Semantic Scholar',
        'is_open_access': True,
        'abstract_snippet': 'Machine learning has revolutionized genomic analysis by enabling researchers to process and interpret vast amounts of biological data. This comprehensive review examines the current state of ML applications in genomics, including gene expression analysis, variant calling, and disease prediction. We discuss various algorithms such as deep learning, random forests, and support vector machines, highlighting their strengths and limitations in genomic contexts. Our analysis reveals that while ML methods have achieved remarkable accuracy in many tasks, challenges remain in interpretability and generalization across diverse populations.'
    },
    {
        'title': 'CRISPR-Cas9 Gene Editing: Recent Advances and Future Directions',
        'authors': ['Garcia, M.', 'Chen, L.'],
        'year': 2024,
        'doi': 'arXiv:2401.12345',
        'citations': 42,
        'source': 'arXiv',
        'is_open_access': True,
        'abstract_snippet': 'CRISPR-Cas9 technology has transformed genetic engineering, offering unprecedented precision in genome modification. This paper reviews recent technical improvements in delivery mechanisms, off-target effect reduction, and multiplexed editing strategies. We present case studies demonstrating successful therapeutic applications and discuss ethical considerations surrounding human germline editing.'
    },
    {
        'title': 'Protein Folding Prediction Using AlphaFold2: Validation and Limitations',
        'authors': ['Lee, K.', 'Patel, R.', 'Zhang, W.', 'Kim, S.', 'Anderson, T.'],
        'year': 2023,
        'doi': '10.5678/proteins.alphafold',
        'citations': 8,
        'source': 'Web of Science',
        'is_open_access': False,
        'abstract_snippet': 'AlphaFold2 represents a breakthrough in computational biology, achieving near-experimental accuracy in protein structure prediction. Our study validates AlphaFold2 predictions against crystallographic data for 500 proteins, examining prediction confidence scores and structural domains. Results indicate high accuracy for globular proteins but reduced performance for intrinsically disordered regions and membrane proteins.'
    }
]

# Create paper cards
paper_cards = [_create_paper_card(paper, i+1) for i, paper in enumerate(sample_papers)]

# Build layout
app.layout = dbc.Container([
    html.H1("Literature Search Results - New Two-Column Layout", className="my-4"),
    html.P([
        "This demonstrates the updated paper card layout with abstracts displayed on the right-hand side. ",
        "Users can now see abstracts without clicking, making it easier to scan multiple papers."
    ], className="lead mb-4"),
    html.Hr(),
    html.Div(paper_cards)
], fluid=False, className="py-4")

if __name__ == '__main__':
    print("=" * 80)
    print("Visual Demonstration of Updated Paper Card Layout")
    print("=" * 80)
    print("\nStarting Dash app on http://127.0.0.1:8051")
    print("\nNew Features:")
    print("  - Abstract displayed on the right side (50% width)")
    print("  - Metadata displayed on the left side (50% width)")
    print("  - No collapsible toggle needed")
    print("  - Border separating the two columns")
    print("  - Scrollable abstract with max-height")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 80)
    
    app.run_server(debug=True, host='127.0.0.1', port=8051)
