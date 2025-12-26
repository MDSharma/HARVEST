#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for contributor filtering on /api/rows.
"""

import os
import tempfile
import hashlib

def test_contributor_filter_prefix_and_limit():
    # Prepare isolated DB
    tmp_db = os.path.join(tempfile.mkdtemp(prefix="harvest_test_"), "test.db")
    os.environ["HARVEST_DB"] = tmp_db
    os.environ["HARVEST_ADMIN_EMAILS"] = "admin@example.com"
    os.environ["EMAIL_HASH_SALT"] = "default-insecure-salt-change-me"

    import harvest_store
    harvest_store.init_db(tmp_db)

    EMAIL_HASH_SALT = "default-insecure-salt-change-me"
    contributor = "user@example.com"
    hashed = hashlib.sha256((EMAIL_HASH_SALT + contributor).encode()).hexdigest()[:16]

    conn = harvest_store.get_conn(tmp_db)
    cur = conn.cursor()
    # Seed minimal sentence and triples
    # Seed project and sentence to satisfy FKs
    cur.execute("INSERT INTO projects(id, name, doi_list, created_by, created_at) VALUES (1, 'p1', 'doi1', 'admin@example.com', datetime('now'))")
    cur.execute("INSERT INTO projects(id, name, doi_list, created_by, created_at) VALUES (2, 'p2', 'doi2', 'admin@example.com', datetime('now'))")
    cur.execute("INSERT INTO sentences(id, text, literature_link, doi_hash, created_at) VALUES (1, 'txt', NULL, NULL, datetime('now'))")
    cur.execute(
        "INSERT INTO triples(id, sentence_id, source_entity_name, source_entity_attr, relation_type, sink_entity_name, sink_entity_attr, contributor_email, created_at, project_id) VALUES (1, 1, 's', 'a', 'r', 't', 'b', ?, datetime('now'), 1)",
        (contributor,),
    )
    cur.execute(
        "INSERT INTO triples(id, sentence_id, source_entity_name, source_entity_attr, relation_type, sink_entity_name, sink_entity_attr, contributor_email, created_at, project_id) VALUES (2, 1, 's2', 'a2', 'r2', 't2', 'b2', ?, datetime('now'), 1)",
        (contributor,),
    )
    cur.execute(
        "INSERT INTO triples(id, sentence_id, source_entity_name, source_entity_attr, relation_type, sink_entity_name, sink_entity_attr, contributor_email, created_at, project_id) VALUES (3, 1, 'other', 'a', 'r', 't', 'b', 'other@example.com', datetime('now'), 2)"
    )
    conn.commit()
    conn.close()

    import harvest_be
    harvest_be.DB_PATH = tmp_db
    client = harvest_be.app.test_client()

    # Prefix match should include both matching contributor rows
    server_hashed = hashlib.sha256((harvest_be.EMAIL_HASH_SALT + contributor).encode()).hexdigest()[:16]
    resp = client.get(f"/api/rows?triple_contributor={server_hashed[:8]}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert all(row["project_id"] == 1 for row in data)

    # Limit after filtering should reduce result size
    resp = client.get(f"/api/rows?triple_contributor={server_hashed[:8]}&limit=1")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
