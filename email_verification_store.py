#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database operations for email verification.
All operations use the main harvest.db database.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple

from email_config import OTP_CONFIG


def hash_ip(ip_address: str, salt: str = "") -> str:
    """Hash IP address for privacy."""
    if not ip_address:
        return ""
    return hashlib.sha256((salt + ip_address).encode()).hexdigest()[:16]


def init_verification_tables(db_path: str) -> bool:
    """
    Initialize email verification tables in the database.
    
    Args:
        db_path: Path to SQLite database
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            # Email verification codes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_verifications (
                    email TEXT PRIMARY KEY,
                    code_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TEXT,
                    ip_address_hash TEXT
                );
            """)
            
            # Verified email sessions table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verified_sessions (
                    session_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    verified_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip_address_hash TEXT
                );
            """)
            
            # Indexes for performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_verifications_expires 
                ON email_verifications(expires_at);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_verified_sessions_expires 
                ON verified_sessions(expires_at);
            """)
            
            # Rate limiting table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_verification_rate_limit (
                    email TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address_hash TEXT
                );
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_rate_limit_email_time
                ON email_verification_rate_limit(email, timestamp);
            """)
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error initializing verification tables: {e}")
        return False


def check_rate_limit(db_path: str, email: str, ip_address: str = None, salt: str = "") -> Tuple[bool, str]:
    """
    Check if email has exceeded rate limit for code requests.
    
    Args:
        db_path: Path to SQLite database
        email: Email address to check
        ip_address: Optional IP address for additional tracking
        salt: Salt for IP hashing
    
    Returns:
        Tuple of (allowed: bool, message: str)
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            # Get rate limit window
            window_start = datetime.utcnow() - timedelta(
                seconds=OTP_CONFIG["rate_limit_window_seconds"]
            )
            
            # Count codes sent in window
            cur.execute("""
                SELECT COUNT(*) FROM email_verification_rate_limit
                WHERE email = ? AND timestamp > ?
            """, (email.strip().lower(), window_start.isoformat()))
            
            count = cur.fetchone()[0]
            
            if count >= OTP_CONFIG["rate_limit_codes"]:
                return False, f"Rate limit exceeded. Maximum {OTP_CONFIG['rate_limit_codes']} codes per hour."
            
            return True, "Rate limit OK"
            
    except Exception as e:
        print(f"Error checking rate limit: {e}")
        return True, "Rate limit check failed, allowing"


def record_code_request(db_path: str, email: str, ip_address: str = None, salt: str = "") -> bool:
    """Record a code request for rate limiting."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            ip_hash = hash_ip(ip_address, salt) if ip_address else None
            
            cur.execute("""
                INSERT INTO email_verification_rate_limit 
                (email, timestamp, ip_address_hash)
                VALUES (?, ?, ?)
            """, (
                email.strip().lower(),
                datetime.utcnow().isoformat(),
                ip_hash
            ))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error recording code request: {e}")
        return False


def store_verification_code(
    db_path: str, 
    email: str, 
    code_hash: str, 
    expiry_seconds: int = None,
    ip_address: str = None,
    salt: str = ""
) -> bool:
    """Store verification code in database."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            if expiry_seconds is None:
                expiry_seconds = OTP_CONFIG["code_expiry_seconds"]
            
            now = datetime.utcnow()
            expires = now + timedelta(seconds=expiry_seconds)
            
            ip_hash = hash_ip(ip_address, salt) if ip_address else None
            
            cur.execute("""
                INSERT OR REPLACE INTO email_verifications 
                (email, code_hash, created_at, expires_at, attempts, ip_address_hash)
                VALUES (?, ?, ?, ?, 0, ?)
            """, (
                email.strip().lower(),
                code_hash,
                now.isoformat(),
                expires.isoformat(),
                ip_hash
            ))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error storing verification code: {e}")
        return False


def verify_code(
    db_path: str, 
    email: str, 
    code: str,
    verify_func
) -> Dict[str, any]:
    """
    Verify code for email.
    
    Args:
        db_path: Path to database
        email: Email address
        code: Plain text code to verify
        verify_func: Function to verify code hash (from email_service)
    
    Returns:
        Dict with 'valid', 'expired', 'attempts_exceeded', 'message' keys
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            # Get verification record
            cur.execute("""
                SELECT code_hash, expires_at, attempts
                FROM email_verifications
                WHERE email = ?
            """, (email.strip().lower(),))
            
            row = cur.fetchone()
            if not row:
                return {
                    'valid': False,
                    'expired': False,
                    'attempts_exceeded': False,
                    'message': 'No verification code found for this email'
                }
            
            stored_hash, expires_at, attempts = row
            
            # Check expiry
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expires_dt:
                return {
                    'valid': False,
                    'expired': True,
                    'attempts_exceeded': False,
                    'message': 'Verification code has expired'
                }
            
            # Check attempts
            if attempts >= OTP_CONFIG["max_attempts"]:
                return {
                    'valid': False,
                    'expired': False,
                    'attempts_exceeded': True,
                    'message': f'Maximum verification attempts ({OTP_CONFIG["max_attempts"]}) exceeded'
                }
            
            # Increment attempts
            cur.execute("""
                UPDATE email_verifications
                SET attempts = attempts + 1,
                    last_attempt_at = ?
                WHERE email = ?
            """, (datetime.utcnow().isoformat(), email.strip().lower()))
            
            # Verify code
            if verify_func(code, stored_hash):
                # Delete verification record (one-time use)
                cur.execute("DELETE FROM email_verifications WHERE email = ?", 
                           (email.strip().lower(),))
                conn.commit()
                return {
                    'valid': True,
                    'expired': False,
                    'attempts_exceeded': False,
                    'message': 'Code verified successfully'
                }
            else:
                conn.commit()
                remaining = OTP_CONFIG["max_attempts"] - attempts - 1
                return {
                    'valid': False,
                    'expired': False,
                    'attempts_exceeded': False,
                    'message': f'Invalid code. {remaining} attempts remaining'
                }
                
    except Exception as e:
        print(f"Error verifying code: {e}")
        return {
            'valid': False,
            'expired': False,
            'attempts_exceeded': False,
            'message': f'Error verifying code: {str(e)}'
        }


def create_verified_session(
    db_path: str,
    session_id: str,
    email: str,
    expiry_seconds: int = None,
    ip_address: str = None,
    salt: str = ""
) -> bool:
    """Create verified session for email."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            if expiry_seconds is None:
                expiry_seconds = OTP_CONFIG["session_expiry_seconds"]
            
            now = datetime.utcnow()
            expires = now + timedelta(seconds=expiry_seconds)
            
            ip_hash = hash_ip(ip_address, salt) if ip_address else None
            
            cur.execute("""
                INSERT OR REPLACE INTO verified_sessions
                (session_id, email, verified_at, expires_at, ip_address_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                email.strip().lower(),
                now.isoformat(),
                expires.isoformat(),
                ip_hash
            ))
            
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating verified session: {e}")
        return False


def check_verified_session(db_path: str, session_id: str) -> Optional[str]:
    """
    Check if session is verified and not expired.
    Returns email if valid, None otherwise.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            cur.execute("""
                SELECT email, expires_at
                FROM verified_sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cur.fetchone()
            if not row:
                return None
            
            email, expires_at = row
            expires_dt = datetime.fromisoformat(expires_at)
            
            if datetime.utcnow() > expires_dt:
                # Expired, delete it
                cur.execute("DELETE FROM verified_sessions WHERE session_id = ?", 
                           (session_id,))
                conn.commit()
                return None
            
            return email
    except Exception as e:
        print(f"Error checking verified session: {e}")
        return None


def cleanup_expired_records(db_path: str) -> Dict[str, int]:
    """
    Cleanup expired verification codes and sessions.
    Returns count of deleted records.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            now = datetime.utcnow().isoformat()
            
            # Delete expired verification codes
            cur.execute("""
                DELETE FROM email_verifications
                WHERE expires_at < ?
            """, (now,))
            verifications_deleted = cur.rowcount
            
            # Delete expired sessions
            cur.execute("""
                DELETE FROM verified_sessions
                WHERE expires_at < ?
            """, (now,))
            sessions_deleted = cur.rowcount
            
            # Delete old rate limit records
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            cur.execute("""
                DELETE FROM email_verification_rate_limit
                WHERE timestamp < ?
            """, (cutoff,))
            rate_limit_deleted = cur.rowcount
            
            conn.commit()
            
            return {
                'verifications': verifications_deleted,
                'sessions': sessions_deleted,
                'rate_limits': rate_limit_deleted
            }
    except Exception as e:
        print(f"Error cleaning up expired records: {e}")
        return {'verifications': 0, 'sessions': 0, 'rate_limits': 0}
