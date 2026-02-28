# NetWatch Configuration

## Required Environment Variables

- `SECRET_KEY`
  - Required.
  - Minimum 32 characters.
  - Used to sign Flask session cookies.

- `ADMIN_PASSWORD_HASH`
  - Required.
  - Bcrypt hash for the admin password.

## Optional Environment Variables

- `SESSION_LIFETIME_HOURS`
  - Default: `8`
  - Session expiration window for authenticated users.

- `SESSION_COOKIE_SECURE`
  - Default:
    - `true` when `FLASK_ENV=production`
    - `false` otherwise
  - Set `true` in production (HTTPS).

- `FLASK_ENV`
  - Default: `production`
  - Used for environment-sensitive defaults.

- `CORS_ORIGINS`
  - Default: `http://localhost:5000,http://127.0.0.1:5000`
  - Comma-separated list of allowed origins.

- `TRUST_PROXY`
  - Default: `false`
  - Set to `true` only when running behind a trusted reverse proxy.
  - Enables `X-Forwarded-For` client IP extraction.

## Example `.env`

```dotenv
ADMIN_PASSWORD_HASH=
SECRET_KEY=
SESSION_LIFETIME_HOURS=8
SESSION_COOKIE_SECURE=true
FLASK_ENV=production
CORS_ORIGINS=http://localhost:5000
TRUST_PROXY=false
```

## Generate Credentials

Generate bcrypt hash:
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'your-strong-password', bcrypt.gensalt()).decode())"
```

Generate random secret key (Python):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Startup Behavior
- Application startup fails if:
  - `SECRET_KEY` is missing or too short
  - `ADMIN_PASSWORD_HASH` is missing

This fail-fast behavior prevents insecure default deployment.
