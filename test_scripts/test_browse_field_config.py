#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for global browse field configuration persistence.
Ensures updates are stored in the shared app_settings table.
"""

import os
import shutil
import tempfile

import harvest_store


def test_browse_field_config_persists_globally():
    """Selected browse fields should persist in the database for all sessions."""
    temp_dir = tempfile.mkdtemp(prefix="harvest_browse_fields_")
    db_path = os.path.join(temp_dir, "test.db")

    try:
        harvest_store.init_db(db_path)

        fields = ["project_id", "sentence", "relation_type"]
        harvest_store.set_browse_visible_fields(db_path, fields)

        loaded = harvest_store.get_browse_visible_fields(db_path)
        assert loaded == fields, f"Expected {fields}, got {loaded}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
