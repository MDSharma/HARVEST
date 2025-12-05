#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database operations for trait extraction module
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

# Import get_conn from harvest_store to avoid duplication
from harvest_store import get_conn

logger = logging.getLogger(__name__)


# Document operations
def create_document(db_path: str, project_id: Optional[int], file_path: str, 
                   text_content: str, doi: Optional[str] = None, 
                   doi_hash: Optional[str] = None) -> int:
    """Create a new document for extraction"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cur.execute("""
        INSERT INTO trait_documents (project_id, file_path, text_content, doi, doi_hash, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?);
    """, (project_id, file_path, text_content, doi, doi_hash, now, now))
    
    doc_id = cur.lastrowid
    conn.close()
    return doc_id


def get_document(db_path: str, document_id: int) -> Optional[Dict[str, Any]]:
    """Get document by ID"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, project_id, file_path, text_content, doi, doi_hash, status, created_at, updated_at
        FROM trait_documents WHERE id = ?;
    """, (document_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "project_id": row[1],
            "file_path": row[2],
            "text_content": row[3],
            "doi": row[4],
            "doi_hash": row[5],
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8]
        }
    return None


def list_documents(db_path: str, project_id: Optional[int] = None, 
                  status: Optional[str] = None, page: int = 1, 
                  per_page: int = 50) -> Tuple[List[Dict[str, Any]], int]:
    """List documents with pagination"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Build query
    conditions = []
    params = []
    
    if project_id is not None:
        conditions.append("project_id = ?")
        params.append(project_id)
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get total count
    cur.execute(f"SELECT COUNT(*) FROM trait_documents{where_clause};", params)
    total = cur.fetchone()[0]
    
    # Get page of results
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    cur.execute(f"""
        SELECT id, project_id, file_path, text_content, doi, doi_hash, status, created_at, updated_at
        FROM trait_documents{where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
    """, params)
    
    documents = []
    for row in cur.fetchall():
        documents.append({
            "id": row[0],
            "project_id": row[1],
            "file_path": row[2],
            "text_content": row[3][:200] + "..." if len(row[3]) > 200 else row[3],  # Truncate for listing
            "doi": row[4],
            "doi_hash": row[5],
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8]
        })
    
    conn.close()
    return documents, total


def update_document_status(db_path: str, document_id: int, status: str) -> None:
    """Update document status"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cur.execute("""
        UPDATE trait_documents 
        SET status = ?, updated_at = ?
        WHERE id = ?;
    """, (status, now, document_id))
    
    conn.close()


# Extraction job operations
def create_extraction_job(db_path: str, project_id: Optional[int], 
                         document_ids: List[int], model_profile: str, 
                         mode: str, created_by: Optional[str] = None) -> int:
    """Create a new extraction job"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    document_ids_json = json.dumps(document_ids)
    
    cur.execute("""
        INSERT INTO trait_extraction_jobs 
        (project_id, document_ids, model_profile, mode, status, progress, total, created_by, created_at)
        VALUES (?, ?, ?, ?, 'pending', 0, ?, ?, ?);
    """, (project_id, document_ids_json, model_profile, mode, len(document_ids), created_by, now))
    
    job_id = cur.lastrowid
    conn.close()
    return job_id


def get_extraction_job(db_path: str, job_id: int) -> Optional[Dict[str, Any]]:
    """Get extraction job by ID"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, project_id, document_ids, model_profile, mode, status, progress, total,
               error_message, results, created_by, created_at, started_at, completed_at
        FROM trait_extraction_jobs WHERE id = ?;
    """, (job_id,))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "project_id": row[1],
            "document_ids": json.loads(row[2]) if row[2] else [],
            "model_profile": row[3],
            "mode": row[4],
            "status": row[5],
            "progress": row[6],
            "total": row[7],
            "error_message": row[8],
            "results": json.loads(row[9]) if row[9] else {},
            "created_by": row[10],
            "created_at": row[11],
            "started_at": row[12],
            "completed_at": row[13]
        }
    return None


def list_extraction_jobs(db_path: str, project_id: Optional[int] = None, 
                        status: Optional[str] = None, page: int = 1, 
                        per_page: int = 50) -> Tuple[List[Dict[str, Any]], int]:
    """List extraction jobs with pagination"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Build query
    conditions = []
    params = []
    
    if project_id is not None:
        conditions.append("project_id = ?")
        params.append(project_id)
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get total count
    cur.execute(f"SELECT COUNT(*) FROM trait_extraction_jobs{where_clause};", params)
    total = cur.fetchone()[0]
    
    # Get page of results
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    cur.execute(f"""
        SELECT id, project_id, document_ids, model_profile, mode, status, progress, total,
               error_message, results, created_by, created_at, started_at, completed_at
        FROM trait_extraction_jobs{where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
    """, params)
    
    jobs = []
    for row in cur.fetchall():
        jobs.append({
            "id": row[0],
            "project_id": row[1],
            "document_ids": json.loads(row[2]) if row[2] else [],
            "model_profile": row[3],
            "mode": row[4],
            "status": row[5],
            "progress": row[6],
            "total": row[7],
            "error_message": row[8],
            "results": json.loads(row[9]) if row[9] else {},
            "created_by": row[10],
            "created_at": row[11],
            "started_at": row[12],
            "completed_at": row[13]
        })
    
    conn.close()
    return jobs, total


def update_extraction_job(db_path: str, job_id: int, updates: Dict[str, Any]) -> None:
    """Update extraction job fields"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Build update query dynamically
    fields = []
    params = []
    
    for key, value in updates.items():
        if key in ["status", "progress", "error_message", "started_at", "completed_at"]:
            fields.append(f"{key} = ?")
            params.append(value)
        elif key == "results":
            fields.append("results = ?")
            params.append(json.dumps(value))
    
    if fields:
        params.append(job_id)
        query = f"UPDATE trait_extraction_jobs SET {', '.join(fields)} WHERE id = ?;"
        cur.execute(query, params)
    
    conn.close()


# Triple operations (extension of existing triples table)
def insert_extracted_triples(db_path: str, triples: List[Dict[str, Any]]) -> int:
    """Insert extracted triples into the triples table"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    inserted_count = 0
    
    for triple in triples:
        # Ensure sentence exists
        sentence_id = triple.get("sentence_id")
        if not sentence_id:
            # Create a sentence if needed
            cur.execute("""
                INSERT INTO sentences (text, literature_link, doi_hash, created_at)
                VALUES (?, ?, ?, ?);
            """, (triple.get("sentence", ""), triple.get("literature_link", ""), 
                  triple.get("doi_hash"), now))
            sentence_id = cur.lastrowid
        
        # Insert triple
        cur.execute("""
            INSERT INTO triples (
                sentence_id, source_entity_name, source_entity_attr, relation_type,
                sink_entity_name, sink_entity_attr, contributor_email, project_id,
                model_profile, confidence, status, trait_name, trait_value, unit,
                job_id, document_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            sentence_id,
            triple.get("source_entity_name", ""),
            triple.get("source_entity_attr", ""),
            triple.get("relation_type", ""),
            triple.get("sink_entity_name", ""),
            triple.get("sink_entity_attr", ""),
            triple.get("contributor_email"),
            triple.get("project_id"),
            triple.get("model_profile", ""),
            triple.get("confidence", 0.0),
            triple.get("status", "raw"),
            triple.get("trait_name"),
            triple.get("trait_value"),
            triple.get("unit"),
            triple.get("job_id"),
            triple.get("document_id"),
            now,
            now
        ))
        inserted_count += 1
    
    conn.close()
    return inserted_count


def list_extracted_triples(db_path: str, document_id: Optional[int] = None,
                          job_id: Optional[int] = None, status: Optional[str] = None,
                          min_confidence: float = 0.0, page: int = 1,
                          per_page: int = 50) -> Tuple[List[Dict[str, Any]], int]:
    """List extracted triples with filtering"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    
    # Build query
    conditions = ["confidence >= ?"]
    params = [min_confidence]
    
    if document_id is not None:
        conditions.append("document_id = ?")
        params.append(document_id)
    
    if job_id is not None:
        conditions.append("job_id = ?")
        params.append(job_id)
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    where_clause = " WHERE " + " AND ".join(conditions)
    
    # Get total count
    cur.execute(f"SELECT COUNT(*) FROM triples{where_clause};", params)
    total = cur.fetchone()[0]
    
    # Get page of results
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    
    cur.execute(f"""
        SELECT t.id, t.sentence_id, t.source_entity_name, t.source_entity_attr,
               t.relation_type, t.sink_entity_name, t.sink_entity_attr,
               t.model_profile, t.confidence, t.status, t.trait_name, t.trait_value, t.unit,
               t.job_id, t.document_id, t.project_id, t.created_at, s.text as sentence_text
        FROM triples t
        LEFT JOIN sentences s ON t.sentence_id = s.id
        {where_clause}
        ORDER BY t.confidence DESC, t.created_at DESC
        LIMIT ? OFFSET ?;
    """, params)
    
    triples = []
    for row in cur.fetchall():
        triples.append({
            "id": row[0],
            "sentence_id": row[1],
            "source_entity_name": row[2],
            "source_entity_attr": row[3],
            "relation_type": row[4],
            "sink_entity_name": row[5],
            "sink_entity_attr": row[6],
            "model_profile": row[7],
            "confidence": row[8],
            "status": row[9],
            "trait_name": row[10],
            "trait_value": row[11],
            "unit": row[12],
            "job_id": row[13],
            "document_id": row[14],
            "project_id": row[15],
            "created_at": row[16],
            "sentence_text": row[17]
        })
    
    conn.close()
    return triples, total


def update_triple_status(db_path: str, triple_id: int, status: str, 
                        edits: Optional[Dict[str, Any]] = None) -> None:
    """Update triple status and optionally edit fields"""
    conn = get_conn(db_path)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    # Build update query
    fields = ["status = ?", "updated_at = ?"]
    params = [status, now]
    
    if edits:
        for key, value in edits.items():
            if key in ["source_entity_name", "source_entity_attr", "relation_type",
                      "sink_entity_name", "sink_entity_attr", "trait_name", 
                      "trait_value", "unit"]:
                fields.append(f"{key} = ?")
                params.append(value)
    
    params.append(triple_id)
    query = f"UPDATE triples SET {', '.join(fields)} WHERE id = ?;"
    cur.execute(query, params)
    
    conn.close()
