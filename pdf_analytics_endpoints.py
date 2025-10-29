#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Download Analytics API Endpoints
Flask endpoints for querying PDF download statistics and managing sources
"""

from flask import jsonify, request
from typing import Optional
import json

from pdf_download_db import (
    get_download_statistics, get_source_rankings,
    get_config_value, set_config_value, cleanup_old_attempts,
    get_retry_queue_ready, init_pdf_download_db,
    get_pdf_db_connection
)


def init_pdf_analytics_routes(app, verify_admin_func, is_admin_func):
    """
    Initialize PDF analytics routes on the Flask app.

    Args:
        app: Flask application instance
        verify_admin_func: Function to verify admin password (email, password) -> bool
        is_admin_func: Function to check if email is admin (email) -> bool
    """

    def require_admin():
        """Helper to verify admin authentication from request"""
        try:
            payload = request.get_json(force=True, silent=True) or {}
        except:
            payload = {}

        email = (payload.get("email") or "").strip()
        password = payload.get("password") or ""

        if not email or not password:
            return None, (jsonify({"error": "Admin authentication required"}), 401)

        if not (verify_admin_func(email, password) or is_admin_func(email)):
            return None, (jsonify({"error": "Invalid admin credentials"}), 403)

        return email, None

    @app.get("/api/admin/pdf-analytics/statistics")
    def get_pdf_statistics():
        """
        Get overall PDF download statistics.
        Query params:
            - project_id (optional): Filter by project
            - days (optional): Number of days to include (default: 30)
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            project_id = request.args.get('project_id', type=int)
            days = request.args.get('days', default=30, type=int)

            # Limit days to prevent excessive queries
            days = min(days, 365)

            stats = get_download_statistics(project_id, days)

            return jsonify({
                "ok": True,
                "statistics": stats
            })

        except Exception as e:
            print(f"[PDF Analytics] Error getting statistics: {e}")
            return jsonify({"error": "Failed to retrieve statistics"}), 500

    @app.get("/api/admin/pdf-analytics/sources")
    def get_pdf_sources():
        """
        Get all PDF sources with performance rankings.
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            sources = get_source_rankings()

            return jsonify({
                "ok": True,
                "sources": sources
            })

        except Exception as e:
            print(f"[PDF Analytics] Error getting sources: {e}")
            return jsonify({"error": "Failed to retrieve sources"}), 500

    @app.post("/api/admin/pdf-analytics/sources/<source_name>/toggle")
    def toggle_pdf_source(source_name: str):
        """
        Enable or disable a PDF source.
        Expected JSON: {
            "email": "admin@example.com",
            "password": "secret",
            "enabled": true/false
        }
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            payload = request.get_json(force=True, silent=False)
            enabled = payload.get("enabled")

            if enabled is None:
                return jsonify({"error": "Missing 'enabled' field"}), 400

            # Update source in database
            conn = get_pdf_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE sources
                SET enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (1 if enabled else 0, source_name))

            if cursor.rowcount == 0:
                conn.close()
                return jsonify({"error": "Source not found"}), 404

            conn.commit()
            conn.close()

            print(f"[PDF Analytics] {email} {'enabled' if enabled else 'disabled'} source: {source_name}")

            return jsonify({
                "ok": True,
                "message": f"Source {source_name} {'enabled' if enabled else 'disabled'}",
                "source": source_name,
                "enabled": enabled
            })

        except Exception as e:
            print(f"[PDF Analytics] Error toggling source: {e}")
            return jsonify({"error": "Failed to toggle source"}), 500

    @app.post("/api/admin/pdf-analytics/sources/<source_name>/priority")
    def update_source_priority(source_name: str):
        """
        Update the priority of a PDF source.
        Expected JSON: {
            "email": "admin@example.com",
            "password": "secret",
            "priority": 50
        }
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            payload = request.get_json(force=True, silent=False)
            priority = payload.get("priority")

            if priority is None:
                return jsonify({"error": "Missing 'priority' field"}), 400

            if not isinstance(priority, int) or priority < 0:
                return jsonify({"error": "Priority must be a non-negative integer"}), 400

            # Update source priority in database
            conn = get_pdf_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE sources
                SET priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE name = ?
            """, (priority, source_name))

            if cursor.rowcount == 0:
                conn.close()
                return jsonify({"error": "Source not found"}), 404

            conn.commit()
            conn.close()

            print(f"[PDF Analytics] {email} updated priority for {source_name} to {priority}")

            return jsonify({
                "ok": True,
                "message": f"Priority updated for {source_name}",
                "source": source_name,
                "priority": priority
            })

        except Exception as e:
            print(f"[PDF Analytics] Error updating priority: {e}")
            return jsonify({"error": "Failed to update priority"}), 500

    @app.get("/api/admin/pdf-analytics/retry-queue")
    def get_pdf_retry_queue():
        """
        Get DOIs in the retry queue that are ready to retry.
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            retry_items = get_retry_queue_ready()

            return jsonify({
                "ok": True,
                "retry_queue": retry_items,
                "count": len(retry_items)
            })

        except Exception as e:
            print(f"[PDF Analytics] Error getting retry queue: {e}")
            return jsonify({"error": "Failed to retrieve retry queue"}), 500

    @app.get("/api/admin/pdf-analytics/config")
    def get_pdf_config():
        """
        Get PDF download configuration settings.
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            conn = get_pdf_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT key, value, description
                FROM configuration
                ORDER BY key
            """)

            config = []
            for row in cursor.fetchall():
                config.append({
                    "key": row[0],
                    "value": row[1],
                    "description": row[2]
                })

            conn.close()

            return jsonify({
                "ok": True,
                "configuration": config
            })

        except Exception as e:
            print(f"[PDF Analytics] Error getting config: {e}")
            return jsonify({"error": "Failed to retrieve configuration"}), 500

    @app.post("/api/admin/pdf-analytics/config")
    def update_pdf_config():
        """
        Update PDF download configuration.
        Expected JSON: {
            "email": "admin@example.com",
            "password": "secret",
            "key": "retry_delay_minutes",
            "value": "120"
        }
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            payload = request.get_json(force=True, silent=False)
            key = payload.get("key")
            value = payload.get("value")

            if not key or value is None:
                return jsonify({"error": "Missing 'key' or 'value' field"}), 400

            # Update configuration
            success = set_config_value(key, str(value))

            if not success:
                return jsonify({"error": "Failed to update configuration"}), 500

            print(f"[PDF Analytics] {email} updated config: {key} = {value}")

            return jsonify({
                "ok": True,
                "message": f"Configuration updated: {key}",
                "key": key,
                "value": value
            })

        except Exception as e:
            print(f"[PDF Analytics] Error updating config: {e}")
            return jsonify({"error": "Failed to update configuration"}), 500

    @app.post("/api/admin/pdf-analytics/cleanup")
    def cleanup_pdf_attempts():
        """
        Clean up old download attempts from database.
        Expected JSON: {
            "email": "admin@example.com",
            "password": "secret",
            "retention_days": 90
        }
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            payload = request.get_json(force=True, silent=False)
            retention_days = payload.get("retention_days", 90)

            if not isinstance(retention_days, int) or retention_days < 1:
                return jsonify({"error": "retention_days must be a positive integer"}), 400

            deleted = cleanup_old_attempts(retention_days)

            print(f"[PDF Analytics] {email} cleaned up {deleted} old attempts (>{retention_days} days)")

            return jsonify({
                "ok": True,
                "message": f"Cleaned up {deleted} old download attempts",
                "deleted": deleted,
                "retention_days": retention_days
            })

        except Exception as e:
            print(f"[PDF Analytics] Error cleaning up: {e}")
            return jsonify({"error": "Failed to cleanup old attempts"}), 500

    @app.get("/api/admin/pdf-analytics/download-history")
    def get_download_history():
        """
        Get detailed download history with filters.
        Query params:
            - project_id (optional): Filter by project
            - doi (optional): Filter by DOI
            - source (optional): Filter by source
            - success (optional): Filter by success (true/false)
            - limit (optional): Limit results (default: 100, max: 1000)
            - offset (optional): Offset for pagination (default: 0)
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            project_id = request.args.get('project_id', type=int)
            doi = request.args.get('doi', type=str)
            source = request.args.get('source', type=str)
            success = request.args.get('success', type=str)
            limit = min(request.args.get('limit', default=100, type=int), 1000)
            offset = request.args.get('offset', default=0, type=int)

            conn = get_pdf_db_connection()
            cursor = conn.cursor()

            # Build query with filters
            where_clauses = []
            params = []

            if project_id is not None:
                where_clauses.append("project_id = ?")
                params.append(project_id)

            if doi:
                where_clauses.append("doi = ?")
                params.append(doi)

            if source:
                where_clauses.append("source_name = ?")
                params.append(source)

            if success is not None:
                success_val = 1 if success.lower() in ['true', '1', 'yes'] else 0
                where_clauses.append("success = ?")
                params.append(success_val)

            where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get total count
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM download_attempts
                {where_clause}
            """, params)
            total_count = cursor.fetchone()[0]

            # Get paginated results
            params.extend([limit, offset])
            cursor.execute(f"""
                SELECT id, project_id, doi, source_name, success,
                       failure_reason, failure_category, response_time_ms,
                       file_size_bytes, timestamp
                FROM download_attempts
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, params)

            history = []
            for row in cursor.fetchall():
                history.append({
                    "id": row[0],
                    "project_id": row[1],
                    "doi": row[2],
                    "source_name": row[3],
                    "success": bool(row[4]),
                    "failure_reason": row[5],
                    "failure_category": row[6],
                    "response_time_ms": row[7],
                    "file_size_bytes": row[8],
                    "timestamp": row[9]
                })

            conn.close()

            return jsonify({
                "ok": True,
                "history": history,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            })

        except Exception as e:
            print(f"[PDF Analytics] Error getting download history: {e}")
            return jsonify({"error": "Failed to retrieve download history"}), 500

    @app.get("/api/admin/pdf-analytics/export")
    def export_pdf_statistics():
        """
        Export PDF download statistics as CSV.
        Query params:
            - project_id (optional): Filter by project
            - days (optional): Number of days to include (default: 30)
        """
        email, error_response = require_admin()
        if error_response:
            return error_response

        try:
            import csv
            from io import StringIO

            project_id = request.args.get('project_id', type=int)
            days = request.args.get('days', default=30, type=int)

            conn = get_pdf_db_connection()
            cursor = conn.cursor()

            where_clause = "WHERE timestamp >= datetime('now', ?)"
            params = [f"-{days} days"]

            if project_id is not None:
                where_clause += " AND project_id = ?"
                params.append(project_id)

            cursor.execute(f"""
                SELECT project_id, doi, source_name, success,
                       failure_reason, failure_category, response_time_ms,
                       file_size_bytes, timestamp
                FROM download_attempts
                {where_clause}
                ORDER BY timestamp DESC
            """, params)

            # Create CSV
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Project ID', 'DOI', 'Source', 'Success', 'Failure Reason',
                           'Failure Category', 'Response Time (ms)', 'File Size (bytes)', 'Timestamp'])

            for row in cursor.fetchall():
                writer.writerow(row)

            conn.close()

            csv_data = output.getvalue()
            output.close()

            # Return as downloadable file
            from flask import Response
            return Response(
                csv_data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=pdf_download_stats_{days}days.csv'
                }
            )

        except Exception as e:
            print(f"[PDF Analytics] Error exporting statistics: {e}")
            return jsonify({"error": "Failed to export statistics"}), 500

    # Initialize database on first request
    init_pdf_download_db()

    print("[PDF Analytics] Analytics endpoints initialized")
