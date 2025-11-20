#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Configuration for OTP Email Verification
Separate from main config.py for cleaner configuration
All email provider settings and credentials are configured here
"""

import os

# ============================================================================
# Email Provider Configuration
# ============================================================================

# Email Provider Selection
# Supported providers: sendpulse, sendpulse_smtp, gmail, sendgrid, aws_ses, custom
# sendpulse: Uses REST API (recommended, more features, 15k free emails/month)
# sendpulse_smtp: Uses SMTP (12k free emails/month, simpler setup)
# Set via EMAIL_PROVIDER environment variable or use default
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "sendpulse")

# From Email Address (used as sender for OTP emails)
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@harvest.app")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "HARVEST App")

# ============================================================================
# SendPulse REST API Configuration (Recommended)
# ============================================================================
# Free tier: 15,000 emails/month
# GDPR compliant with EU servers
# Professional deliverability
# REST API Documentation: https://sendpulse.com/integrations/api
# Python Library: https://github.com/sendpulse/sendpulse-rest-api-python
# Setup:
#   1. Sign up at https://sendpulse.com/
#   2. Go to Settings > API
#   3. Create API credentials (get User ID and Secret)
#   4. Set environment variables: SENDPULSE_USER_ID and SENDPULSE_SECRET
# ============================================================================

SENDPULSE_API_CONFIG = {
    "api_user_id": os.getenv("SENDPULSE_USER_ID", ""),  # REST API User ID
    "api_secret": os.getenv("SENDPULSE_SECRET", ""),  # REST API Secret
    "storage_type": "FILE",  # Token storage: FILE or MEMCACHED
}

# ============================================================================
# SendPulse SMTP Configuration (Alternative)
# ============================================================================
# Free tier: 12,000 emails/month
# Use this if you prefer SMTP over REST API
# Setup: https://sendpulse.com/integrations/api/smtp
# ============================================================================

SENDPULSE_SMTP_CONFIG = {
    "smtp_host": "smtp-pulse.com",
    "smtp_port": 465,  # SSL port (alternative: 587 for TLS, 2525 for alternative)
    "use_ssl": True,
    "use_tls": False,
    "username": os.getenv("SENDPULSE_SMTP_USERNAME", ""),  # Your SendPulse email
    "password": os.getenv("SENDPULSE_SMTP_PASSWORD", ""),  # Your SendPulse password/API key
}

# ============================================================================
# Gmail Configuration
# ============================================================================
# Free tier: 500 emails/day
# Requires App Password (not regular password)
# Setup: https://support.google.com/accounts/answer/185833
# ============================================================================

GMAIL_CONFIG = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,  # TLS port
    "use_ssl": False,
    "use_tls": True,
    "username": os.getenv("GMAIL_USERNAME", ""),  # Your Gmail address
    "password": os.getenv("GMAIL_APP_PASSWORD", ""),  # App Password (not regular password)
}

# ============================================================================
# SendGrid Configuration
# ============================================================================
# Free tier: 100 emails/day
# Professional email service
# Setup: https://sendgrid.com/
# ============================================================================

SENDGRID_CONFIG = {
    "smtp_host": "smtp.sendgrid.net",
    "smtp_port": 587,  # TLS port
    "use_ssl": False,
    "use_tls": True,
    "username": "apikey",  # Always "apikey" for SendGrid
    "password": os.getenv("SENDGRID_API_KEY", ""),  # Your SendGrid API Key
}

# ============================================================================
# AWS SES Configuration
# ============================================================================
# Pay per email (~$0.10 per 1,000 emails)
# Requires AWS account
# Setup: https://aws.amazon.com/ses/
# ============================================================================

AWS_SES_CONFIG = {
    "smtp_host": os.getenv("AWS_SES_SMTP_HOST", "email-smtp.us-east-1.amazonaws.com"),
    "smtp_port": 587,  # TLS port
    "use_ssl": False,
    "use_tls": True,
    "username": os.getenv("AWS_SES_SMTP_USERNAME", ""),  # AWS SES SMTP username
    "password": os.getenv("AWS_SES_SMTP_PASSWORD", ""),  # AWS SES SMTP password
}

# ============================================================================
# Custom SMTP Configuration
# ============================================================================
# For institutional or custom SMTP servers
# ============================================================================

CUSTOM_SMTP_CONFIG = {
    "smtp_host": os.getenv("CUSTOM_SMTP_HOST", ""),
    "smtp_port": int(os.getenv("CUSTOM_SMTP_PORT", "587")),
    "use_ssl": os.getenv("CUSTOM_SMTP_USE_SSL", "false").lower() == "true",
    "use_tls": os.getenv("CUSTOM_SMTP_USE_TLS", "true").lower() == "true",
    "username": os.getenv("CUSTOM_SMTP_USERNAME", ""),
    "password": os.getenv("CUSTOM_SMTP_PASSWORD", ""),
}

# ============================================================================
# OTP Configuration
# ============================================================================

OTP_CONFIG = {
    "code_length": 6,  # Length of OTP code (6 digits)
    "code_expiry_seconds": 600,  # OTP expires in 10 minutes
    "session_expiry_seconds": 86400,  # Verified session lasts 24 hours
    "max_attempts": 5,  # Maximum verification attempts per code
    "rate_limit_codes": 3,  # Maximum codes per email per hour
    "rate_limit_window_seconds": 3600,  # Rate limit window (1 hour)
}

# ============================================================================
# Email Templates
# ============================================================================

EMAIL_TEMPLATES = {
    "otp_subject": "Your HARVEST Verification Code",
    
    "otp_html": """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HARVEST Verification Code</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; border-radius: 10px; padding: 30px; margin-bottom: 20px;">
        <h1 style="color: #2c5282; margin-top: 0;">HARVEST Verification Code</h1>
        <p>Hello,</p>
        <p>You requested to contribute annotations to HARVEST. Please use the following verification code to proceed:</p>
        
        <div style="background-color: #fff; border: 2px solid #2c5282; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
            <div style="font-size: 32px; font-weight: bold; color: #2c5282; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                {code}
            </div>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            <strong>Note:</strong> This code will expire in <strong>10 minutes</strong>.
        </p>
        
        <p>If you didn't request this code, you can safely ignore this email.</p>
    </div>
    
    <div style="font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px;">
        <p>This is an automated message from the HARVEST application. Please do not reply to this email.</p>
        <p>HARVEST - Literature Annotation Platform</p>
    </div>
</body>
</html>""",
    
    "otp_text": """HARVEST Verification Code

Hello,

You requested to contribute annotations to HARVEST. Please use the following verification code to proceed:

Verification Code: {code}

Note: This code will expire in 10 minutes.

If you didn't request this code, you can safely ignore this email.

---
This is an automated message from the HARVEST application. Please do not reply to this email.
HARVEST - Literature Annotation Platform
""",
}

# ============================================================================
# Helper Functions
# ============================================================================

def get_smtp_config():
    """Get SMTP configuration for the selected provider."""
    provider_configs = {
        "sendpulse_smtp": SENDPULSE_SMTP_CONFIG,
        "gmail": GMAIL_CONFIG,
        "sendgrid": SENDGRID_CONFIG,
        "aws_ses": AWS_SES_CONFIG,
        "custom": CUSTOM_SMTP_CONFIG,
    }
    
    config = provider_configs.get(EMAIL_PROVIDER.lower())
    if not config:
        raise ValueError(f"Unknown SMTP provider: {EMAIL_PROVIDER}")
    
    return config

def get_sendpulse_api_config():
    """Get SendPulse REST API configuration."""
    return SENDPULSE_API_CONFIG

def is_sendpulse_api():
    """Check if using SendPulse REST API."""
    return EMAIL_PROVIDER.lower() == "sendpulse"

def is_smtp_provider():
    """Check if using SMTP (not REST API)."""
    return EMAIL_PROVIDER.lower() in ["sendpulse_smtp", "gmail", "sendgrid", "aws_ses", "custom"]

def validate_smtp_config():
    """Validate that SMTP configuration has required credentials."""
    config = get_smtp_config()
    
    if not config.get("smtp_host"):
        return False, "SMTP host not configured"
    
    if not config.get("username"):
        return False, f"SMTP username not configured for {EMAIL_PROVIDER}"
    
    if not config.get("password"):
        return False, f"SMTP password not configured for {EMAIL_PROVIDER}"
    
    return True, "Configuration valid"

def validate_sendpulse_api_config():
    """Validate that SendPulse API configuration has required credentials."""
    config = get_sendpulse_api_config()
    
    if not config.get("api_user_id"):
        return False, "SendPulse API User ID not configured"
    
    if not config.get("api_secret"):
        return False, "SendPulse API Secret not configured"
    
    return True, "Configuration valid"

def get_email_template(template_type, **kwargs):
    """Get email template with variables replaced."""
    template = EMAIL_TEMPLATES.get(template_type, "")
    return template.format(**kwargs)
