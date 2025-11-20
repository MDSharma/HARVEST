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
