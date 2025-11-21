# Deployment Architecture Diagrams

Visual guide to understand how the T2T Training Application works in different deployment modes.

## Table of Contents
- [Internal Mode Architecture](#internal-mode-architecture)
- [Nginx Mode Architecture](#nginx-mode-architecture)
- [Request Flow Comparison](#request-flow-comparison)
- [Component Interaction](#component-interaction)

---

## Internal Mode Architecture

### Network Diagram

```
┌─────────────────────────────────────────────────┐
│                 User's Browser                  │
│              (http://localhost:8050)            │
└────────────────────┬────────────────────────────┘
                     │
                     │ HTTP Requests
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│        Frontend (Dash) - Port 8050              │
│             Host: 0.0.0.0                       │
│                                                 │
│  Routes:                                        │
│  • / → Dash Application                         │
│  • /proxy/pdf/<id>/<file> → Proxy Route        │
│  • /proxy/highlights/<id>/<file> → Proxy Route │
└────────────────────┬────────────────────────────┘
                     │
                     │ Internal HTTP (127.0.0.1)
                     │ Proxied Requests Only
                     ▼
┌─────────────────────────────────────────────────┐
│        Backend (Flask) - Port 5001              │
│           Host: 127.0.0.1 (localhost)           │
│           NOT ACCESSIBLE EXTERNALLY              │
│                                                 │
│  API Endpoints:                                 │
│  • /api/health                                  │
│  • /api/projects/<id>/pdf/<file>               │
│  • /api/projects/<id>/pdf/<file>/highlights    │
│  • ... (all other API endpoints)                │
└─────────────────────────────────────────────────┘
```

### Key Characteristics

**Security:**
- Backend bound to `127.0.0.1` (localhost only)
- Backend not accessible from outside the server
- Only frontend is exposed to users

**Request Flow:**
1. User requests PDF → Frontend at `/proxy/pdf/...`
2. Frontend receives request
3. Frontend makes internal request to backend at `127.0.0.1:5001`
4. Backend serves PDF
5. Frontend streams PDF back to user

**Configuration:**
```python
DEPLOYMENT_MODE = "internal"
HOST = "127.0.0.1"  # Backend localhost only
```

---

## Nginx Mode Architecture

### Network Diagram (Single Server)

```
┌─────────────────────────────────────────────────┐
│                 User's Browser                  │
│           (https://yourdomain.com)              │
└────────────────────┬────────────────────────────┘
                     │
                     │ HTTPS Requests
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│           Nginx Reverse Proxy - Port 443        │
│                                                 │
│  Routes:                                        │
│  • / → Frontend                                 │
│  • /api/* → Backend                            │
│                                                 │
│  Features:                                      │
│  • SSL/TLS Termination                         │
│  • Load Balancing                              │
│  • Rate Limiting                               │
│  • Caching                                     │
└──────────┬─────────────────────┬────────────────┘
           │                     │
           │                     │
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │   Frontend   │      │   Backend    │
    │  (Dash)      │      │   (Flask)    │
    │  Port 8050   │      │  Port 5001   │
    │              │      │              │
    │ Host: 0.0.0.0│      │ Host: 0.0.0.0│
    └──────────────┘      └──────────────┘
```

### Network Diagram (Separate API Subdomain)

```
┌─────────────────────────────────────────────────┐
│               User's Browser                    │
└──────────┬─────────────────────┬────────────────┘
           │                     │
           │                     │
           ▼                     ▼
    ┌─────────────┐      ┌──────────────┐
    │   Nginx     │      │    Nginx     │
    │   (Main)    │      │    (API)     │
    │   Port 443  │      │   Port 443   │
    │             │      │              │
    │ yourdomain  │      │api.yourdomain│
    └──────┬──────┘      └──────┬───────┘
           │                     │
           ▼                     ▼
    ┌──────────────┐      ┌──────────────┐
    │   Frontend   │      │   Backend    │
    │   Port 8050  │      │  Port 5001   │
    └──────────────┘      └──────────────┘
```

### Key Characteristics

**Security:**
- Backend bound to `0.0.0.0` (accessible on network)
- Nginx handles SSL/TLS termination
- Firewall should restrict direct backend access
- Rate limiting at nginx level

**Request Flow:**
1. User requests PDF → Nginx at `https://yourdomain.com/api/...`
2. Nginx routes to backend at `127.0.0.1:5001`
3. Backend serves PDF
4. Nginx returns to user

**Configuration:**
```python
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "https://yourdomain.com/api"
HOST = "0.0.0.0"  # Backend accessible on network
```

---

## Request Flow Comparison

### Internal Mode - PDF Request

```
Browser                Frontend                Backend
   │                      │                      │
   │ GET /proxy/pdf/1/x.pdf                     │
   ├──────────────────────>│                     │
   │                      │                      │
   │                      │ GET http://127.0.0.1:5001/
   │                      │     api/projects/1/pdf/x.pdf
   │                      ├─────────────────────>│
   │                      │                      │
   │                      │    PDF Data          │
   │                      │<─────────────────────┤
   │                      │                      │
   │    PDF Data          │                      │
   │<─────────────────────┤                      │
   │                      │                      │
```

### Nginx Mode - PDF Request

```
Browser                 Nginx               Backend
   │                      │                      │
   │ GET https://domain.com/api/projects/1/pdf/x.pdf
   ├──────────────────────>│                     │
   │                      │                      │
   │                      │ GET http://127.0.0.1:5001/
   │                      │     api/projects/1/pdf/x.pdf
   │                      ├─────────────────────>│
   │                      │                      │
   │                      │    PDF Data          │
   │                      │<─────────────────────┤
   │                      │                      │
   │    PDF Data (HTTPS)  │                      │
   │<─────────────────────┤                      │
   │                      │                      │
```

---

## Component Interaction

### Internal Mode Components

```
┌─────────────────────────────────────────────────┐
│                  config.py                      │
│  DEPLOYMENT_MODE = "internal"                   │
│  BACKEND_PUBLIC_URL = ""                        │
│  HOST = "127.0.0.1"                            │
└────────────┬────────────────────────────────────┘
             │
             │ Configuration Read
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
  ┌─────────┐  ┌─────────┐
  │Frontend │  │Backend  │
  │         │  │         │
  │Proxy ON │  │CORS:    │
  │API: int.│  │localhost│
  └─────────┘  └─────────┘
```

### Nginx Mode Components

```
┌─────────────────────────────────────────────────┐
│                  config.py                      │
│  DEPLOYMENT_MODE = "nginx"                      │
│  BACKEND_PUBLIC_URL = "https://api.domain.com"  │
│  HOST = "0.0.0.0"                              │
└────────────┬────────────────────────────────────┘
             │
             │ Configuration Read
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
  ┌─────────┐  ┌─────────┐
  │Frontend │  │Backend  │
  │         │  │         │
  │Proxy OFF│  │CORS:    │
  │API: pub.│  │allow all│
  └─────────┘  └─────────┘
       │           │
       │           │
       └─────┬─────┘
             │
             ▼
     ┌───────────────┐
     │     Nginx     │
     │  Port: 443    │
     │  SSL/TLS      │
     └───────────────┘
```

---

## CORS Configuration

### Internal Mode CORS

```
Backend CORS Configuration:
┌──────────────────────────────────────┐
│ Allowed Origins:                     │
│  • http://localhost:*                │
│  • http://127.0.0.1:*               │
│  • http://0.0.0.0:*                 │
│                                      │
│ Security: Restrictive                │
│ Reason: Backend only accessed        │
│         internally via proxy         │
└──────────────────────────────────────┘
```

### Nginx Mode CORS

```
Backend CORS Configuration:
┌──────────────────────────────────────┐
│ Allowed Origins:                     │
│  • * (all origins)                   │
│                                      │
│ Security: Permissive                 │
│ Reason: Nginx handles origin         │
│         restrictions, backend        │
│         trusts proxy                 │
└──────────────────────────────────────┘
```

---

## Scaling Patterns

### Internal Mode (Limited Scaling)

```
┌─────────┐
│ Server  │
│  ┌───┐  │
│  │FE │  │
│  └───┘  │
│  ┌───┐  │
│  │BE │  │
│  └───┘  │
└─────────┘

Limitation: Single server only
```

### Nginx Mode (Horizontal Scaling)

```
                ┌──────────┐
                │  Nginx   │
                │  (LB)    │
                └────┬─────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
      ┌───────┐  ┌───────┐  ┌───────┐
      │Server1│  │Server2│  │Server3│
      │ ┌──┐  │  │ ┌──┐  │  │ ┌──┐  │
      │ │BE│  │  │ │BE│  │  │ │BE│  │
      │ └──┘  │  │ └──┘  │  │ └──┘  │
      └───────┘  └───────┘  └───────┘

Capability: Multiple backend instances
           with load balancing
```

---

## Security Boundaries

### Internal Mode Security

```
┌───────────────────────────────────────┐
│           Firewall                    │
│  ┌─────────────────────────────────┐  │
│  │ Exposed: Frontend :8050         │  │
│  │ ┌────────────────────────────┐  │  │
│  │ │Protected: Backend :5001    │  │  │
│  │ │(localhost only)            │  │  │
│  │ └────────────────────────────┘  │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
```

### Nginx Mode Security

```
┌───────────────────────────────────────┐
│           Firewall                    │
│  ┌─────────────────────────────────┐  │
│  │ Exposed: Nginx :443 (SSL)       │  │
│  │ ┌────────────────────────────┐  │  │
│  │ │Internal Network            │  │  │
│  │ │  Frontend :8050            │  │  │
│  │ │  Backend :5001             │  │  │
│  │ └────────────────────────────┘  │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
```

---

## Decision Flow

### Choosing Deployment Mode

```
Start
  │
  ▼
Development or        YES    ┌──────────────┐
Simple Deployment? ────────> │ Internal Mode│
  │                           └──────────────┘
  │ NO
  ▼
Need SSL/TLS,         YES    ┌──────────────┐
Load Balancing, or   ────────> │ Nginx Mode   │
Multiple Instances?           └──────────────┘
  │
  │ NO
  ▼
┌────────────────────┐
│ Start with         │
│ Internal Mode,     │
│ Migrate Later      │
└────────────────────┘
```

---

## Migration Path

### Internal → Nginx

```
Step 1: Current State (Internal)
┌─────────────────────────────┐
│  Frontend ──> Backend        │
│  (proxy)    (localhost)      │
└─────────────────────────────┘

Step 2: Add Nginx
┌─────────────────────────────┐
│         Nginx                │
│           │                  │
│   ┌───────┴───────┐          │
│   ▼               ▼          │
│Frontend         Backend      │
└─────────────────────────────┘

Step 3: Update Config
DEPLOYMENT_MODE = "nginx"
BACKEND_PUBLIC_URL = "..."
HOST = "0.0.0.0"

Step 4: Restart
Frontend now uses direct API
Proxy routes disabled
CORS updated automatically
```

---

## Performance Characteristics

### Internal Mode

```
┌────────────────────────────────────┐
│ Latency: Low (local only)         │
│ Throughput: Moderate               │
│ Bottleneck: Single server          │
│ Caching: Application level only    │
└────────────────────────────────────┘
```

### Nginx Mode

```
┌────────────────────────────────────┐
│ Latency: Low to Medium             │
│ Throughput: High (with scaling)    │
│ Bottleneck: Nginx capacity         │
│ Caching: Nginx + Application       │
│ Optimization: Load balancing       │
└────────────────────────────────────┘
```

---

## Summary

### Internal Mode
✓ Simple setup
✓ Secure by default
✓ Perfect for development
✗ No horizontal scaling
✗ No SSL at app level

### Nginx Mode
✓ Production ready
✓ Horizontal scaling
✓ SSL/TLS termination
✓ Advanced features
✗ More complex setup
✗ Requires proxy knowledge

**Recommendation**: Start with internal mode for development, migrate to nginx mode for production.
