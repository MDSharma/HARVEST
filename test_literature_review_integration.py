#!/usr/bin/env python3
"""
Integration test for Literature Review feature.

This test demonstrates the complete workflow:
1. Check ASReview service health
2. Create a review project
3. Upload papers
4. Start review
5. Screen papers
6. Export results

Usage:
    # Start mock ASReview service in background:
    python3 asreview_mock_service.py &
    
    # Run this test:
    python3 test_literature_review_integration.py
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"
ASREVIEW_URL = "http://localhost:5275"

# Sample papers for testing
SAMPLE_PAPERS = [
    {
        "title": "CRISPR-Cas9 gene editing in crop improvement",
        "abstract": "This study demonstrates the use of CRISPR-Cas9 for targeted gene editing in rice. We achieved 95% editing efficiency and observed improved drought tolerance. Field trials showed 20% yield increase under water stress conditions.",
        "authors": ["Smith J", "Johnson A", "Williams B"],
        "doi": "10.1234/crispr.2024.001",
        "year": 2024
    },
    {
        "title": "A review of gene editing technologies",
        "abstract": "This review article discusses various gene editing technologies including CRISPR, TALENs, and zinc finger nucleases. We compare their efficiency, specificity, and applications in different organisms.",
        "authors": ["Brown C", "Davis D"],
        "doi": "10.1234/review.2024.002",
        "year": 2024
    },
    {
        "title": "Validation of CRISPR editing through RNA-seq",
        "abstract": "We present a comprehensive validation study of CRISPR edits using RNA-seq. Our results confirm on-target editing with minimal off-target effects. The study includes biological replicates and statistical analysis.",
        "authors": ["Garcia M", "Martinez R", "Lopez S"],
        "doi": "10.1234/validation.2024.003",
        "year": 2024
    },
    {
        "title": "Protein structure prediction using AI",
        "abstract": "This paper discusses AlphaFold and other AI methods for protein structure prediction. We present benchmarks and comparisons with experimental structures.",
        "authors": ["Chen L", "Wang X"],
        "doi": "10.1234/protein.2024.004",
        "year": 2024
    },
    {
        "title": "Gene-phenotype associations in Tribolium",
        "abstract": "We report novel gene-phenotype associations in the model organism Tribolium castaneum. RNAi knockdown experiments revealed genes affecting reproduction and stress tolerance.",
        "authors": ["Anderson K", "Thompson P"],
        "doi": "10.1234/tribolium.2024.005",
        "year": 2024
    }
]


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_asreview_health():
    """Check if ASReview service is available."""
    print_section("1. Checking ASReview Service Health")
    
    try:
        response = requests.get(f"{ASREVIEW_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ ASReview service is available")
            print(f"  Version: {data.get('version', 'unknown')}")
            print(f"  Status: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ ASReview service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to ASReview service at {ASREVIEW_URL}")
        print("  Please start the mock service first:")
        print("    python3 asreview_mock_service.py &")
        return False
    except Exception as e:
        print(f"✗ Error checking ASReview health: {e}")
        return False


def check_harvest_health():
    """Check if HARVEST backend is available."""
    print_section("2. Checking HARVEST Backend")
    
    try:
        response = requests.get(f"{BASE_URL}/api/literature-review/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ HARVEST backend is available")
            print(f"  Feature configured: {data.get('configured', False)}")
            print(f"  Service available: {data.get('available', False)}")
            return True
        else:
            print(f"✗ HARVEST returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to HARVEST at {BASE_URL}")
        print("  Please start HARVEST first:")
        print("    python3 launch_harvest.py")
        return False
    except Exception as e:
        print(f"✗ Error checking HARVEST: {e}")
        return False


def test_direct_client():
    """Test the ASReview client directly."""
    print_section("3. Testing ASReview Client")
    
    try:
        from asreview_client import ASReviewClient
        
        # Create client
        client = ASReviewClient(service_url=ASREVIEW_URL)
        print(f"✓ Client created with URL: {ASREVIEW_URL}")
        
        # Check health
        health = client.check_health()
        if health.get('available'):
            print(f"✓ Client can communicate with service")
            print(f"  Version: {health.get('version', 'unknown')}")
        else:
            print(f"✗ Client health check failed: {health.get('error')}")
            return False
        
        # Create project
        print("\n  Creating test project...")
        result = client.create_project(
            project_name="Integration Test Project",
            description="Testing Literature Review integration",
            model_type="nb"
        )
        
        if not result.get('success'):
            print(f"✗ Failed to create project: {result.get('error')}")
            return False
        
        project_id = result.get('project_id')
        print(f"✓ Project created: {project_id}")
        
        # Upload papers
        print(f"\n  Uploading {len(SAMPLE_PAPERS)} sample papers...")
        result = client.upload_papers(project_id, SAMPLE_PAPERS)
        
        if not result.get('success'):
            print(f"✗ Failed to upload papers: {result.get('error')}")
            return False
        
        print(f"✓ Uploaded {result.get('uploaded_count')} papers")
        
        # Start review
        print("\n  Starting review process...")
        result = client.start_review(project_id)
        
        if not result.get('success'):
            print(f"✗ Failed to start review: {result.get('error')}")
            return False
        
        print(f"✓ Review started")
        
        # Get next paper
        print("\n  Getting first paper to review...")
        result = client.get_next_paper(project_id)
        
        if not result.get('success'):
            print(f"✗ Failed to get next paper: {result.get('error')}")
            return False
        
        paper = result.get('paper')
        print(f"✓ Next paper retrieved:")
        print(f"    Title: {paper['title'][:60]}...")
        print(f"    Relevance: {result.get('relevance_score', 0):.2%}")
        
        # Record decision
        print("\n  Recording decision (relevant)...")
        result = client.record_decision(
            project_id,
            paper['paper_id'],
            relevant=True,
            note="Has experimental validation"
        )
        
        if not result.get('success'):
            print(f"✗ Failed to record decision: {result.get('error')}")
            return False
        
        print(f"✓ Decision recorded")
        print(f"  Model updated: {result.get('model_updated', False)}")
        
        # Get progress
        print("\n  Checking progress...")
        result = client.get_progress(project_id)
        
        if not result.get('success'):
            print(f"✗ Failed to get progress: {result.get('error')}")
            return False
        
        print(f"✓ Progress retrieved:")
        print(f"    Total papers: {result.get('total_papers', 0)}")
        print(f"    Reviewed: {result.get('reviewed_papers', 0)}")
        print(f"    Relevant: {result.get('relevant_papers', 0)}")
        print(f"    Progress: {result.get('progress_percent', 0):.1f}%")
        
        # Export results
        print("\n  Exporting results...")
        result = client.export_results(project_id)
        
        if not result.get('success'):
            print(f"✗ Failed to export: {result.get('error')}")
            return False
        
        relevant_count = len(result.get('relevant_papers', []))
        print(f"✓ Results exported:")
        print(f"    Relevant papers: {relevant_count}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error during client test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run integration tests."""
    print("\n" + "=" * 60)
    print("  Literature Review Integration Test")
    print("=" * 60)
    
    # Check ASReview service
    if not check_asreview_health():
        print("\n❌ ASReview service is not available. Exiting.")
        sys.exit(1)
    
    # Test client directly
    if not test_direct_client():
        print("\n❌ Client tests failed. Exiting.")
        sys.exit(1)
    
    # Success
    print_section("✓ All Tests Passed!")
    print()
    print("The Literature Review feature is working correctly.")
    print("You can now:")
    print("  1. Configure ASREVIEW_SERVICE_URL in config.py")
    print("  2. Restart HARVEST")
    print("  3. Use the Literature Review feature in the UI")
    print()


if __name__ == "__main__":
    main()
