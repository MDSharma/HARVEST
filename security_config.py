#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Configuration for HARVEST Email Verification
Additional security settings and utilities
"""

import os
import stat
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Security Settings
# ============================================================================

# Session Security
SESSION_BINDING_ENABLED = os.getenv("SESSION_BINDING_ENABLED", "false").lower() == "true"
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
SECURITY_MONITORING_ENABLED = os.getenv("SECURITY_MONITORING_ENABLED", "true").lower() == "true"

# Debug Mode (affects error message verbosity)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Database Security
DATABASE_FILE_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR  # 600 (owner read/write only)


def secure_database_file(db_path: str) -> bool:
    """
    Set secure permissions on database file.
    
    Args:
        db_path: Path to database file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(db_path):
            os.chmod(db_path, DATABASE_FILE_PERMISSIONS)
            logger.info(f"Secured database file permissions: {db_path}")
            return True
        else:
            logger.warning(f"Database file does not exist: {db_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to set database permissions: {e}")
        return False


def get_generic_error_message(detailed_error: str, context: str = "") -> str:
    """
    Return appropriate error message based on debug mode.
    
    Args:
        detailed_error: Detailed error message for debugging
        context: Context description for logging
    
    Returns:
        Generic or detailed error message based on DEBUG_MODE
    """
    if DEBUG_MODE:
        return detailed_error
    else:
        logger.error(f"{context}: {detailed_error}")
        return "Service temporarily unavailable. Please try again later."


# ============================================================================
# Security Event Logging
# ============================================================================

class SecurityEventLogger:
    """Log security-relevant events for monitoring and auditing."""
    
    @staticmethod
    def log_otp_request(email: str, ip_address: str, success: bool):
        """Log OTP code request event."""
        if SECURITY_MONITORING_ENABLED:
            masked_email = f"{email[:3]}***@{email.split('@')[1] if '@' in email else 'unknown'}"
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"OTP_REQUEST|{status}|email={masked_email}|ip={ip_address[:8]}***")
    
    @staticmethod
    def log_verification_attempt(email: str, ip_address: str, success: bool, remaining_attempts: int = None):
        """Log verification attempt event."""
        if SECURITY_MONITORING_ENABLED:
            masked_email = f"{email[:3]}***@{email.split('@')[1] if '@' in email else 'unknown'}"
            status = "SUCCESS" if success else "FAILED"
            attempts_info = f"|remaining={remaining_attempts}" if remaining_attempts is not None else ""
            logger.info(f"VERIFICATION_ATTEMPT|{status}|email={masked_email}|ip={ip_address[:8]}***{attempts_info}")
    
    @staticmethod
    def log_rate_limit_exceeded(email: str, ip_address: str, limit_type: str = "code_request"):
        """Log rate limit exceeded event."""
        if SECURITY_MONITORING_ENABLED:
            masked_email = f"{email[:3]}***@{email.split('@')[1] if '@' in email else 'unknown'}"
            logger.warning(f"RATE_LIMIT_EXCEEDED|type={limit_type}|email={masked_email}|ip={ip_address[:8]}***")
    
    @staticmethod
    def log_session_created(email: str, session_id: str, expiry_hours: int):
        """Log session creation event."""
        if SECURITY_MONITORING_ENABLED:
            masked_email = f"{email[:3]}***@{email.split('@')[1] if '@' in email else 'unknown'}"
            logger.info(f"SESSION_CREATED|email={masked_email}|session={session_id[:8]}***|expiry={expiry_hours}h")
    
    @staticmethod
    def log_security_error(error_type: str, details: str):
        """Log security error event."""
        if SECURITY_MONITORING_ENABLED:
            logger.error(f"SECURITY_ERROR|type={error_type}|details={details}")


# ============================================================================
# Input Validation Utilities
# ============================================================================

def sanitize_email(email: str) -> str:
    """
    Sanitize email address input.
    
    Args:
        email: Raw email address input
    
    Returns:
        Sanitized email address
    """
    if not email:
        return ""
    # Strip whitespace and convert to lowercase
    return email.strip().lower()


def validate_otp_code(code: str) -> Tuple[bool, str]:
    """
    Validate OTP code format.
    
    Args:
        code: OTP code to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code:
        return False, "Code is required"
    
    # Remove any whitespace
    code = code.strip()
    
    # Check length
    if len(code) != 6:
        return False, "Code must be exactly 6 digits"
    
    # Check if all digits
    if not code.isdigit():
        return False, "Code must contain only digits"
    
    return True, ""


def validate_session_id(session_id: str) -> Tuple[bool, str]:
    """
    Validate session ID format.
    
    Args:
        session_id: Session ID to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not session_id:
        return False, "Session ID is required"
    
    # Session IDs should be URL-safe base64 strings
    if len(session_id) < 16:
        return False, "Invalid session ID format"
    
    # Check for valid characters (URL-safe base64)
    import string
    valid_chars = string.ascii_letters + string.digits + '-_'
    if not all(c in valid_chars for c in session_id):
        return False, "Invalid session ID format"
    
    return True, ""


# ============================================================================
# Monitoring Metrics
# ============================================================================

class SecurityMetrics:
    """Track security-related metrics for monitoring."""
    
    # These would typically be stored in a metrics backend (Prometheus, etc.)
    # For now, we just log them
    
    @staticmethod
    def increment_otp_requests():
        """Increment OTP request counter."""
        if SECURITY_MONITORING_ENABLED:
            logger.debug("METRIC|otp_requests_total|+1")
    
    @staticmethod
    def increment_verification_failures():
        """Increment verification failure counter."""
        if SECURITY_MONITORING_ENABLED:
            logger.debug("METRIC|verification_failures_total|+1")
    
    @staticmethod
    def increment_rate_limit_triggers():
        """Increment rate limit trigger counter."""
        if SECURITY_MONITORING_ENABLED:
            logger.debug("METRIC|rate_limit_triggers_total|+1")
    
    @staticmethod
    def increment_email_send_failures():
        """Increment email send failure counter."""
        if SECURITY_MONITORING_ENABLED:
            logger.debug("METRIC|email_send_failures_total|+1")


# Export security event logger singleton
security_events = SecurityEventLogger()
security_metrics = SecurityMetrics()
