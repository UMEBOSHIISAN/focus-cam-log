# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories
("Report a vulnerability" on the repository's Security tab) rather than
opening a public issue. Reports will be acknowledged on a best-effort basis;
this is a small personal project without a guaranteed response SLA.

## Scope notes

- Your `GEMINI_API_KEY` is read from the environment or a local env file.
  Never commit it; `.gitignore` excludes `env` and `*.env` by default.
- All data is stored locally (see [PRIVACY.md](PRIVACY.md)); the only network
  communication is with the Google Gemini API over HTTPS.
- Snapshots and the SQLite database are written with your user's default
  permissions — protect `FOCUS_LOG_DATA_DIR` accordingly on shared machines.
