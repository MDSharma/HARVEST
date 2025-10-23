#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime
import json

# -----------------------------
# Seed schema from your JSON
# -----------------------------
SCHEMA_JSON = {
    "orl": "opinion role labeling",
    "span-attribute": {
        "Gene": "gene",
        "Regulator": "regulator",
        "Variant": "variant",
        "Protein": "protein",
        "Trait": "phenotype",
        "Enzyme": "enzyme",
        "QTL": "qtl",
        "Coordinates": "coordinates",
        "Metabolite": "metabolite"
    },
    "relation-type": {
        "is_a": "is_a",
        "part_of": "part_of",
        "develops_from": "develops_from",
        "is_related_to": "is_related_to",
        "is_not_related_to": "is_not_related_to",
        "increases": "increases",
        "decreases": "decreases",
        "influences": "influences",
        "does_not_influence": "does_not_influence",
        "may_influence": "may_influence",
        "may_not_influence": "may_not_influence",
        "disrupts": "disrupts",
        "regulates": "regulates",
        "contributes_to": "contributes_to",
        "inhers_in": "inhers_in"
    }
}

def get_conn(db_path: str) -> sqlite3.Connection:
    # New connection per call; autocommit; FK on
    conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str) -> None:
    conn = get_conn(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entity_types (
            name TEXT PRIMARY KEY,
            value TEXT UNIQUE NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS relation_types (
            name TEXT PRIMARY KEY
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            literature_link TEXT,
            contributor_email TEXT,
            created_at TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tuples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sentence_id INTEGER NOT NULL,
            source_entity_name TEXT NOT NULL,
            source_entity_attr TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            sink_entity_name TEXT NOT NULL,
            sink_entity_attr TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY(sentence_id) REFERENCES sentences(id) ON DELETE CASCADE
        );
    """)

    for name, value in SCHEMA_JSON["span-attribute"].items():
        cur.execute("INSERT OR IGNORE INTO entity_types(name, value) VALUES (?, ?);", (name, value))

    for name in SCHEMA_JSON["relation-type"].keys():
        cur.execute("INSERT OR IGNORE INTO relation_types(name) VALUES (?);", (name,))

    conn.close()

def fetch_entity_dropdown_options(db_path: str):
    conn = get_conn(db_path); cur = conn.cursor()
    cur.execute("SELECT name, value FROM entity_types ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    opts = [{"label": name, "value": value} for (name, value) in rows]
    opts.append({"label": "other (type below)", "value": "other"})
    return opts

def fetch_relation_dropdown_options(db_path: str):
    conn = get_conn(db_path); cur = conn.cursor()
    cur.execute("SELECT name FROM relation_types ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    opts = [{"label": name, "value": name} for (name,) in rows]
    opts.append({"label": "other (type below)", "value": "other"})
    return opts

def upsert_sentence(db_path: str, sid, text: str, link: str, email: str = None) -> int:
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    if sid is None or str(sid).strip() == "":
        cur.execute("INSERT INTO sentences(text, literature_link, contributor_email, created_at) VALUES (?, ?, ?, ?);",
                    (text, link, email, now))
        cur.execute("SELECT last_insert_rowid();")
        new_id = cur.fetchone()[0]
        conn.close()
        return new_id

    try:
        sid = int(sid)
    except Exception:
        cur.execute("INSERT INTO sentences(text, literature_link, contributor_email, created_at) VALUES (?, ?, ?, ?);",
                    (text, link, email, now))
        cur.execute("SELECT last_insert_rowid();")
        new_id = cur.fetchone()[0]
        conn.close()
        return new_id

    cur.execute("SELECT COUNT(1) FROM sentences WHERE id=?;", (sid,))
    exists = cur.fetchone()[0] > 0
    if exists:
        cur.execute("UPDATE sentences SET text=?, literature_link=?, contributor_email=? WHERE id=?;", (text, link, email, sid))
        conn.close()
        return sid
    else:
        cur.execute("INSERT INTO sentences(id, text, literature_link, contributor_email, created_at) VALUES (?, ?, ?, ?, ?);",
                    (sid, text, link, email, now))
        conn.close()
        return sid

def insert_tuple_rows(db_path: str, sentence_id: int, rows: list[dict]) -> None:
    conn = get_conn(db_path); cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    q = """INSERT INTO tuples(
        sentence_id, source_entity_name, source_entity_attr,
        relation_type, sink_entity_name, sink_entity_attr, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?);"""
    for r in rows:
        cur.execute(q, (
            sentence_id,
            r["source_entity_name"], r["source_entity_attr"],
            r["relation_type"], r["sink_entity_name"], r["sink_entity_attr"],
            now
        ))
    conn.close()

def add_relation_type(db_path: str, name: str) -> bool:
    if not name or not name.strip():
        return False
    conn = get_conn(db_path); cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO relation_types(name) VALUES (?);", (name.strip(),))
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def add_entity_type(db_path: str, display_name: str, value: str) -> bool:
    if not display_name or not value:
        return False
    conn = get_conn(db_path); cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO entity_types(name, value) VALUES (?, ?);",
                    (display_name.strip(), value.strip()))
        conn.close()
        return True
    except Exception:
        conn.close()
        return False
