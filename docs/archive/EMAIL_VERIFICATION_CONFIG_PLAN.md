# OTP Email Verification - Updated Configuration Plan

## Configuration Architecture

To keep `config.py` clean and maintainable, we'll separate email provider settings into a dedicated configuration file and use a feature flag to enable/disable OTP validation.

---

## File Structure

```
/home/runner/work/HARVEST/HARVEST/
├── config.py                    # Main configuration (feature flags)
├── email_config.py              # Email provider settings (NEW)
├── email_service.py             # Email service implementation (NEW)
├── harvest_be.py                # Backend with OTP endpoints
├── harvest_fe.py                # Frontend with OTP UI
└── harvest_store.py             # Database operations
```

---

## 1. Main Configuration (`config.py`)

### Updated config.py

Add a simple feature flag at the top of the existing config.py:

```python
# config.py

# =============================================================================
# Feature Flags
# =============================================================================

# Enable Literature Search tab (requires admin authentication)
ENABLE_LITERATURE_SEARCH = True

# Enable Literature Review feature (requires admin authentication)
ENABLE_LITERATURE_REVIEW = True

# Enable OTP Email Verification for annotations
# When enabled, users must verify their email via OTP before submitting annotations
# Email provider settings are configured in email_config.py
ENABLE_OTP_VALIDATION = False  # Set to True to enable OTP verification

# ... rest of existing config.py ...
```

**Key points:**
- Single boolean flag: `ENABLE_OTP_VALIDATION`
- Clear comment explaining what it does
- Reference to `email_config.py` for provider settings
- Default is `False` for backwards compatibility
- Easy to enable: just change to `True`

---

## 2. Email Configuration (`email_config.py`) - NEW FILE

Create a new dedicated file for all email-related settings:

```python
# email_config.py
"""
Email Configuration for OTP Verification

This file contains all email provider settings for the OTP verification system.
Sensitive credentials should be stored in environment variables.

Supported providers:
- SendPulse (recommended for HARVEST)
- Gmail
- SendGrid
- AWS SES
- Custom SMTP server
"""

import os

# =============================================================================
# Email Provider Selection
# =============================================================================

# Choose your email provider
# Options: 'sendpulse', 'gmail', 'sendgrid', 'aws_ses', 'custom'
EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'sendpulse')

# =============================================================================
# SendPulse Configuration (RECOMMENDED)
# =============================================================================

SENDPULSE_CONFIG = {
    'smtp_host': 'smtp-pulse.com',
    'smtp_port': 465,  # SSL port (or 587 for TLS)
    'smtp_tls': True,
    'smtp_username': os.environ.get('SENDPULSE_USERNAME', ''),
    'smtp_password': os.environ.get('SENDPULSE_PASSWORD', ''),
    'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@harvest.local'),
    'from_name': 'HARVEST System',
}

# =============================================================================
# Gmail Configuration
# =============================================================================

GMAIL_CONFIG = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_tls': True,
    'smtp_username': os.environ.get('GMAIL_USERNAME', ''),
    'smtp_password': os.environ.get('GMAIL_APP_PASSWORD', ''),  # Use App Password, not regular password
    'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@harvest.local'),
    'from_name': 'HARVEST System',
}

# =============================================================================
# SendGrid Configuration
# =============================================================================

SENDGRID_CONFIG = {
    'smtp_host': 'smtp.sendgrid.net',
    'smtp_port': 587,
    'smtp_tls': True,
    'smtp_username': 'apikey',  # Always 'apikey' for SendGrid
    'smtp_password': os.environ.get('SENDGRID_API_KEY', ''),
    'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@harvest.local'),
    'from_name': 'HARVEST System',
}

# =============================================================================
# AWS SES Configuration
# =============================================================================

AWS_SES_CONFIG = {
    'smtp_host': os.environ.get('AWS_SES_HOST', 'email-smtp.us-east-1.amazonaws.com'),
    'smtp_port': 587,
    'smtp_tls': True,
    'smtp_username': os.environ.get('AWS_SES_USERNAME', ''),
    'smtp_password': os.environ.get('AWS_SES_PASSWORD', ''),
    'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@harvest.local'),
    'from_name': 'HARVEST System',
}

# =============================================================================
# Custom SMTP Configuration
# =============================================================================

CUSTOM_SMTP_CONFIG = {
    'smtp_host': os.environ.get('SMTP_HOST', 'smtp.example.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
    'smtp_tls': os.environ.get('SMTP_TLS', 'true').lower() == 'true',
    'smtp_username': os.environ.get('SMTP_USERNAME', ''),
    'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
    'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@harvest.local'),
    'from_name': os.environ.get('SMTP_FROM_NAME', 'HARVEST System'),
}

# =============================================================================
# Active Configuration (selected based on EMAIL_PROVIDER)
# =============================================================================

PROVIDER_CONFIGS = {
    'sendpulse': SENDPULSE_CONFIG,
    'gmail': GMAIL_CONFIG,
    'sendgrid': SENDGRID_CONFIG,
    'aws_ses': AWS_SES_CONFIG,
    'custom': CUSTOM_SMTP_CONFIG,
}

# Get the active configuration
EMAIL_CONFIG = PROVIDER_CONFIGS.get(EMAIL_PROVIDER, SENDPULSE_CONFIG)

# =============================================================================
# OTP Verification Settings
# =============================================================================

# Code generation
OTP_CODE_LENGTH = 6  # 6-digit codes (1 million combinations)
OTP_CODE_EXPIRY_SECONDS = 600  # 10 minutes

# Session management
OTP_SESSION_EXPIRY_SECONDS = 86400  # 24 hours (1 day)

# Rate limiting
OTP_RATE_LIMIT_REQUESTS = 3  # Max verification emails per email address
OTP_RATE_LIMIT_WINDOW_SECONDS = 3600  # Per hour

# Verification attempts
OTP_MAX_VERIFICATION_ATTEMPTS = 5  # Max wrong codes per verification

# Security
OTP_HASH_ALGORITHM = 'bcrypt'  # Algorithm for hashing codes
OTP_HASH_ROUNDS = 12  # bcrypt rounds (higher = more secure but slower)

# =============================================================================
# Email Templates
# =============================================================================

# Subject line
OTP_EMAIL_SUBJECT = "HARVEST Email Verification Code"

# HTML email template
OTP_EMAIL_TEMPLATE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            line-height: 1.6; 
            color: #333;
        }}
        .container {{ 
            max-width: 600px; 
            margin: 0 auto; 
            padding: 20px; 
        }}
        .header {{
            background: #007bff;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 8px 8px;
        }}
        .code {{ 
            font-size: 36px; 
            font-weight: bold; 
            color: #007bff; 
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            letter-spacing: 8px;
            margin: 20px 0;
            border: 2px solid #007bff;
        }}
        .info {{
            text-align: center;
            margin: 20px 0;
            font-size: 14px;
        }}
        .footer {{ 
            font-size: 12px; 
            color: #666; 
            margin-top: 30px;
            text-align: center;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>HARVEST Email Verification</h2>
        </div>
        <div class="content">
            <p>Thank you for contributing to HARVEST!</p>
            <p>Your verification code is:</p>
            <div class="code">{code}</div>
            <div class="info">
                <p><strong>This code will expire in 10 minutes.</strong></p>
                <p>Enter this code in HARVEST to verify your email address.</p>
            </div>
            <p>If you didn't request this code, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>HARVEST - Human-in-the-loop Actionable Research and Vocabulary Extraction Technology</p>
        </div>
    </div>
</body>
</html>
"""

# Plain text email template (fallback)
OTP_EMAIL_TEMPLATE_TEXT = """
HARVEST Email Verification

Your verification code is: {code}

This code will expire in 10 minutes.

Enter this code in HARVEST to verify your email address.

If you didn't request this code, you can safely ignore this email.

---
HARVEST - Human-in-the-loop Actionable Research and Vocabulary Extraction Technology
"""

# =============================================================================
# Validation
# =============================================================================

def validate_email_config():
    """
    Validate email configuration on startup.
    Raises ValueError if configuration is invalid.
    """
    if not EMAIL_CONFIG['smtp_host']:
        raise ValueError("SMTP host is not configured")
    
    if not EMAIL_CONFIG['smtp_username'] or not EMAIL_CONFIG['smtp_password']:
        raise ValueError(
            f"Email credentials not configured for provider '{EMAIL_PROVIDER}'. "
            "Set environment variables or update email_config.py"
        )
    
    if not EMAIL_CONFIG['from_email']:
        raise ValueError("From email address is not configured")
    
    return True


# =============================================================================
# Helper Functions
# =============================================================================

def get_email_config():
    """Get the active email configuration."""
    return EMAIL_CONFIG.copy()


def get_otp_settings():
    """Get OTP verification settings."""
    return {
        'code_length': OTP_CODE_LENGTH,
        'code_expiry': OTP_CODE_EXPIRY_SECONDS,
        'session_expiry': OTP_SESSION_EXPIRY_SECONDS,
        'rate_limit_requests': OTP_RATE_LIMIT_REQUESTS,
        'rate_limit_window': OTP_RATE_LIMIT_WINDOW_SECONDS,
        'max_attempts': OTP_MAX_VERIFICATION_ATTEMPTS,
    }
```

---

## 3. Environment Variables

Create a `.env.example` file for documentation:

```bash
# .env.example
# Email OTP Verification Configuration

# Email provider selection
# Options: sendpulse, gmail, sendgrid, aws_ses, custom
EMAIL_PROVIDER=sendpulse

# SendPulse Configuration (if EMAIL_PROVIDER=sendpulse)
SENDPULSE_USERNAME=your-email@example.com
SENDPULSE_PASSWORD=your-sendpulse-password

# Gmail Configuration (if EMAIL_PROVIDER=gmail)
# Note: Use App Password, not regular Gmail password
# https://support.google.com/accounts/answer/185833
GMAIL_USERNAME=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# SendGrid Configuration (if EMAIL_PROVIDER=sendgrid)
SENDGRID_API_KEY=SG.your-api-key-here

# AWS SES Configuration (if EMAIL_PROVIDER=aws_ses)
AWS_SES_HOST=email-smtp.us-east-1.amazonaws.com
AWS_SES_USERNAME=your-aws-username
AWS_SES_PASSWORD=your-aws-password

# Custom SMTP Configuration (if EMAIL_PROVIDER=custom)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password

# Common settings (all providers)
SMTP_FROM_EMAIL=noreply@your-domain.com
SMTP_FROM_NAME=HARVEST System
```

---

## 4. Backend Integration (`harvest_be.py`)

Update backend to use the feature flag:

```python
# harvest_be.py

# At the top with other imports
from config import ENABLE_OTP_VALIDATION

# Only import email config if OTP is enabled
if ENABLE_OTP_VALIDATION:
    try:
        from email_config import validate_email_config, get_email_config, get_otp_settings
        from email_service import EmailService
        
        # Validate configuration on startup
        validate_email_config()
        email_service = EmailService()
        logger.info("OTP email verification enabled")
    except Exception as e:
        logger.error(f"Failed to initialize OTP verification: {e}")
        logger.error("OTP verification will be disabled")
        ENABLE_OTP_VALIDATION = False

# API endpoint example
@app.post("/api/auth/send-verification-code")
def send_verification_code():
    """Send OTP verification code to email."""
    if not ENABLE_OTP_VALIDATION:
        return jsonify({
            "ok": False,
            "error": "Email verification is not enabled"
        }), 503
    
    # ... rest of endpoint implementation ...
```

---

## 5. Frontend Integration (`harvest_fe.py`)

Update frontend to check the feature flag:

```python
# harvest_fe.py

# At the top with other imports
from config import ENABLE_OTP_VALIDATION

# In the layout, conditionally show OTP UI
if ENABLE_OTP_VALIDATION:
    email_verification_ui = html.Div([
        dbc.Button("Send Verification Code", id="btn-send-verification"),
        dbc.Input(id="verification-code", placeholder="Enter 6-digit code"),
        html.Div(id="verification-status"),
    ])
else:
    email_verification_ui = html.Div()  # Empty div if OTP disabled

# In annotation form
dbc.Row([
    dbc.Col([
        dbc.Label("Your Email (required)"),
        dbc.Input(id="contributor-email", type="email"),
        html.Small(id="email-validation"),
        email_verification_ui,  # Only shown if ENABLE_OTP_VALIDATION = True
    ])
])
```

---

## 6. Email Service Implementation (`email_service.py`) - NEW FILE

```python
# email_service.py
"""
Email service for OTP verification.
"""

import smtplib
import secrets
import bcrypt
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

try:
    from email_config import (
        get_email_config, 
        get_otp_settings,
        OTP_EMAIL_SUBJECT,
        OTP_EMAIL_TEMPLATE_HTML,
        OTP_EMAIL_TEMPLATE_TEXT
    )
except ImportError:
    raise ImportError("email_config.py not found. Please create it based on email_config.py.example")


class EmailService:
    """Service for sending OTP verification emails."""
    
    def __init__(self):
        self.config = get_email_config()
        self.otp_settings = get_otp_settings()
    
    def generate_otp_code(self):
        """Generate a random OTP code."""
        length = self.otp_settings['code_length']
        code = ''.join(str(secrets.randbelow(10)) for _ in range(length))
        return code
    
    def hash_code(self, code):
        """Hash OTP code for secure storage."""
        return bcrypt.hashpw(code.encode(), bcrypt.gensalt(12)).decode()
    
    def verify_code(self, code, hashed):
        """Verify OTP code against hash."""
        return bcrypt.checkpw(code.encode(), hashed.encode())
    
    def send_verification_email(self, to_email, code):
        """
        Send verification code email.
        
        Args:
            to_email: Recipient email address
            code: OTP code to send
        
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = OTP_EMAIL_SUBJECT
            msg['From'] = f"{self.config['from_name']} <{self.config['from_email']}>"
            msg['To'] = to_email
            
            # Add plain text version
            text_content = OTP_EMAIL_TEMPLATE_TEXT.format(code=code)
            msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML version
            html_content = OTP_EMAIL_TEMPLATE_HTML.format(code=code)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            port = self.config['smtp_port']
            host = self.config['smtp_host']
            username = self.config['smtp_username']
            password = self.config['smtp_password']

            if port == 465:
                # Use SSL for port 465
                with smtplib.SMTP_SSL(host, port) as server:
                    server.login(username, password)
                    server.send_message(msg)
            else:
                # Use STARTTLS for other ports (e.g., 587)
                with smtplib.SMTP(host, port) as server:
                    if self.config['smtp_tls']:
                        server.starttls()
                    server.login(username, password)
                    server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
```

---

## 7. Usage Examples

### Enable OTP Verification

```python
# config.py
ENABLE_OTP_VALIDATION = True  # Enable the feature
```

### Configure SendPulse

```bash
# .env or environment variables
export EMAIL_PROVIDER=sendpulse
export SENDPULSE_USERNAME=your-email@example.com
export SENDPULSE_PASSWORD=your-password
export SMTP_FROM_EMAIL=noreply@harvest.com
```

### Switch to Gmail

```bash
export EMAIL_PROVIDER=gmail
export GMAIL_USERNAME=your-email@gmail.com
export GMAIL_APP_PASSWORD=your-app-password
```

### Disable OTP Verification

```python
# config.py
ENABLE_OTP_VALIDATION = False  # Disable the feature
```

---

## 8. Advantages of This Approach

### ✅ Clean Separation
- Main config has only feature flags
- Email settings in dedicated file
- Easy to find and modify

### ✅ Flexible
- Easy to enable/disable OTP
- Switch providers without touching code
- Environment-based configuration

### ✅ Maintainable
- All email settings in one place
- Clear documentation
- Type safety with validation

### ✅ Backwards Compatible
- Default is disabled (False)
- No breaking changes
- Gradual rollout possible

### ✅ Secure
- Credentials in environment variables
- No hardcoded passwords
- Clear security settings

---

## 9. Migration Guide

### Step 1: Add Feature Flag to config.py

```python
# At top of config.py after other feature flags
ENABLE_OTP_VALIDATION = False  # Add this line
```

### Step 2: Create email_config.py

Copy the complete `email_config.py` from section 2 above.

### Step 3: Create email_service.py

Copy the complete `email_service.py` from section 6 above.

### Step 4: Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your SMTP credentials
```

### Step 5: Update Backend

Add the conditional import and feature check to `harvest_be.py`.

### Step 6: Update Frontend

Add the conditional OTP UI to `harvest_fe.py`.

### Step 7: Enable Feature

```python
# config.py
ENABLE_OTP_VALIDATION = True  # Change to True when ready
```

---

## 10. Testing

### Test with OTP Disabled

```python
# config.py
ENABLE_OTP_VALIDATION = False
```

Start app, verify annotations work without OTP.

### Test with OTP Enabled

```python
# config.py
ENABLE_OTP_VALIDATION = True
```

Start app, verify OTP flow works:
1. Enter email
2. Click "Send Code"
3. Receive email
4. Enter code
5. Verify success
6. Submit annotation

### Test Provider Switching

```bash
# Test SendPulse
export EMAIL_PROVIDER=sendpulse

# Test Gmail
export EMAIL_PROVIDER=gmail

# Test others...
```

---

## 11. Summary

### File Changes

| File | Type | Purpose |
|------|------|---------|
| `config.py` | Modified | Add `ENABLE_OTP_VALIDATION` flag |
| `email_config.py` | **NEW** | All email provider settings |
| `email_service.py` | **NEW** | Email sending implementation |
| `.env.example` | **NEW** | Environment variable documentation |
| `harvest_be.py` | Modified | Conditional OTP endpoints |
| `harvest_fe.py` | Modified | Conditional OTP UI |

### Configuration Structure

```
config.py
  └─ ENABLE_OTP_VALIDATION = True/False
       │
       ├─ If True → import email_config.py
       │              └─ EMAIL_PROVIDER selection
       │                   └─ Provider-specific settings
       │                        └─ From environment variables
       │
       └─ If False → Skip OTP entirely
```

### Benefits

- ✅ Clean config.py (just feature flag)
- ✅ All email settings in one place
- ✅ Easy provider switching
- ✅ Secure (credentials in env)
- ✅ Easy to enable/disable
- ✅ Backwards compatible

This approach keeps the configuration clean, maintainable, and flexible while providing all the functionality needed for OTP email verification.
