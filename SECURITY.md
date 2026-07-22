# Security Policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

**Do not open a public issue.** Instead, use
[GitHub private vulnerability reporting](https://github.com/nnayda/pricepoint/security/advisories/new).

Please include reproduction steps, the affected component (API, frontend,
data pipeline, Helm chart), and impact. You can expect an acknowledgement
within a few days, and we'll coordinate disclosure with you.

## Scope notes

- The bundled Docker Compose stack and Helm chart ship development-friendly
  defaults (local credentials, permissive CORS). Reports that these defaults
  are insecure *for local development* are out of scope; reports that the
  chart or docs **encourage** insecure production deployment are in scope.
- Third-party data sources (Redfin, county GIS, FRED, etc.) are out of scope.
