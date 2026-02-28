# NetWatch Security

## Security Model
- Public users can view dashboard health, but sensitive host/IP and geo details are masked server-side.
- Configuration changes are restricted to authenticated sessions only.
- State-changing endpoints require CSRF protection.

## Authentication
- Login endpoint: `POST /api/login`
- Session status endpoint: `GET /api/auth/status`
- Logout endpoint: `POST /api/logout`
- Config endpoint (protected): `GET/POST /api/config`

NetWatch uses Flask signed session cookies (no JWT):
- `HttpOnly` enabled
- `SameSite=Strict`
- `Secure` controlled by `SESSION_COOKIE_SECURE` (enable in production with HTTPS)

## Password Handling
- Admin password is never stored in plaintext.
- Set `ADMIN_PASSWORD_HASH` to a bcrypt hash.

Generate hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your-strong-password', bcrypt.gensalt()).decode())"
```

## CSRF Protection
- Obtain token: `GET /api/csrf-token`
- Include token in `X-CSRF-Token` header for:
  - `POST /api/login`
  - `POST /api/config`
  - `POST /api/logout`

## Brute-Force Mitigation
- Login attempts are rate-limited per IP:
  - Max 5 attempts per 15 minutes
  - Exceeding limit returns `429` with `Retry-After` header
- Login response includes random delay to reduce timing side-channel leakage.

## Security Headers
API responses include baseline hardening headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Cache-Control: no-store` for `/api/*`
- `Content-Security-Policy` constrained to app + required CDNs

## Session Lifetime
- Session expiration is controlled by `SESSION_LIFETIME_HOURS`.
- Default is 8 hours.

## Operational Smoke Checks
Use these checks after deployment:
1. `GET /api/metrics` without auth -> host masked (`••••••••`), `lat/lon` hidden.
2. `POST /api/config` without session -> `401`.
3. Invalid login 6x from same IP -> `429` on attempt 6.
4. `POST /api/config` with session but no CSRF header -> `403`.
5. Browser login -> settings load + save + logout.
6. Verify cookie flags in browser devtools (`HttpOnly`, `SameSite=Strict`, `Secure` in prod).
