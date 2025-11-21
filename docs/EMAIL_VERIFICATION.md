# Email Verification System

Complete guide for HARVEST's OTP-based email verification system.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Database Architecture](#database-architecture)
- [Frontend Implementation](#frontend-implementation)
- [API Endpoints](#api-endpoints)
- [Security Considerations](#security-considerations)

---


---

## Content from EMAIL_VERIFICATION_QUICK_GUIDE.md

# Email Verification Solutions - Quick Comparison

## Summary of Options

| Solution | Security | UX Friction | Complexity | Cost | Recommended |
|----------|----------|-------------|------------|------|-------------|
| **OTP Email Verification** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | $ | ✅ YES |
| User Accounts | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | $$ | ❌ No |
| Domain Whitelist | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | $ | ❌ No |
| CAPTCHA | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | $ | ⚠️ Partial |
| Admin Review | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | $$$ | ❌ No |

**Legend:**
- ⭐ = Low | ⭐⭐⭐ = Medium | ⭐⭐⭐⭐⭐ = High
- $ = Low cost | $$ = Medium | $$$ = High cost

---

## Recommended Solution: OTP Email Verification

### What It Does
1. User enters email → clicks "Send Code"
2. 6-digit code sent to email (expires in 10 min)
3. User enters code → email verified
4. Verification valid for 24 hours
5. Can now submit annotations

### Why This Solution?
✅ **Verifies real email ownership** - Not just format validation
✅ **Prevents fake emails** - Must receive and enter code
✅ **Low friction** - Familiar pattern users know
✅ **No accounts needed** - Keeps current simple flow
✅ **Reasonable cost** - Just need SMTP service
✅ **GDPR friendly** - No permanent storage of unverified data

### Implementation Time
- **Simplified version:** 2 days (14 hours)
- **Full version:** 4 days (28 hours)

---

## How It Works

```
Current Flow (VULNERABLE):
┌─────────────────────────────────────┐
│ 1. Enter email: fake@example.com   │
│ 2. Format looks valid ✓             │
│ 3. Submit annotation immediately    │
│ 4. Data added to system ✓           │
└─────────────────────────────────────┘
Problem: Anyone can use fake emails!

New Flow (SECURE):
┌─────────────────────────────────────┐
│ 1. Enter email: user@real.com      │
│ 2. Click "Send Verification Code"  │
│ 3. Check email → receive: 123456   │
│ 4. Enter code: 123456               │
│ 5. Verified ✓ (valid 24 hours)     │
│ 6. Can now submit annotations       │
└─────────────────────────────────────┘
Solution: Must own the email!
```

---

## Visual Mockup

### Before Verification
```
┌────────────────────────────────────────┐
│ Your Email (required)                  │
│ ┌────────────────────────────────────┐ │
│ │ user@example.com                   │ │
│ └────────────────────────────────────┘ │
│ ❌ Email not verified                  │
│ [Send Verification Code]               │
│                                        │
│ [Submit Annotation] ← DISABLED         │
└────────────────────────────────────────┘
```

### Code Sent
```
┌────────────────────────────────────────┐
│ Your Email (required)                  │
│ ┌────────────────────────────────────┐ │
│ │ user@example.com                   │ │
│ └────────────────────────────────────┘ │
│ ℹ️  Code sent! Check your email        │
│                                        │
│ Verification Code                      │
│ ┌────────────────────────────────────┐ │
│ │ [______]                           │ │
│ └────────────────────────────────────┘ │
│ [Verify Code] [Resend Code (45s)]     │
│                                        │
│ [Submit Annotation] ← DISABLED         │
└────────────────────────────────────────┘
```

### Verified
```
┌────────────────────────────────────────┐
│ Your Email (required)                  │
│ ┌────────────────────────────────────┐ │
│ │ user@example.com                   │ │
│ └────────────────────────────────────┘ │
│ ✅ Email verified (valid 24 hours)     │
│                                        │
│ [Submit Annotation] ← ENABLED          │
└────────────────────────────────────────┘
```

---

## Required Configuration

### 1. SMTP Settings (in `config.py`)
```python
# Email verification settings
ENABLE_EMAIL_VERIFICATION = True
SMTP_HOST = "smtp.gmail.com"  # or your SMTP server
SMTP_PORT = 587
SMTP_TLS = True
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = "noreply@your-domain.com"
SMTP_FROM_NAME = "HARVEST System"

# Verification settings
VERIFICATION_CODE_LENGTH = 6
VERIFICATION_CODE_EXPIRY = 600  # 10 minutes
VERIFICATION_SESSION_EXPIRY = 86400  # 24 hours
VERIFICATION_RATE_LIMIT = 3  # codes per hour per email
VERIFICATION_MAX_ATTEMPTS = 5  # max wrong codes
```

### 2. Environment Variables
```bash
export SMTP_USERNAME="your-email@example.com"
export SMTP_PASSWORD="your-app-password"
```

### 3. SMTP Service Options

**Option A: Gmail (Free)**
- Use Gmail SMTP
- Need App Password (not regular password)
- Limit: 500 emails/day
- Best for: Testing, small deployments

**Option B: SendGrid (Freemium)**
- 100 emails/day free
- Professional sender reputation
- Email analytics
- Best for: Small to medium deployments

**Option C: AWS SES (Pay-as-you-go)**
- $0.10 per 1,000 emails
- High deliverability
- Scalable
- Best for: Large deployments

**Option D: Institutional SMTP**
- Use university/organization SMTP
- Usually free
- Already trusted
- Best for: Academic/institutional use

---

## Security Features

### Rate Limiting
- 3 code requests per email per hour
- 5 verification attempts per code
- IP-based tracking
- Exponential backoff

### Code Security
- 6-digit codes (1 million combinations)
- Cryptographically random generation
- Hashed storage (bcrypt)
- 10-minute expiry
- One-time use

### Session Management
- 24-hour validity
- Secure token generation
- Automatic expiry cleanup
- Session invalidation on logout

### Privacy
- No email enumeration
- IP addresses hashed
- Minimal logging
- GDPR compliant
- Auto-deletion after 7 days

---

## Alternative: Hybrid Approach

Combine multiple methods for maximum security:

**Tier 1 (Basic):**
- Email format validation
- CAPTCHA

**Tier 2 (Standard):**
- Email verification (OTP)
- Session management

**Tier 3 (Advanced - optional):**
- Domain whitelist for institutions
- Admin review for suspicious patterns
- Rate limiting per IP

This gives flexibility while maintaining security.

---

## Migration Path

### Phase 1: Deploy (Week 1)
- Add verification system
- Make it optional with warning
- Monitor adoption

### Phase 2: Encourage (Week 2)
- Show "unverified" badge on annotations
- Add banner encouraging verification
- Offer to verify existing contributors

### Phase 3: Require (Week 3)
- Make verification mandatory
- Remove bypass option
- All new annotations require verification

**OR: Direct Deployment**
- Deploy with verification required immediately
- Simpler approach
- Clear expectations
- Faster security improvement

---

## Cost Estimate

### Development Cost
- Simplified version: 2 days
- Full version: 4 days

### Operational Cost (per month)
- **Gmail:** Free (up to 500/day)
- **SendGrid:** Free (100/day) to $15/month (40k/day)
- **AWS SES:** ~$1-10/month (1k-10k emails)
- **Institutional:** Free

### Maintenance Cost
- Monitoring: 1 hour/month
- Support: 2 hours/month
- Updates: Minimal

**Total:** $0-15/month + minimal maintenance

---

## FAQ

**Q: What if user doesn't receive the code?**
A: Add "Resend Code" button (with 60s cooldown). Also check spam folder.

**Q: What if SMTP is down?**
A: Graceful degradation - show error message, allow admin override.

**Q: How long is code valid?**
A: 10 minutes (configurable). Balance between security and convenience.

**Q: Can users verify once and reuse forever?**
A: No, verification valid for 24 hours. Must re-verify after expiry.

**Q: What about existing contributors?**
A: Grandfather them - they verify on next contribution.

**Q: Can admins bypass verification?**
A: Yes, add admin override for trusted users.

**Q: What if user typos their email?**
A: They won't receive code, can re-enter email and try again.

**Q: Mobile-friendly?**
A: Yes, 6-digit codes work well on mobile devices.

---

## Decision Matrix

Choose your implementation based on your constraints:

| Constraint | Simplified OTP | Full OTP | Account System |
|------------|----------------|----------|----------------|
| Time < 1 week | ✅ | ❌ | ❌ |
| Budget < $50/month | ✅ | ✅ | ❌ |
| No SMTP available | ❌ | ❌ | ❌ |
| High security needed | ⚠️ | ✅ | ✅ |
| Low user friction | ✅ | ✅ | ❌ |
| Casual contributors | ✅ | ✅ | ❌ |

**Recommendation:** Start with Simplified OTP, upgrade to Full OTP if needed.

---

## Next Steps

**To proceed, please answer:**

1. **SMTP Service:** Which option? (Gmail/SendGrid/AWS SES/Institutional)
2. **Verification Required:** Immediately or phased rollout?
3. **Implementation:** Simplified (2 days) or Full (4 days)?
4. **Timeline:** When do you want this deployed?
5. **Testing:** Internal only or beta users?

**Once decided, I can:**
- Implement the chosen solution
- Setup database schema
- Create email templates
- Add frontend UI
- Write tests
- Deploy to staging

Ready to proceed with implementation?



---

## Content from EMAIL_VERIFICATION_DATABASE_ARCHITECTURE.md

# Email Verification Database Architecture - Separate vs Integrated

## Question

Should the email validation database be separate from the main database that holds triples, or should they be integrated?

## Analysis

### Current Database Structure

HARVEST currently uses a **single SQLite database** (`harvest.db`) with multiple tables:

**Core Data Tables:**
- `sentences` - Literature sentences
- `triples` - Entity relationships (main data)
- `doi_metadata` - Document metadata
- `projects` - Annotation projects

**User/Auth Tables:**
- `user_sessions` - User session tracking
- `admin_users` - Admin authentication

**Operational Tables:**
- `pdf_download_progress` - PDF download status

**Database path:** Typically `data/harvest.db` (single file)

---

## Recommendation: ⭐ Keep in Same Database (Integrated)

### Why Integrate Email Verification Tables?

#### ✅ Advantages

**1. Simpler Architecture**
- Single database file to manage
- No need for multiple connections
- Easier backup and restore
- Simpler deployment

**2. Transaction Safety**
- Can use atomic transactions across all tables
- Ensure data consistency between email verification and annotations
- Example: Verify email + insert annotation in single transaction

**3. Less Operational Overhead**
- One database to monitor
- One database to backup
- One database to optimize
- One database to migrate

**4. Related Data**
- Email verifications are directly related to contributors
- Contributor email is already stored in `triples` table
- Makes sense to keep related data together

**5. Better Performance**
- No cross-database queries needed
- Single connection pool
- Faster lookups when checking verification status

**6. Easier Foreign Key Relationships**
- Can create foreign keys between verification and triples tables
- Referential integrity enforced by SQLite

**7. Consistent with Current Design**
- Already mixing auth tables (`admin_users`, `user_sessions`) with data tables
- Email verification is similar to user sessions

**8. Simpler Code**
- Single database connection in code
- No need to manage multiple database paths
- Easier to test

#### ⚠️ Considerations

**1. Table Separation is Still Clean**
- Email verification tables are separate entities
- Clear naming convention (e.g., `email_verifications`, `verified_sessions`)
- No direct coupling with triples table schema

**2. Data Isolation**
- Can still query verification data independently
- Can drop/recreate verification tables without affecting triples
- Can export/import separately if needed

**3. Size Won't Be an Issue**
- Verification data is tiny compared to triples
- Codes expire and get cleaned up
- Sessions expire after 24 hours
- Minimal storage impact

---

## Alternative: Separate Database (Not Recommended)

### If You Use Separate Database

**Structure:**
```
data/harvest.db              # Main database (triples, sentences, etc.)
data/harvest_auth.db         # Separate auth database (email verification)
```

#### ❌ Disadvantages

**1. More Complex Code**
```python
# Need two database connections
main_db = sqlite3.connect('data/harvest.db')
auth_db = sqlite3.connect('data/harvest_auth.db')

# Can't use transactions across databases
# More error-prone code
```

**2. Operational Burden**
- Two databases to backup
- Two databases to monitor
- Two databases to optimize
- More complex deployment

**3. No Transaction Safety**
- Can't atomically verify email + insert annotation
- Risk of inconsistency

**4. Harder to Query**
- Need to join data across databases (complex in SQLite)
- Can't use foreign keys across databases
- More complex reporting queries

**5. Inconsistent with Current Design**
- Current design already mixes auth (`admin_users`) with data
- Would need to move `admin_users` and `user_sessions` too for consistency
- Or have inconsistent architecture

#### ✅ Advantages (Minor)

**1. Conceptual Separation**
- Clear separation of concerns
- Auth data physically separate from annotation data

**2. Independent Scaling** (Not Relevant)
- Could theoretically scale auth separately
- But SQLite doesn't scale horizontally anyway
- Not a real benefit for HARVEST's use case

**3. Security Isolation** (Minimal)
- Could set different permissions
- But both databases on same server anyway
- Not a significant security benefit

---

## Recommended Database Schema

### Integrated Approach (Recommended)

Add these tables to the existing `harvest.db`:

```sql
-- Email verification codes (temporary, expires in 10 minutes)
CREATE TABLE IF NOT EXISTS email_verifications (
    email TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_attempt_at TEXT,
    ip_address_hash TEXT  -- Hashed for privacy
);

-- Verified email sessions (lasts 24 hours)
CREATE TABLE IF NOT EXISTS verified_sessions (
    session_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ip_address_hash TEXT  -- Hashed for privacy
);

-- Cleanup expired records with indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_verifications_expires 
    ON email_verifications(expires_at);
CREATE INDEX IF NOT EXISTS idx_verified_sessions_expires 
    ON verified_sessions(expires_at);
```

**Benefits:**
- All in `data/harvest.db` (single file)
- Clear table names (prefixed with purpose)
- Proper indexes for cleanup queries
- No foreign keys needed (loose coupling)

### Maintenance Queries

**Cleanup expired verification codes:**
```sql
DELETE FROM email_verifications 
WHERE expires_at < datetime('now');
```

**Cleanup expired sessions:**
```sql
DELETE FROM verified_sessions 
WHERE expires_at < datetime('now');
```

**Schedule cleanup:** Run every hour via cron or background task

---

## Updated Implementation Plan

### Database Initialization (`harvest_store.py`)

```python
def init_db(db_path: str) -> None:
    """Initialize database with all tables including email verification."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        
        # ... existing tables (sentences, triples, etc.) ...
        
        # Email verification tables (NEW)
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
        
        conn.commit()
```

### Email Verification Service (`email_verification_store.py` - NEW)

Create a separate module for email verification database operations:

```python
# email_verification_store.py
"""
Database operations for email verification.
All operations use the main harvest.db database.
"""

import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

def hash_ip(ip_address: str, salt: str) -> str:
    """Hash IP address for privacy."""
    return hashlib.sha256((salt + ip_address).encode()).hexdigest()[:16]

def store_verification_code(
    db_path: str, 
    email: str, 
    code_hash: str, 
    expiry_seconds: int = 600,
    ip_address: str = None,
    salt: str = ""
) -> bool:
    """Store verification code in database."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
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
    code: str, # Changed from code_hash to raw code
    max_attempts: int = 5
) -> Dict[str, any]:
    """
    Verify code for email.
    Returns dict with 'valid', 'expired', 'attempts_exceeded' flags.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            email_lower = email.strip().lower()
            cur.execute("""
                SELECT code_hash, expires_at, attempts
                FROM email_verifications
                WHERE email = ?
            """, (email_lower,))
            
            row = cur.fetchone()
            if not row:
                return {'valid': False, 'error': 'not_found'}
            
            stored_hash, expires_at, attempts = row
            
            if datetime.utcnow() > datetime.fromisoformat(expires_at):
                return {'valid': False, 'error': 'expired'}
            
            if attempts >= max_attempts:
                return {'valid': False, 'error': 'attempts_exceeded'}
            
            # Use bcrypt to securely compare the raw code with the stored hash
            import bcrypt
            if bcrypt.checkpw(code.encode(), stored_hash.encode()):
                # On success, delete the record
                cur.execute("DELETE FROM email_verifications WHERE email = ?", (email_lower,))
                conn.commit()
                return {'valid': True}
            else:
                # On failure, increment attempts
                cur.execute("""
                    UPDATE email_verifications
                    SET attempts = attempts + 1,
                        last_attempt_at = ?
                    WHERE email = ?
                """, (datetime.utcnow().isoformat(), email_lower))
                conn.commit()
                return {'valid': False, 'error': 'invalid_code'}
                
    except Exception as e:
        print(f"Error verifying code: {e}")
        return {'valid': False, 'error': 'server_error'}

def create_verified_session(
    db_path: str,
    session_id: str,
    email: str,
    expiry_seconds: int = 86400,
    ip_address: str = None,
    salt: str = ""
) -> bool:
    """Create verified session for email."""
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
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
            
            conn.commit()
            
            return {
                'verifications': verifications_deleted,
                'sessions': sessions_deleted
            }
    except Exception as e:
        print(f"Error cleaning up expired records: {e}")
        return {'verifications': 0, 'sessions': 0}
```

### Background Cleanup Task

Add to backend startup (e.g., in `harvest_be.py`):

```python
import threading
import time
from email_verification_store import cleanup_expired_records

def cleanup_task(db_path: str, interval_seconds: int = 3600):
    """Background task to cleanup expired records every hour."""
    while True:
        time.sleep(interval_seconds)
        try:
            deleted = cleanup_expired_records(db_path)
            print(f"Cleaned up {deleted['verifications']} expired codes, "
                  f"{deleted['sessions']} expired sessions")
        except Exception as e:
            print(f"Cleanup task error: {e}")

# Start cleanup task when OTP is enabled
if ENABLE_OTP_VALIDATION:
    cleanup_thread = threading.Thread(
        target=cleanup_task, 
        args=(DB_PATH, 3600),  # Run every hour
        daemon=True
    )
    cleanup_thread.start()
```

---

## Comparison Summary

| Aspect | Single Database (✅ Recommended) | Separate Database (❌ Not Recommended) |
|--------|----------------------------------|----------------------------------------|
| **Architecture** | Simple, single file | Complex, multiple files |
| **Code Complexity** | Low (one connection) | High (two connections) |
| **Transactions** | Atomic across all tables | No cross-database transactions |
| **Backup** | One file to backup | Two files to backup |
| **Performance** | Fast (single connection) | Slower (multiple connections) |
| **Deployment** | Simple | More complex |
| **Maintenance** | Easy | More overhead |
| **Consistency** | Strong (FK constraints) | Weak (no FK across DBs) |
| **Current Design** | Consistent | Inconsistent |
| **Data Size** | Negligible impact | Minimal benefit |

---

## Implementation Checklist

### Phase 1: Update Database Schema
- [x] Add `email_verifications` table to `harvest_store.py`
- [x] Add `verified_sessions` table to `harvest_store.py`
- [x] Add indexes for expiry fields
- [x] Test schema migration on existing database

### Phase 2: Create Verification Module
- [x] Create `email_verification_store.py` module
- [x] Implement `store_verification_code()` function
- [x] Implement `verify_code()` function
- [x] Implement `create_verified_session()` function
- [x] Implement `check_verified_session()` function
- [x] Implement `cleanup_expired_records()` function
- [x] Add IP address hashing for privacy

### Phase 3: Background Cleanup
- [x] Add cleanup background task
- [x] Schedule to run every hour
- [x] Log cleanup activity

### Phase 4: Integration
- [x] Use in backend OTP endpoints
- [x] Use in frontend verification flow
- [x] Test end-to-end

---

## Final Recommendation

**✅ Use Single Database (Integrated Approach)**

**Rationale:**
1. **Simpler** - Single database file, single connection, easier to manage
2. **Consistent** - Auth tables (`admin_users`, `user_sessions`) already in main database
3. **Safe** - Transaction safety across all tables
4. **Performant** - No cross-database queries, single connection pool
5. **Maintainable** - One database to backup, monitor, and optimize
6. **Practical** - Verification data is tiny, no size concerns

**Database Structure:**
```
data/harvest.db (single database)
├── Core Data Tables
│   ├── sentences
│   ├── triples
│   ├── doi_metadata
│   └── projects
├── Auth Tables
│   ├── admin_users
│   ├── user_sessions
│   ├── email_verifications     (NEW - OTP codes)
│   └── verified_sessions       (NEW - Verified emails)
└── Operational Tables
    └── pdf_download_progress
```

**Implementation:**
- Add two new tables to existing `harvest.db`
- Create separate module (`email_verification_store.py`) for verification operations
- Add background cleanup task for expired records
- Use existing database connection pattern

This approach keeps the architecture clean, simple, and maintainable while providing all needed functionality for OTP email verification.



---

## Content from FRONTEND_EMAIL_VERIFICATION_GUIDE.md

# Frontend Email Verification Implementation Guide

## Overview

This document provides step-by-step instructions for integrating email verification into the HARVEST frontend (harvest_fe.py).

## Current State

**Backend:** ✅ Complete
- Database tables created
- API endpoints implemented
- Background cleanup running
- SendPulse REST API supported

**Frontend:** 🚧 To Be Implemented
- Email verification UI components
- OTP code input
- Session management
- Integration with annotation flow

## Implementation Steps

### Step 1: Add Stores for OTP State

Add new dcc.Store components after the existing email-store:

```python
# Around line 735, after existing stores
dcc.Store(id="email-store", storage_type="session"),
dcc.Store(id="otp-verification-store", storage_type="session"),  # NEW: OTP state
dcc.Store(id="otp-session-store", storage_type="local"),  # NEW: Verified session (24h)
```

### Step 2: Update Email Input Section

Replace the current email input section (around lines 1370-1386) with enhanced version:

```python
dbc.Col(
    [
        dbc.Label("Your Email (required)", style={"fontWeight": "bold"}),
        dbc.Input(
            id="contributor-email",
            placeholder="email@example.com",
            type="email",
            debounce=True,
            required=True,
        ),
        html.Small(
            id="email-validation",
            className="text-muted",
        ),
        # NEW: OTP Verification Section (hidden by default)
        html.Div(
            id="otp-verification-section",
            children=[
                dbc.Label("Verification Code", className="mt-2", style={"fontWeight": "bold"}),
                html.Small("Check your email for the 6-digit code", className="text-muted d-block mb-1"),
                dbc.InputGroup(
                    [
                        dbc.Input(
                            id="otp-code-input",
                            placeholder="Enter 6-digit code",
                            type="text",
                            maxLength=6,
                            pattern="[0-9]{6}",
                        ),
                        dbc.Button(
                            "Verify",
                            id="otp-verify-button",
                            color="primary",
                            disabled=True
                        ),
                    ],
                    className="mb-2"
                ),
                html.Div(id="otp-verification-feedback"),
                dbc.Button(
                    "Resend Code",
                    id="otp-resend-button",
                    color="link",
                    size="sm",
                    className="p-0"
                ),
            ],
            style={"display": "none"}  # Hidden by default
        ),
    ],
    md=12,
),
```

### Step 3: Add Callback to Request OTP Code

Add after the existing validate_email callback (around line 2088):

```python
@app.callback(
    Output("otp-verification-section", "style"),
    Output("otp-verification-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Input("email-store", "data"),
    State("otp-session-store", "data"),
    prevent_initial_call=True
)
def request_otp_code(email, session_data):
    """
    Request OTP code when email is validated.
    Check if OTP validation is enabled first.
    """
    import requests
    
    # Check if OTP is enabled
    try:
        config_response = requests.get(f"{BACKEND_URL}/api/email-verification/config")
        if not config_response.ok or not config_response.json().get("enabled"):
            # OTP not enabled, keep section hidden
            return {"display": "none"}, None, "", {}
    except:
        # API error, keep section hidden
        return {"display": "none"}, None, "", {}
    
    # Check if already verified
    if session_data and session_data.get("session_id"):
        # Check session validity
        try:
            check_response = requests.post(
                f"{BACKEND_URL}/api/email-verification/check-session",
                json={"session_id": session_data["session_id"]}
            )
            if check_response.ok and check_response.json().get("verified"):
                # Already verified, keep section hidden
                return {"display": "none"}, session_data, "✓ Email verified", {"color": "green"}
        except:
            pass
    
    if not email:
        return {"display": "none"}, None, "", {}
    
    # Request OTP code
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return (
                {"display": "block"},  # Show OTP section
                {"email": email, "code_requested": True},
                "Verification code sent to your email",
                {"color": "blue"}
            )
        else:
            error = response.json().get("error", "Failed to send code")
            return (
                {"display": "none"},
                None,
                f"Error: {error}",
                {"color": "red"}
            )
    except Exception as e:
        return (
            {"display": "none"},
            None,
            f"Error requesting code: {str(e)}",
            {"color": "red"}
        )
```

### Step 4: Add Callback to Enable Verify Button

```python
@app.callback(
    Output("otp-verify-button", "disabled"),
    Input("otp-code-input", "value"),
)
def enable_verify_button(code):
    """Enable verify button when code is 6 digits."""
    if code and len(code) == 6 and code.isdigit():
        return False
    return True
```

### Step 5: Add Callback to Verify OTP Code

```python
@app.callback(
    Output("otp-verification-feedback", "children"),
    Output("otp-session-store", "data"),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Output("otp-verification-section", "style", allow_duplicate=True),
    Input("otp-verify-button", "n_clicks"),
    State("otp-code-input", "value"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def verify_otp_code(n_clicks, code, otp_data):
    """Verify OTP code and create session."""
    if not n_clicks or not code or not otp_data:
        return "", None, "", {}, {"display": "block"}
    
    email = otp_data.get("email")
    if not email:
        return (
            dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"}
        )
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/verify-code",
            json={"email": email, "code": code}
        )
        
        if response.ok:
            data = response.json()
            session_id = data.get("session_id")
            
            return (
                dbc.Alert("✓ Email verified successfully!", color="success", dismissable=True, duration=3000),
                {"session_id": session_id, "email": email},
                "✓ Email verified",
                {"color": "green"},
                {"display": "none"}  # Hide OTP section
            )
        else:
            error_data = response.json()
            error_msg = error_data.get("error", "Invalid code")
            
            if error_data.get("expired"):
                error_msg = "Code expired. Please request a new code."
            elif error_data.get("attempts_exceeded"):
                error_msg = "Too many attempts. Please request a new code."
            
            return (
                dbc.Alert(error_msg, color="danger", dismissable=True, duration=4000),
                None,
                "",
                {},
                {"display": "block"}
            )
    except Exception as e:
        return (
            dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000),
            None,
            "",
            {},
            {"display": "block"}
        )
```

### Step 6: Add Callback to Resend Code

```python
@app.callback(
    Output("otp-verification-feedback", "children", allow_duplicate=True),
    Input("otp-resend-button", "n_clicks"),
    State("otp-verification-store", "data"),
    prevent_initial_call=True
)
def resend_otp_code(n_clicks, otp_data):
    """Resend OTP code."""
    if not n_clicks or not otp_data:
        return ""
    
    email = otp_data.get("email")
    if not email:
        return dbc.Alert("Error: Email not found", color="danger", dismissable=True, duration=4000)
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/request-code",
            json={"email": email}
        )
        
        if response.ok:
            return dbc.Alert(
                "New code sent to your email",
                color="info",
                dismissable=True,
                duration=3000
            )
        else:
            error = response.json().get("error", "Failed to send code")
            return dbc.Alert(error, color="danger", dismissable=True, duration=4000)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger", dismissable=True, duration=4000)
```

### Step 7: Update Save Triples Callback

Update the save_triples callback to check OTP verification (around line 3030):

```python
@app.callback(
    Output("save-feedback", "children", allow_duplicate=True),
    Input("save-btn", "n_clicks"),
    State("sentence-input", "value"),
    State("literature-link", "value"),
    State("contributor-email", "value"),
    State("email-store", "data"),
    State("otp-session-store", "data"),  # NEW: Check verified session
    # ... other states
    prevent_initial_call=True,
)
def save_triples(n_clicks, sentence_text, literature_link, contributor_email, email_validated, 
                 otp_session, source_entity_name, ...):
    """Save annotation triples (with OTP verification if enabled)."""
    if not n_clicks:
        raise PreventUpdate
    
    # Check basic email validation
    if not email_validated:
        return dbc.Alert("Please enter a valid email address.", color="danger", dismissable=True, duration=4000)
    
    # NEW: Check OTP verification if enabled
    import requests
    try:
        config_response = requests.get(f"{BACKEND_URL}/api/email-verification/config")
        if config_response.ok and config_response.json().get("enabled"):
            # OTP is enabled, check verification
            if not otp_session or not otp_session.get("session_id"):
                return dbc.Alert(
                    "Please verify your email address before submitting annotations.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Verify session is still valid
            check_response = requests.post(
                f"{BACKEND_URL}/api/email-verification/check-session",
                json={"session_id": otp_session["session_id"]}
            )
            
            if not check_response.ok or not check_response.json().get("verified"):
                return dbc.Alert(
                    "Your verification session has expired. Please verify your email again.",
                    color="warning",
                    dismissable=True,
                    duration=6000
                )
            
            # Use verified email from session
            email_validated = check_response.json().get("email")
    except:
        pass  # If OTP check fails, continue with basic validation
    
    # Rest of save_triples logic remains the same
    # ...
```

### Step 8: Add Session Check on Page Load

Add callback to check existing session on page load:

```python
@app.callback(
    Output("otp-session-store", "data", allow_duplicate=True),
    Output("email-validation", "children", allow_duplicate=True),
    Output("email-validation", "style", allow_duplicate=True),
    Input("url", "pathname"),
    State("otp-session-store", "data"),
    prevent_initial_call=True
)
def check_existing_session(pathname, session_data):
    """Check if there's an existing verified session on page load."""
    if not session_data or not session_data.get("session_id"):
        return None, "", {}
    
    import requests
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/email-verification/check-session",
            json={"session_id": session_data["session_id"]}
        )
        
        if response.ok and response.json().get("verified"):
            email = response.json().get("email")
            return (
                session_data,
                f"✓ Email verified ({email})",
                {"color": "green"}
            )
        else:
            # Session expired or invalid
            return None, "", {}
    except:
        return None, "", {}
```

## Testing the Implementation

### 1. Enable OTP Validation

```python
# config.py
ENABLE_OTP_VALIDATION = True
```

### 2. Configure Email Provider

```bash
# .env
EMAIL_PROVIDER=sendpulse
SENDPULSE_USER_ID=your-user-id
SENDPULSE_SECRET=your-secret
SMTP_FROM_EMAIL=noreply@harvest.app
```

### 3. Test Flow

1. Navigate to Annotate tab
2. Enter email address
3. Click outside email field (triggers validation)
4. OTP section should appear
5. Check email for 6-digit code
6. Enter code and click Verify
7. Green checkmark should appear
8. Can now save annotations
9. Session persists for 24 hours

### 4. Test Rate Limiting

- Request code 4 times in one hour
- Should get "Rate limit exceeded" error

### 5. Test Session Persistence

- Verify email
- Close browser
- Reopen browser
- Session should still be valid (for 24 hours)

### 6. Test Feature Toggle

```python
# config.py
ENABLE_OTP_VALIDATION = False
```

- OTP section should not appear
- Can save annotations without verification

## Error Handling

The implementation includes comprehensive error handling for:

1. **API Errors**: Network failures, server errors
2. **Rate Limiting**: Too many code requests
3. **Invalid Codes**: Wrong or expired codes
4. **Expired Sessions**: Session validity checking
5. **Feature Toggle**: Graceful fallback when disabled

## UI/UX Considerations

1. **Progressive Disclosure**: OTP section only shown when needed
2. **Clear Feedback**: Visual indicators for each state
3. **Easy Resend**: One-click code resend
4. **Persistent Sessions**: 24-hour validity reduces friction
5. **Graceful Degradation**: Works without OTP if disabled

## Security Notes

1. **Rate Limiting**: Prevents abuse (3 codes/hour)
2. **Attempt Limiting**: Max 5 attempts per code
3. **Code Expiry**: 10-minute window
4. **Session Expiry**: 24-hour validity
5. **IP Tracking**: Hashed for privacy
6. **Secure Storage**: bcrypt hashing for codes

## Performance Considerations

1. **Client-Side Storage**: Session stored in browser (localStorage)
2. **Minimal API Calls**: Only when needed
3. **Background Cleanup**: Server-side, doesn't impact users
4. **Fast Validation**: Cached session checks

## Future Enhancements

1. **Email Preferences**: Allow users to opt out of verification for trusted networks
2. **Multi-Factor Options**: Add ORCID OAuth as alternative
3. **Admin Override**: Allow admins to bypass verification
4. **Analytics**: Track verification success rates
5. **Customizable Expiry**: Allow admins to configure timeouts

## Troubleshooting

### OTP Section Not Appearing
- Check `ENABLE_OTP_VALIDATION = True` in config.py
- Check backend is running
- Check API endpoint: `GET /api/email-verification/config`

### Code Not Received
- Check email provider configuration
- Check SMTP credentials in .env
- Check spam/junk folder
- Check backend logs for errors

### Verification Fails
- Check code is not expired (10 minutes)
- Check not exceeded max attempts (5)
- Check rate limit not exceeded (3/hour)
- Check backend logs for details

### Session Lost
- Sessions expire after 24 hours
- Browser localStorage cleared
- Check session validity: `POST /api/email-verification/check-session`

## Summary

This implementation provides:
- ✅ Secure email verification
- ✅ User-friendly UI/UX
- ✅ Comprehensive error handling
- ✅ Feature toggle support
- ✅ Rate limiting and security
- ✅ Session persistence
- ✅ SendPulse integration
- ✅ Production-ready code

Follow the steps above to integrate email verification into the HARVEST frontend. Each step builds on the previous one, creating a complete, secure, and user-friendly verification flow.



---

## Content from EMAIL_VERIFICATION_CONFIG_PLAN.md

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


