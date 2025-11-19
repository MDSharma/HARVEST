#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Email Service for OTP Verification
Handles email sending via SMTP or SendPulse REST API with support for multiple providers
"""

import smtplib
import secrets
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Optional

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("Warning: bcrypt not available, using SHA256 for password hashing")

# Try to import SendPulse REST API library
try:
    from pysendpulse.pysendpulse import PySendPulse
    SENDPULSE_API_AVAILABLE = True
except ImportError:
    SENDPULSE_API_AVAILABLE = False
    print("Info: pysendpulse library not available. Install with: pip install pysendpulse")

from email_config import (
    get_smtp_config,
    get_sendpulse_api_config,
    validate_smtp_config,
    validate_sendpulse_api_config,
    is_sendpulse_api,
    is_smtp_provider,
    get_email_template,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    OTP_CONFIG,
    EMAIL_PROVIDER
)


class EmailService:
    """Service for sending emails and managing OTP codes."""
    
    def __init__(self):
        """Initialize email service with configuration."""
        self.provider = EMAIL_PROVIDER.lower()
        self.from_email = SMTP_FROM_EMAIL
        self.from_name = SMTP_FROM_NAME
        
        # Initialize based on provider type
        if is_sendpulse_api():
            # Use SendPulse REST API
            if not SENDPULSE_API_AVAILABLE:
                raise ValueError(
                    "SendPulse REST API selected but pysendpulse library not installed. "
                    "Install with: pip install pysendpulse"
                )
            
            is_valid, msg = validate_sendpulse_api_config()
            if not is_valid:
                raise ValueError(f"Invalid SendPulse API configuration: {msg}")
            
            api_config = get_sendpulse_api_config()
            self.sendpulse = PySendPulse(
                api_config["api_user_id"],
                api_config["api_secret"],
                storage_type=api_config.get("storage_type", "FILE")
            )
            self.smtp_config = None
            
        elif is_smtp_provider():
            # Use SMTP
            self.smtp_config = get_smtp_config()
            is_valid, msg = validate_smtp_config()
            if not is_valid:
                raise ValueError(f"Invalid SMTP configuration: {msg}")
            self.sendpulse = None
            
        else:
            raise ValueError(f"Unknown email provider: {EMAIL_PROVIDER}")
    
    @staticmethod
    def generate_otp_code(length: int = 6) -> str:
        """
        Generate a cryptographically secure OTP code.
        
        Args:
            length: Length of the OTP code (default: 6)
        
        Returns:
            OTP code as string
        """
        # Generate secure random digits
        code = ''.join([str(secrets.randbelow(10)) for _ in range(length)])
        return code
    
    @staticmethod
    def hash_code(code: str) -> str:
        """
        Hash OTP code for secure storage.
        
        Args:
            code: Plain text OTP code
        
        Returns:
            Hashed code
        """
        if BCRYPT_AVAILABLE:
            # Use bcrypt for secure hashing
            return bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # Fallback to SHA256 (less secure but acceptable for OTP)
            return hashlib.sha256(code.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_code(plain_code: str, hashed_code: str) -> bool:
        """
        Verify OTP code against hash.
        
        Args:
            plain_code: Plain text OTP code
            hashed_code: Hashed code from database
        
        Returns:
            True if code matches, False otherwise
        """
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(plain_code.encode('utf-8'), hashed_code.encode('utf-8'))
            except Exception:
                return False
        else:
            # Fallback to SHA256 comparison
            return hashlib.sha256(plain_code.encode('utf-8')).hexdigest() == hashed_code
    
    def send_otp_email(self, to_email: str, code: str) -> Tuple[bool, str]:
        """
        Send OTP verification email.
        
        Args:
            to_email: Recipient email address
            code: OTP code to send
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if is_sendpulse_api():
            return self._send_via_sendpulse_api(to_email, code)
        else:
            return self._send_via_smtp(to_email, code)
    
    def _send_via_sendpulse_api(self, to_email: str, code: str) -> Tuple[bool, str]:
        """Send email via SendPulse REST API."""
        try:
            # Prepare email data
            email_data = {
                "subject": get_email_template("otp_subject"),
                "html": get_email_template("otp_html", code=code),
                "text": get_email_template("otp_text", code=code),
                "from": {
                    "name": self.from_name,
                    "email": self.from_email
                },
                "to": [
                    {
                        "email": to_email
                    }
                ]
            }
            
            # Send via API
            response = self.sendpulse.smtp_send_mail(email_data)
            
            # Check response
            if response and response.get("result"):
                return True, f"OTP email sent successfully to {to_email}"
            else:
                error_msg = response.get("message", "Unknown error") if response else "No response"
                return False, f"SendPulse API error: {error_msg}"
                
        except Exception as e:
            return False, f"Failed to send email via SendPulse API: {str(e)}"
    
    def _send_via_smtp(self, to_email: str, code: str) -> Tuple[bool, str]:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = get_email_template("otp_subject")
            
            # Add text and HTML versions
            text_body = get_email_template("otp_text", code=code)
            html_body = get_email_template("otp_html", code=code)
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            if self.smtp_config.get("use_ssl"):
                # Use SSL connection
                with smtplib.SMTP_SSL(
                    self.smtp_config["smtp_host"],
                    self.smtp_config["smtp_port"],
                    timeout=30
                ) as server:
                    server.login(
                        self.smtp_config["username"],
                        self.smtp_config["password"]
                    )
                    server.send_message(msg)
            else:
                # Use TLS connection
                with smtplib.SMTP(
                    self.smtp_config["smtp_host"],
                    self.smtp_config["smtp_port"],
                    timeout=30
                ) as server:
                    if self.smtp_config.get("use_tls"):
                        server.starttls()
                    server.login(
                        self.smtp_config["username"],
                        self.smtp_config["password"]
                    )
                    server.send_message(msg)
            
            return True, f"OTP email sent successfully to {to_email}"
            
        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check email provider credentials."
        except smtplib.SMTPException as e:
            return False, f"SMTP error: {str(e)}"
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    def send_verification_email(self, to_email: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate OTP code and send verification email.
        
        Args:
            to_email: Recipient email address
        
        Returns:
            Tuple of (success: bool, message: str, code_hash: Optional[str])
        """
        try:
            # Generate OTP code
            code = self.generate_otp_code(OTP_CONFIG["code_length"])
            
            # Send email
            success, msg = self.send_otp_email(to_email, code)
            
            if success:
                # Hash code for storage
                code_hash = self.hash_code(code)
                return True, msg, code_hash
            else:
                return False, msg, None
                
        except Exception as e:
            return False, f"Error generating verification email: {str(e)}", None


# Singleton instance
_email_service_instance = None

def get_email_service() -> EmailService:
    """Get singleton EmailService instance."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance


# Test function
def test_email_service():
    """Test email service configuration."""
    try:
        service = get_email_service()
        print(f"✓ Email service initialized successfully")
        print(f"  Provider: {EMAIL_PROVIDER}")
        print(f"  From: {SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>")
        
        if is_sendpulse_api():
            print(f"  Method: SendPulse REST API")
            api_config = get_sendpulse_api_config()
            print(f"  API User ID: {api_config['api_user_id'][:10]}..." if api_config['api_user_id'] else "  API User ID: NOT SET")
            print(f"  API Secret: {'*' * 20}")
        else:
            print(f"  Method: SMTP")
            print(f"  SMTP Host: {service.smtp_config['smtp_host']}")
            print(f"  SMTP Port: {service.smtp_config['smtp_port']}")
            print(f"  Use SSL: {service.smtp_config.get('use_ssl', False)}")
            print(f"  Use TLS: {service.smtp_config.get('use_tls', False)}")
        
        # Test code generation
        code = EmailService.generate_otp_code()
        print(f"\n✓ OTP code generation works: {code}")
        
        # Test hashing
        hashed = EmailService.hash_code(code)
        print(f"✓ Code hashing works: {hashed[:50]}...")
        
        # Test verification
        verified = EmailService.verify_code(code, hashed)
        print(f"✓ Code verification works: {verified}")
        
        return True
    except Exception as e:
        print(f"✗ Email service test failed: {e}")
        return False


if __name__ == "__main__":
    test_email_service()
