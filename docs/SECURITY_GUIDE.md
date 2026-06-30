# AuthenticEye Platform — Security & Hardening Guide

This document describes the security protocols, file validations, and gateway hardening standards applied to the AuthenticEye deepfake verification suite.

---

## 1. Network & Header Defenses

### Content Security Policy (CSP)
We utilize **Helmet** middleware to inject strict CSP headers, preventing cross-site scripting (XSS) and data injection vulnerabilities.
- **`default-src`**: Restricted to `'self'`.
- **`connect-src`**: Explicitly whitelists gateway channels (`localhost:5000`, `localhost:8000`, and Vite HMR sockets).
- **`img-src`**: Restricts image loads to local uploads, base64 data strings, and trusted CDNs.
- **`script-src` / `style-src`**: Standardized to exclude arbitrary third-party domains.

### Input Sanitization & MongoDB Injection
To defend against NoSQL injection vectors (such as parameter pollution utilizing `$gt` or queries designed to bypass login), the gateway intercepts incoming JSON payloads:
- Express uses `express-mongo-sanitize` to recursively strip any object keys prefixing with `$` or containing `.`.

---

## 2. Authentication Hardening

AuthenticEye implements a secure **Short-Lived Access Token + Long-Lived Refresh Token** system:

```
┌────────┐               Credentials               ┌────────┐
│ Client │ ──────────────────────────────────────> │ Server │
│        │ <────────────────────────────────────── │        │
└────────┘   Access Token (15m JWT, In-Memory)     └────────┘
             Refresh Token (7d Cookie, HTTP-Only)
```

1. **Access Token**:
   - Short-lived JWT (15 minutes expiry).
   - Saved in client-side memory (never stored in LocalStorage, preventing XSS-based theft).
   - Attached manually to authorization headers: `Authorization: Bearer <token>`.
2. **Refresh Token**:
   - Long-lived token (7 days expiry).
   - Stored in a secure cookie with:
     - `httpOnly: true` (inaccessible to client-side scripts).
     - `secure: true` (only transmitted over HTTPS).
     - `sameSite: 'Strict'` (mitigates CSRF attack vectors).
   - Sent to `/api/auth/refresh` to transparently regenerate access tokens when they expire.

---

## 3. Upload File Validation & Quarantine Workflow

To guarantee that malicious payloads or spoofed files do not compromise servers:

```
                         Upload Request
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Quarantine Folder   │
                    └──────────┬───────────┘
                               │
                   Security Check Pipeline
                               │
               ┌───────────────┼───────────────┐
               ▼               ▼               ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │ Magic Bytes │ │ SHA-256 Hash│ │ Virus Scan  │
        │ Verification│ │ Calculation │ │   (ClamAV)  │
        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
               │               │               │
               └───────────────┼───────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   Promote & Store    │
                    │   (/uploads/ folder) │
                    └──────────────────────┘
```

1. **Quarantine Directory**:
   - All uploaded files are written to `/uploads/quarantine/` using dynamic randomized file names.
   - Files are kept isolated until security checks pass.
2. **Verification Pipeline**:
   - **Magic Bytes Validation**: Read first 4 bytes of files synchronously. Confirms JPEGs start with `ffd8ff`, PNGs with `89504e47`, WEBP with `52494646`, and ZIPs with `504b0304` to prevent extension spoofing.
   - **File Hash Check**: Computes a SHA-256 checksum of the file before processing, ensuring file integrity.
   - **Virus Scanning**: Integrated scanning hook running on the host system. In local development environments, it defaults to a mock hook verification check.
3. **Uplink Promotion**:
   - If clean, file is moved to `/uploads/` and forwarded for model inference.
   - If any validation fails, the file is deleted immediately, throwing a 500 security error.
