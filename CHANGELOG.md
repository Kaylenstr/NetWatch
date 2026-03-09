# Changelog

## 2026-03-09

- Security: XSS mitigation (sanitized popup content, `esc()` helper)
- Security: Generic error messages (no server-name leakage)
- Security: Request size limit on POST /api/config (100KB), atomic config writes
- Security: CORS origin validation (no wildcards, URL format check)
- Security: Docker hardening (resource limits, cap_drop, read_only, pip-audit)
- Proxy: ProxyFix middleware, gunicorn as production server
- New: Nginx proxy example config (`docs/proxy-nginx-netwatch.example.conf`)

## 2026-03-01

- Fixed out-of-the-box authentication on HTTP/LAN deployments by changing the default `SESSION_COOKIE_SECURE` behavior to `false`.
- Updated default environment templates to include localhost + loopback CORS origins and HTTP-friendly session defaults.
- Updated installation and configuration documentation in English with explicit HTTP vs HTTPS guidance and setup-mode behavior.
