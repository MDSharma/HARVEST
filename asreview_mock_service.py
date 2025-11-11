#!/usr/bin/env python3
"""
Mock ASReview Service for Testing

This is a simple mock implementation of the ASReview API for testing
the HARVEST Literature Review integration without requiring a full
ASReview deployment.

Usage:
    python3 asreview_mock_service.py

This will start a simple Flask server on port 5275 that simulates
the ASReview API endpoints used by HARVEST.

Note: This is for testing only. For production use, deploy actual ASReview:
    docker run -p 5275:5275 asreview/asreview:latest
"""

from flask import Flask, jsonify, request
import random
import time
from typing import Dict, List, Any

app = Flask(__name__)

# In-memory storage for testing
projects = {}
project_counter = 0


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'version': '1.0.0-mock',
        'status': 'ok',
        'mock': True
    })


@app.route('/api/projects', methods=['POST'])
def create_project():
    """Create a new ASReview project."""
    global project_counter
    
    data = request.json
    project_name = data.get('project_name', 'Untitled')
    description = data.get('description', '')
    model_type = data.get('model_type', 'nb')
    
    project_counter += 1
    project_id = f'project_{project_counter}'
    
    projects[project_id] = {
        'project_id': project_id,
        'project_name': project_name,
        'description': description,
        'model_type': model_type,
        'papers': [],
        'decisions': {},
        'started': False
    }
    
    return jsonify({
        'project_id': project_id,
        'project_name': project_name
    }), 201


@app.route('/api/projects/<project_id>/data', methods=['POST'])
def upload_papers(project_id):
    """Upload papers to a project."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.json
    papers = data.get('papers', [])
    
    # Assign IDs to papers
    for i, paper in enumerate(papers):
        paper['paper_id'] = paper.get('doi') or f'paper_{len(projects[project_id]["papers"]) + i + 1}'
    
    projects[project_id]['papers'].extend(papers)
    
    return jsonify({
        'message': f'Uploaded {len(papers)} papers',
        'total_papers': len(projects[project_id]['papers'])
    })


@app.route('/api/projects/<project_id>/start', methods=['POST'])
def start_review(project_id):
    """Start the review process."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.json or {}
    prior_relevant = data.get('prior_relevant', [])
    prior_irrelevant = data.get('prior_irrelevant', [])
    
    # Mark prior knowledge
    for paper_id in prior_relevant:
        projects[project_id]['decisions'][paper_id] = {
            'relevant': True,
            'note': 'Prior knowledge',
            'timestamp': time.time()
        }
    
    for paper_id in prior_irrelevant:
        projects[project_id]['decisions'][paper_id] = {
            'relevant': False,
            'note': 'Prior knowledge',
            'timestamp': time.time()
        }
    
    projects[project_id]['started'] = True
    
    return jsonify({
        'message': 'Review started successfully'
    })


@app.route('/api/projects/<project_id>/next', methods=['GET'])
def get_next_paper(project_id):
    """Get next paper to review."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    project = projects[project_id]
    
    # Find unreviewed papers
    unreviewed = [
        p for p in project['papers']
        if p['paper_id'] not in project['decisions']
    ]
    
    if not unreviewed:
        return jsonify({
            'paper': None,
            'message': 'Review complete - no more papers to screen'
        }), 404
    
    # Simulate relevance scoring based on number of decisions
    num_decisions = len(project['decisions'])
    num_relevant = sum(1 for d in project['decisions'].values() if d['relevant'])
    
    # Simulate active learning: early papers get random scores,
    # later papers get scores based on learned pattern
    if num_decisions < 5:
        # Random initially
        next_paper = random.choice(unreviewed)
        relevance_score = random.uniform(0.3, 0.9)
    else:
        # Simulate learning: prioritize papers similar to relevant ones
        # In real ASReview, this would use ML embeddings
        next_paper = unreviewed[0]  # Simplified
        relevance_score = 0.7 + random.uniform(-0.2, 0.2)
    
    return jsonify({
        'paper': {
            'paper_id': next_paper['paper_id'],
            'title': next_paper['title'],
            'abstract': next_paper['abstract'],
            'authors': next_paper['authors'],
            'doi': next_paper.get('doi', ''),
            'year': next_paper.get('year')
        },
        'relevance_score': min(max(relevance_score, 0.0), 1.0),
        'progress': {
            'reviewed': len(project['decisions']),
            'total': len(project['papers']),
            'percent': len(project['decisions']) / len(project['papers']) * 100
        }
    })


@app.route('/api/projects/<project_id>/record', methods=['POST'])
def record_decision(project_id):
    """Record a decision for a paper."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.json
    paper_id = data.get('paper_id')
    relevant = data.get('relevant')
    note = data.get('note', '')
    
    if not paper_id:
        return jsonify({'error': 'paper_id is required'}), 400
    
    if relevant is None:
        return jsonify({'error': 'relevant field is required'}), 400
    
    projects[project_id]['decisions'][paper_id] = {
        'relevant': bool(relevant),
        'note': note,
        'timestamp': time.time()
    }
    
    return jsonify({
        'message': 'Decision recorded',
        'model_updated': True
    })


@app.route('/api/projects/<project_id>/progress', methods=['GET'])
def get_progress(project_id):
    """Get review progress."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    project = projects[project_id]
    total = len(project['papers'])
    reviewed = len(project['decisions'])
    relevant = sum(1 for d in project['decisions'].values() if d['relevant'])
    irrelevant = reviewed - relevant
    
    # Estimate remaining based on current rate
    if reviewed > 0 and relevant > 0:
        # Simple estimation: if we found X relevant in Y reviewed,
        # estimate we'll need to review ~2*total to find most relevant papers
        estimated_remaining = max(0, int(total * 0.3) - reviewed)
    else:
        estimated_remaining = total - reviewed
    
    return jsonify({
        'total_papers': total,
        'reviewed_papers': reviewed,
        'relevant_papers': relevant,
        'irrelevant_papers': irrelevant,
        'progress_percent': reviewed / total * 100 if total > 0 else 0,
        'estimated_remaining': estimated_remaining
    })


@app.route('/api/projects/<project_id>/export', methods=['GET'])
def export_results(project_id):
    """Export review results."""
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404
    
    project = projects[project_id]
    
    relevant_papers = []
    irrelevant_papers = []
    
    for paper in project['papers']:
        paper_id = paper['paper_id']
        if paper_id in project['decisions']:
            decision = project['decisions'][paper_id]
            paper_with_decision = {
                **paper,
                'decision': 'relevant' if decision['relevant'] else 'irrelevant',
                'note': decision['note']
            }
            
            if decision['relevant']:
                relevant_papers.append(paper_with_decision)
            else:
                irrelevant_papers.append(paper_with_decision)
    
    return jsonify({
        'relevant_papers': relevant_papers,
        'irrelevant_papers': irrelevant_papers,
        'format': 'json'
    })


if __name__ == '__main__':
    print("=" * 60)
    print("ASReview Mock Service for HARVEST Testing")
    print("=" * 60)
    print()
    print("This is a mock implementation for testing purposes only.")
    print("For production use, deploy actual ASReview service:")
    print("  docker run -p 5275:5275 asreview/asreview:latest")
    print()
    print("Mock service starting on http://0.0.0.0:5275")
    print("Configure HARVEST with:")
    print("  ASREVIEW_SERVICE_URL = 'http://localhost:5275'")
    print()
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5275, debug=False)
