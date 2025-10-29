#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Download Tracking Database
Separate SQLite database for tracking PDF download attempts, source performance, and analytics
"""

import sqlite3
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import json

PDF_DB_PATH = "pdf_downloads.db"


def init_pdf_download_db(db_path: str = PDF_DB_PATH) -> bool:
    """
    Initialize the PDF download tracking database with all required tables.
    Returns True on success, False on failure.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Table 1: Sources - Configuration for each PDF download source
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                enabled INTEGER DEFAULT 1,
                base_url TEXT,
                requires_auth INTEGER DEFAULT 0,
                timeout INTEGER DEFAULT 30,
                priority INTEGER DEFAULT 100,
                description TEXT,
                requires_library TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 2: Download Attempts - Log every download attempt
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                doi TEXT NOT NULL,
                source_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                failure_reason TEXT,
                failure_category TEXT,
                response_time_ms INTEGER,
                file_size_bytes INTEGER,
                pdf_url TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_name) REFERENCES sources(name)
            )
        """)

        # Table 3: Source Performance - Aggregated metrics per source
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS source_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT UNIQUE NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_response_time_ms REAL DEFAULT 0.0,
                last_success_at TIMESTAMP,
                last_failure_at TIMESTAMP,
                success_rate REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_name) REFERENCES sources(name)
            )
        """)

        # Table 4: Publisher Patterns - Learned URL patterns by publisher
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publisher_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi_prefix TEXT UNIQUE NOT NULL,
                publisher_name TEXT,
                successful_source TEXT,
                url_pattern TEXT,
                success_count INTEGER DEFAULT 1,
                last_success_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (successful_source) REFERENCES sources(name)
            )
        """)

        # Table 5: Retry Queue - DOIs that need retry with scheduling
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS retry_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                doi TEXT NOT NULL,
                failure_category TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                next_retry_at TIMESTAMP,
                last_attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, doi)
            )
        """)

        # Table 6: Configuration - Store runtime configuration and settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_doi ON download_attempts(doi)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_project ON download_attempts(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_source ON download_attempts(source_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON download_attempts(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_publisher_prefix ON publisher_patterns(doi_prefix)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_retry_next ON retry_queue(next_retry_at)")

        # Insert default sources
        default_sources = [
            ("unpaywall", 1, "https://api.unpaywall.org/v2/", 0, 10, 10, "Unpaywall REST API - free open access database", None),
            ("unpywall", 1, None, 0, 10, 20, "Unpywall library fallback for Unpaywall API", "unpywall"),
            ("europe_pmc", 1, "https://www.ebi.ac.uk/europepmc/webservices/rest/", 0, 15, 30, "Europe PMC REST API - biomedical literature", None),
            ("core", 1, "https://api.core.ac.uk/v3/", 0, 15, 40, "CORE.ac.uk REST API - open access research papers", None),
            ("semantic_scholar", 1, "https://api.semanticscholar.org/", 0, 15, 50, "Semantic Scholar API - academic paper metadata and PDFs", None),
            ("scihub", 0, None, 0, 20, 90, "SciHub mirror (optional, disabled by default)", None),
            ("metapub", 0, None, 0, 15, 60, "Metapub - PubMed Central and arXiv", "metapub"),
            ("habanero", 0, None, 0, 15, 70, "Habanero/Crossref - institutional access", "habanero"),
            ("habanero_proxy", 0, None, 1, 20, 80, "Habanero with institutional proxy", "habanero"),
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO sources (name, enabled, base_url, requires_auth, timeout, priority, description, requires_library)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_sources)

        # Initialize performance records for all sources
        cursor.execute("""
            INSERT OR IGNORE INTO source_performance (source_name)
            SELECT name FROM sources
        """)

        # Insert default configuration
        default_config = [
            ("retry_delay_minutes", "60", "Base delay in minutes before retrying failed downloads"),
            ("max_retry_attempts", "3", "Maximum number of retry attempts for temporary failures"),
            ("cleanup_retention_days", "90", "Number of days to keep download attempt history"),
            ("rate_limit_delay_seconds", "1", "Delay between requests to respect API rate limits"),
            ("user_agent_rotation", "1", "Enable rotating User-Agent headers"),
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO configuration (key, value, description)
            VALUES (?, ?, ?)
        """, default_config)

        conn.commit()
        conn.close()

        print(f"[PDF DB] Initialized PDF download tracking database: {db_path}")
        return True

    except Exception as e:
        print(f"[PDF DB] Error initializing database: {e}")
        return False


def get_pdf_db_connection(db_path: str = PDF_DB_PATH) -> sqlite3.Connection:
    """Get a connection to the PDF download tracking database"""
    if not os.path.exists(db_path):
        init_pdf_download_db(db_path)
    return sqlite3.connect(db_path)


def log_download_attempt(
    project_id: int,
    doi: str,
    source_name: str,
    success: bool,
    failure_reason: Optional[str] = None,
    failure_category: Optional[str] = None,
    response_time_ms: Optional[int] = None,
    file_size_bytes: Optional[int] = None,
    pdf_url: Optional[str] = None,
    db_path: str = PDF_DB_PATH
) -> int:
    """
    Log a download attempt to the database.
    Returns the attempt ID, or -1 on error.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO download_attempts
            (project_id, doi, source_name, success, failure_reason, failure_category,
             response_time_ms, file_size_bytes, pdf_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, doi, source_name, success, failure_reason, failure_category,
              response_time_ms, file_size_bytes, pdf_url))

        attempt_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Update aggregated performance metrics
        update_source_performance(source_name, success, response_time_ms, db_path)

        return attempt_id

    except Exception as e:
        print(f"[PDF DB] Error logging download attempt: {e}")
        return -1


def update_source_performance(
    source_name: str,
    success: bool,
    response_time_ms: Optional[int] = None,
    db_path: str = PDF_DB_PATH
) -> bool:
    """
    Update aggregated performance metrics for a source.
    Returns True on success, False on failure.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        # Get current metrics
        cursor.execute("""
            SELECT total_attempts, success_count, failure_count, avg_response_time_ms
            FROM source_performance
            WHERE source_name = ?
        """, (source_name,))

        row = cursor.fetchone()
        if not row:
            # Initialize if not exists
            cursor.execute("""
                INSERT INTO source_performance (source_name, total_attempts, success_count, failure_count)
                VALUES (?, 0, 0, 0)
            """, (source_name,))
            row = (0, 0, 0, 0.0)

        total, success_count, failure_count, avg_time = row

        # Update counts
        total += 1
        if success:
            success_count += 1
        else:
            failure_count += 1

        # Update average response time
        if response_time_ms is not None:
            if avg_time == 0:
                new_avg_time = float(response_time_ms)
            else:
                new_avg_time = ((avg_time * (total - 1)) + response_time_ms) / total
        else:
            new_avg_time = avg_time

        # Calculate success rate
        success_rate = (success_count / total * 100.0) if total > 0 else 0.0

        # Update timestamp based on success/failure
        timestamp_field = "last_success_at" if success else "last_failure_at"

        cursor.execute(f"""
            UPDATE source_performance
            SET total_attempts = ?,
                success_count = ?,
                failure_count = ?,
                avg_response_time_ms = ?,
                success_rate = ?,
                {timestamp_field} = CURRENT_TIMESTAMP,
                last_updated = CURRENT_TIMESTAMP
            WHERE source_name = ?
        """, (total, success_count, failure_count, new_avg_time, success_rate, source_name))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[PDF DB] Error updating source performance: {e}")
        return False


def get_source_rankings(db_path: str = PDF_DB_PATH) -> List[Dict]:
    """
    Get sources ranked by performance (success rate and speed).
    Returns list of source dicts with performance metrics.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.name, s.enabled, s.priority, s.requires_library,
                   sp.success_rate, sp.avg_response_time_ms, sp.total_attempts,
                   sp.success_count, sp.failure_count
            FROM sources s
            LEFT JOIN source_performance sp ON s.name = sp.source_name
            WHERE s.enabled = 1
            ORDER BY sp.success_rate DESC, sp.avg_response_time_ms ASC, s.priority ASC
        """)

        sources = []
        for row in cursor.fetchall():
            sources.append({
                "name": row[0],
                "enabled": row[1],
                "priority": row[2],
                "requires_library": row[3],
                "success_rate": row[4] or 0.0,
                "avg_response_time_ms": row[5] or 0.0,
                "total_attempts": row[6] or 0,
                "success_count": row[7] or 0,
                "failure_count": row[8] or 0
            })

        conn.close()
        return sources

    except Exception as e:
        print(f"[PDF DB] Error getting source rankings: {e}")
        return []


def get_best_source_for_publisher(doi_prefix: str, db_path: str = PDF_DB_PATH) -> Optional[str]:
    """
    Get the best source for a given DOI prefix (publisher) based on historical success.
    Returns source name or None.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT successful_source
            FROM publisher_patterns
            WHERE doi_prefix = ?
            ORDER BY success_count DESC, last_success_at DESC
            LIMIT 1
        """, (doi_prefix,))

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None

    except Exception as e:
        print(f"[PDF DB] Error getting best source for publisher: {e}")
        return None


def record_publisher_success(
    doi_prefix: str,
    publisher_name: str,
    source_name: str,
    url_pattern: Optional[str] = None,
    db_path: str = PDF_DB_PATH
) -> bool:
    """
    Record a successful download for a publisher to learn patterns.
    Returns True on success, False on failure.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        # Check if pattern exists
        cursor.execute("""
            SELECT id, success_count FROM publisher_patterns
            WHERE doi_prefix = ? AND successful_source = ?
        """, (doi_prefix, source_name))

        row = cursor.fetchone()

        if row:
            # Update existing pattern
            cursor.execute("""
                UPDATE publisher_patterns
                SET success_count = success_count + 1,
                    last_success_at = CURRENT_TIMESTAMP,
                    url_pattern = COALESCE(?, url_pattern)
                WHERE id = ?
            """, (url_pattern, row[0]))
        else:
            # Insert new pattern
            cursor.execute("""
                INSERT INTO publisher_patterns (doi_prefix, publisher_name, successful_source, url_pattern)
                VALUES (?, ?, ?, ?)
            """, (doi_prefix, publisher_name, source_name, url_pattern))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[PDF DB] Error recording publisher success: {e}")
        return False


def add_to_retry_queue(
    project_id: int,
    doi: str,
    failure_category: str,
    retry_delay_minutes: int = 60,
    db_path: str = PDF_DB_PATH
) -> bool:
    """
    Add a failed DOI to the retry queue with scheduled retry time.
    Returns True on success, False on failure.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        # Calculate next retry time with exponential backoff
        cursor.execute("""
            SELECT retry_count FROM retry_queue
            WHERE project_id = ? AND doi = ?
        """, (project_id, doi))

        row = cursor.fetchone()
        retry_count = row[0] + 1 if row else 0

        # Exponential backoff: base_delay * 2^retry_count
        delay_minutes = retry_delay_minutes * (2 ** retry_count)
        next_retry = datetime.now() + timedelta(minutes=delay_minutes)

        cursor.execute("""
            INSERT OR REPLACE INTO retry_queue
            (project_id, doi, failure_category, retry_count, next_retry_at, last_attempted_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (project_id, doi, failure_category, retry_count, next_retry))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[PDF DB] Error adding to retry queue: {e}")
        return False


def get_retry_queue_ready(db_path: str = PDF_DB_PATH) -> List[Dict]:
    """
    Get DOIs from retry queue that are ready to retry (next_retry_at <= now).
    Returns list of retry dicts.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_id, doi, failure_category, retry_count
            FROM retry_queue
            WHERE next_retry_at <= CURRENT_TIMESTAMP
            ORDER BY next_retry_at ASC
        """)

        retries = []
        for row in cursor.fetchall():
            retries.append({
                "id": row[0],
                "project_id": row[1],
                "doi": row[2],
                "failure_category": row[3],
                "retry_count": row[4]
            })

        conn.close()
        return retries

    except Exception as e:
        print(f"[PDF DB] Error getting retry queue: {e}")
        return []


def remove_from_retry_queue(project_id: int, doi: str, db_path: str = PDF_DB_PATH) -> bool:
    """
    Remove a DOI from retry queue (after successful download or max retries reached).
    Returns True on success, False on failure.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM retry_queue
            WHERE project_id = ? AND doi = ?
        """, (project_id, doi))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[PDF DB] Error removing from retry queue: {e}")
        return False


def get_download_statistics(
    project_id: Optional[int] = None,
    days: int = 30,
    db_path: str = PDF_DB_PATH
) -> Dict:
    """
    Get download statistics for a project or overall.
    Returns dict with various metrics.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        # Base query
        where_clause = "WHERE timestamp >= datetime('now', ?)"
        params = [f"-{days} days"]

        if project_id is not None:
            where_clause += " AND project_id = ?"
            params.append(project_id)

        # Overall stats
        cursor.execute(f"""
            SELECT
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                AVG(response_time_ms) as avg_response_time,
                COUNT(DISTINCT doi) as unique_dois
            FROM download_attempts
            {where_clause}
        """, params)

        stats_row = cursor.fetchone()

        # Stats by source
        cursor.execute(f"""
            SELECT
                source_name,
                COUNT(*) as attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(response_time_ms) as avg_response_time
            FROM download_attempts
            {where_clause}
            GROUP BY source_name
            ORDER BY successful DESC
        """, params)

        source_stats = []
        for row in cursor.fetchall():
            source_stats.append({
                "source": row[0],
                "attempts": row[1],
                "successful": row[2],
                "success_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                "avg_response_time_ms": row[3] or 0
            })

        # Failure categories
        cursor.execute(f"""
            SELECT
                failure_category,
                COUNT(*) as count
            FROM download_attempts
            {where_clause} AND success = 0 AND failure_category IS NOT NULL
            GROUP BY failure_category
            ORDER BY count DESC
        """, params)

        failure_categories = []
        for row in cursor.fetchall():
            failure_categories.append({
                "category": row[0],
                "count": row[1]
            })

        conn.close()

        total = stats_row[0] or 0
        successful = stats_row[1] or 0

        return {
            "total_attempts": total,
            "successful": successful,
            "failed": stats_row[2] or 0,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_response_time_ms": stats_row[3] or 0,
            "unique_dois": stats_row[4] or 0,
            "by_source": source_stats,
            "failure_categories": failure_categories,
            "period_days": days
        }

    except Exception as e:
        print(f"[PDF DB] Error getting download statistics: {e}")
        return {}


def cleanup_old_attempts(retention_days: int = 90, db_path: str = PDF_DB_PATH) -> int:
    """
    Clean up old download attempts to prevent database bloat.
    Returns number of records deleted.
    """
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM download_attempts
            WHERE timestamp < datetime('now', ?)
        """, (f"-{retention_days} days",))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"[PDF DB] Cleaned up {deleted} old download attempts (older than {retention_days} days)")
        return deleted

    except Exception as e:
        print(f"[PDF DB] Error cleaning up old attempts: {e}")
        return 0


def get_config_value(key: str, default: str = None, db_path: str = PDF_DB_PATH) -> Optional[str]:
    """Get a configuration value from the database"""
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM configuration WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        return row[0] if row else default

    except Exception as e:
        print(f"[PDF DB] Error getting config value: {e}")
        return default


def set_config_value(key: str, value: str, description: str = None, db_path: str = PDF_DB_PATH) -> bool:
    """Set a configuration value in the database"""
    try:
        conn = get_pdf_db_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO configuration (key, value, description, updated_at)
            VALUES (?, ?, COALESCE(?, (SELECT description FROM configuration WHERE key = ?)), CURRENT_TIMESTAMP)
        """, (key, value, description, key))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[PDF DB] Error setting config value: {e}")
        return False


if __name__ == "__main__":
    # Test database initialization
    print("Testing PDF download tracking database...")

    if init_pdf_download_db():
        print("✓ Database initialized successfully")

        # Test logging an attempt
        attempt_id = log_download_attempt(
            project_id=1,
            doi="10.1371/journal.pone.0000001",
            source_name="unpaywall",
            success=True,
            response_time_ms=450,
            file_size_bytes=1024000
        )
        print(f"✓ Logged download attempt: {attempt_id}")

        # Test getting rankings
        rankings = get_source_rankings()
        print(f"✓ Retrieved {len(rankings)} source rankings")
        for source in rankings[:3]:
            print(f"  - {source['name']}: {source['success_rate']:.1f}% success")

        # Test statistics
        stats = get_download_statistics()
        print(f"✓ Statistics: {stats.get('total_attempts', 0)} attempts, {stats.get('success_rate', 0):.1f}% success")

        print("\nDatabase test completed successfully!")
    else:
        print("✗ Database initialization failed")
