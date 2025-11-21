# Email Verification System - Implementation Plan

## Problem Statement

Currently, the annotation system asks users to input an email address for attribution, but only validates the email syntax (format). This is vulnerable to abuse as users can:
- Enter fake email addresses that look valid (e.g., `fake@example.com`)
- Add malicious or incorrect entries without accountability
- Impersonate other contributors

## Proposed Solutions

### Option 1: Email Verification with OTP (One-Time Password) ⭐ RECOMMENDED

**Overview:**
Implement a verification system where users must confirm their email address by entering a unique code sent to their email before they can submit annotations.

**Advantages:**
- ✅ Verifies actual email ownership
- ✅ Prevents fake email addresses
- ✅ Maintains accountability
- ✅ User-friendly (familiar pattern)
- ✅ No permanent account needed
- ✅ Works for casual contributors
- ✅ GDPR-compliant (no permanent storage of unverified emails)

**Disadvantages:**
- ❌ Requires email sending infrastructure (SMTP)
- ❌ Slight friction for first-time users
- ❌ Requires backend email service configuration

**Implementation Complexity:** Medium

---

### Option 2: Persistent User Accounts with Email Verification

**Overview:**
Create a full user registration system where users must create an account and verify their email before contributing.

**Advantages:**
- ✅ Strong identity verification
- ✅ Can track user history across sessions
- ✅ Enables user profiles and preferences
- ✅ Better for frequent contributors

**Disadvantages:**
- ❌ High implementation complexity
- ❌ Discourages casual contributors
- ❌ Requires full authentication system
- ❌ Increases data privacy obligations
- ❌ Not aligned with current lightweight approach

**Implementation Complexity:** High

---

### Option 3: Email Domain Whitelist/Blacklist

**Overview:**
Only allow email addresses from specific domains (e.g., institutional domains) or block known disposable email domains.

**Advantages:**
- ✅ Easy to implement
- ✅ Can restrict to trusted institutions
- ✅ No email sending needed

**Disadvantages:**
- ❌ Doesn't verify email ownership
- ❌ Can still be bypassed with fake addresses
- ❌ Excludes legitimate users from non-whitelisted domains
- ❌ Maintenance overhead (updating lists)

**Implementation Complexity:** Low

---

### Option 4: CAPTCHA + Enhanced Email Validation

**Overview:**
Add CAPTCHA (e.g., reCAPTCHA) to prevent automated abuse, combined with stricter email validation.

**Advantages:**
- ✅ Prevents bot abuse
- ✅ Easy to implement
- ✅ No email sending needed
- ✅ Low friction for users

**Disadvantages:**
- ❌ Doesn't prevent fake email addresses
- ❌ Doesn't verify email ownership
- ❌ Only prevents automated abuse, not manual abuse
- ❌ Accessibility concerns

**Implementation Complexity:** Low-Medium

---

### Option 5: Admin Review Queue

**Overview:**
All annotations go into a review queue that admins must approve before becoming visible.

**Advantages:**
- ✅ Complete control over data quality
- ✅ No technical verification needed
- ✅ Can catch all types of abuse

**Disadvantages:**
- ❌ High administrative burden
- ❌ Delays annotation availability
- ❌ Doesn't scale well
- ❌ Discourages casual contributors

**Implementation Complexity:** Medium

---

## Recommended Solution: Email Verification with OTP

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  User Flow                                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. User enters email address                              │
│     ↓                                                       │
│  2. System validates format                                │
│     ↓                                                       │
│  3. User clicks "Send Verification Code"                   │
│     ↓                                                       │
│  4. Backend generates 6-digit code + stores in cache       │
│     ↓                                                       │
│  5. Backend sends email with code (expires in 10 min)      │
│     ↓                                                       │
│  6. User enters code from email                            │
│     ↓                                                       │
│  7. Backend verifies code                                  │
│     ↓                                                       │
│  8. Email marked as verified (session valid 24 hours)      │
│     ↓                                                       │
│  9. User can now submit annotations                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Technical Implementation

#### 1. Database Changes

**New table: `email_verifications`**
```sql
CREATE TABLE IF NOT EXISTS email_verifications (
    email TEXT PRIMARY KEY,
    verification_code TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    verified_at TEXT,
    attempts INTEGER DEFAULT 0,
    last_attempt_at TEXT,
    ip_address TEXT
);
```

**New table: `verified_sessions`**
```sql
CREATE TABLE IF NOT EXISTS verified_sessions (
    session_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ip_address TEXT
);
```

#### 2. Backend Changes (`harvest_be.py`)

**New endpoints:**
```python
@app.post("/api/auth/send-verification-code")
def send_verification_code():
    """
    Generate and send verification code to email.
    Rate limited: max 3 requests per email per hour.
    """
    # 1. Validate email format
    # 2. Check rate limits
    # 3. Generate 6-digit code
    # 4. Hash code for storage
    # 5. Store in database with expiry (10 minutes)
    # 6. Send email via SMTP
    # 7. Return success (don't reveal if email exists)
    pass

@app.post("/api/auth/verify-code")
def verify_code():
    """
    Verify the code entered by user.
    Max 5 attempts per code.
    """
    # 1. Check code exists and not expired
    # 2. Verify code hash matches
    # 3. Check attempt count < 5
    # 4. Create verified session (24 hour validity)
    # 5. Return session token
    pass

@app.get("/api/auth/check-verification")
def check_verification():
    """
    Check if current session has verified email.
    """
    # 1. Check session token
    # 2. Verify session not expired
    # 3. Return verification status
    pass
```

**Email service configuration:**
```python
# In config.py
SMTP_HOST = "smtp.gmail.com"  # or your SMTP server
SMTP_PORT = 587
SMTP_USERNAME = "your-email@example.com"
SMTP_PASSWORD = ""  # Use environment variable
SMTP_FROM_EMAIL = "noreply@harvest-app.com"
SMTP_FROM_NAME = "HARVEST Annotation System"

# Rate limits
EMAIL_VERIFICATION_RATE_LIMIT = 3  # per hour per email
EMAIL_VERIFICATION_CODE_EXPIRY = 600  # 10 minutes
EMAIL_VERIFICATION_SESSION_EXPIRY = 86400  # 24 hours
EMAIL_VERIFICATION_MAX_ATTEMPTS = 5
```

#### 3. Frontend Changes (`harvest_fe.py`)

**UI Updates:**
1. Add "Send Verification Code" button next to email input
2. Add verification code input field (hidden until code sent)
3. Add "Verify" button
4. Show verification status (pending/verified/expired)
5. Disable annotation submission until verified
6. Add countdown timer for code expiry
7. Add resend code button (with cooldown)

**New components:**
```python
# Verification code input
dbc.Input(
    id="verification-code",
    placeholder="Enter 6-digit code",
    type="text",
    maxLength=6,
    pattern="[0-9]{6}",
    style={"display": "none"}  # Hidden initially
)

# Send code button
dbc.Button(
    "Send Verification Code",
    id="btn-send-verification",
    color="primary",
    size="sm"
)

# Verification status
html.Div(id="verification-status")
```

**New callbacks:**
```python
@app.callback(
    Output("verification-code", "style"),
    Output("verification-status", "children"),
    Input("btn-send-verification", "n_clicks"),
    State("contributor-email", "value")
)
def send_verification_code(n_clicks, email):
    # Call backend API to send code
    # Show code input field
    # Display "Code sent to email" message
    pass

@app.callback(
    Output("email-store", "data"),
    Input("verification-code", "value"),
    State("contributor-email", "value")
)
def verify_code(code, email):
    # Call backend API to verify code
    # Store verified session token
    # Update UI to show verified status
    pass
```

#### 4. Email Service Module

**New file: `email_service.py`**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self, smtp_host, smtp_port, username, password):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_verification_code(self, to_email, code):
        """Send verification code email"""
        subject = "HARVEST Verification Code"
        
        html_content = f"""
        <html>
        <body>
            <h2>HARVEST Email Verification</h2>
            <p>Your verification code is:</p>
            <h1 style="color: #007bff;">{code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
        </body>
        </html>
        """
        
        # Send email via SMTP
        pass
```

#### 5. Security Considerations

**Rate Limiting:**
- Max 3 verification code requests per email per hour
- Max 5 verification attempts per code
- Track attempts by IP address
- Exponential backoff on failed attempts

**Code Generation:**
- Use cryptographically secure random number generator
- 6-digit codes (1 million combinations)
- Hash codes before storing (bcrypt or similar)
- Short expiry (10 minutes)

**Session Management:**
- Store verified sessions with expiry
- Use secure session tokens
- Clear expired sessions regularly
- Prevent session fixation attacks

**Privacy:**
- Don't reveal if email exists in system
- Hash IP addresses before storage
- Clear verification records after 7 days
- Log minimal information

#### 6. Migration Strategy

**Phase 1: Add verification (optional)**
- Deploy email verification system
- Make it optional initially
- Add "Skip verification (not recommended)" option
- Monitor adoption rate

**Phase 2: Make verification recommended**
- Keep optional but show strong warnings
- Add banners encouraging verification
- Show verification badge on verified annotations

**Phase 3: Make verification required**
- Remove skip option
- All new annotations require verification
- Grandfather existing contributors (verify on next contribution)

### Alternative: Simplified OTP Implementation

For faster implementation, consider a simplified version:

**Simplified UI:**
- Single "Verify Email" button
- Modal dialog for code entry
- Simpler status indicators

**Simplified Backend:**
- In-memory code storage (no database table)
- Fixed 15-minute expiry
- No session management (verify per submission)

**Pros:**
- Faster implementation
- Less infrastructure
- Simpler maintenance

**Cons:**
- User must verify for each annotation session
- Less secure (no rate limiting)
- No verification history

---

## Implementation Estimates

### Full OTP Implementation
- **Database changes:** 2 hours
- **Backend API endpoints:** 8 hours
- **Email service setup:** 4 hours
- **Frontend UI changes:** 6 hours
- **Testing & security review:** 6 hours
- **Documentation:** 2 hours
- **Total:** ~28 hours (3-4 days)

### Simplified OTP Implementation
- **Backend (in-memory):** 4 hours
- **Email service:** 3 hours
- **Frontend UI:** 4 hours
- **Testing:** 3 hours
- **Total:** ~14 hours (2 days)

---

## Recommendations

1. **Start with simplified OTP implementation** to quickly address the abuse problem
2. **Use existing email infrastructure** if available (institutional SMTP, SendGrid, AWS SES)
3. **Make verification required from day one** - don't do phased rollout (causes confusion)
4. **Add admin override** - let admins manually verify emails for trusted contributors
5. **Monitor verification failures** - log failed attempts to detect abuse patterns
6. **Consider future enhancements:**
   - OAuth integration (Sign in with Google/GitHub)
   - Institutional SSO (SAML/LDAP)
   - API keys for automated submissions

---

## Dependencies

### Python Packages
```txt
# Already in requirements.txt:
flask>=3.0.0
bcrypt>=3.2.0

# Need to add:
# None - use stdlib smtplib
```

### External Services
- SMTP server (Gmail, SendGrid, AWS SES, or institutional)
- Optional: Redis for rate limiting (can use SQLite initially)

### Configuration
- SMTP credentials (environment variables)
- Email templates
- Rate limit settings

---

## Security Checklist

- [ ] Codes are cryptographically random
- [ ] Codes are hashed before storage
- [ ] Short expiry times (10 minutes)
- [ ] Rate limiting implemented
- [ ] Max attempts enforced
- [ ] Session tokens are secure
- [ ] No email enumeration attacks
- [ ] IP addresses are hashed
- [ ] HTTPS enforced
- [ ] Email templates sanitized
- [ ] Logging excludes sensitive data
- [ ] GDPR compliance (data retention)

---

## Testing Plan

1. **Unit tests:**
   - Code generation
   - Code validation
   - Rate limiting
   - Expiry handling

2. **Integration tests:**
   - Email sending
   - Database operations
   - Session management

3. **E2E tests:**
   - Full verification flow
   - Error handling
   - Edge cases

4. **Security tests:**
   - Brute force attempts
   - Code enumeration
   - Rate limit bypass
   - Session hijacking

5. **User acceptance:**
   - Test with sample users
   - Verify email delivery
   - Check spam filters
   - Mobile compatibility

---

## Rollout Plan

### Week 1: Development
- Implement simplified OTP
- Setup email service
- Basic UI

### Week 2: Testing
- Internal testing
- Security review
- Fix bugs

### Week 3: Beta
- Deploy to staging
- Selected user testing
- Monitor metrics

### Week 4: Production
- Deploy to production
- Monitor verification rates
- Gather feedback

---

## Success Metrics

- **Verification rate:** % of users who complete verification
- **Abuse reduction:** Decrease in suspicious annotations
- **User friction:** Time to first annotation
- **Email deliverability:** % of codes successfully delivered
- **Support tickets:** Issues related to verification

**Target:** >90% verification rate, <2 min to first annotation

---

## Appendix: Email Template

```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .code { 
            font-size: 32px; 
            font-weight: bold; 
            color: #007bff; 
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            letter-spacing: 5px;
        }
        .footer { font-size: 12px; color: #666; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>HARVEST Email Verification</h2>
        <p>Thank you for contributing to HARVEST!</p>
        <p>Your verification code is:</p>
        <div class="code">{{ code }}</div>
        <p>This code will expire in <strong>10 minutes</strong>.</p>
        <p>If you didn't request this code, you can safely ignore this email.</p>
        <div class="footer">
            <p>HARVEST - Human-in-the-loop Actionable Research and Vocabulary Extraction Technology</p>
        </div>
    </div>
</body>
</html>
```

---

## Questions for Decision

1. **SMTP Service:** Do you have institutional SMTP or should we use a service like SendGrid?
2. **Verification Frequency:** Per session (24 hours) or per submission?
3. **Required vs Optional:** Make verification required immediately or phase it in?
4. **Admin Override:** Should admins be able to manually verify emails?
5. **Code Format:** 6 digits, or alphanumeric for higher security?
6. **Existing Users:** Grandfather them or require verification on next contribution?

---

## Next Steps

To proceed with implementation:
1. Choose implementation approach (full or simplified)
2. Configure SMTP settings
3. Review security requirements
4. Approve database schema changes
5. Set deployment timeline
6. Assign resources

Would you like me to proceed with implementing the simplified OTP system as a starting point?
