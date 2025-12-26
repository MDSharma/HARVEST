#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for browse fields API endpoints.
"""

import os
import tempfile


def test_browse_fields_endpoints():
    tmp_db = os.path.join(tempfile.mkdtemp(prefix="harvest_test_"), "test.db")
    os.environ["HARVEST_DB"] = tmp_db
    os.environ["HARVEST_ADMIN_EMAILS"] = "admin@example.com"
    os.environ["EMAIL_HASH_SALT"] = "default-insecure-salt-change-me"

    import harvest_store
    harvest_store.init_db(tmp_db)

    import harvest_be
    harvest_be.DB_PATH = tmp_db
    client = harvest_be.app.test_client()

    # GET should return default fields
    resp = client.get("/api/browse-fields")
    assert resp.status_code == 200
    fields = resp.get_json().get("fields")
    assert isinstance(fields, list)
    assert "sentence_id" in fields

    # Unauthenticated POST should fail
    resp = client.post("/api/admin/browse-fields", json={"fields": ["sentence_id"]})
    assert resp.status_code == 403

    # Authenticated POST should succeed and sanitize invalid fields
    resp = client.post(
        "/api/admin/browse-fields",
            json={
                "email": "admin@example.com",
                "password": "irrelevant",
                "fields": ["sentence_id", "bad_field"],
            },
        )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload.get("ok") is True
    assert payload.get("fields") == ["sentence_id"]

    # GET should reflect persisted fields
    resp = client.get("/api/browse-fields")
    assert resp.status_code == 200
    fields = resp.get_json().get("fields")
    assert fields == ["sentence_id"]
