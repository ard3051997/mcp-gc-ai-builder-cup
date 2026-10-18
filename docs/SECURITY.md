# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | ✅        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by email to: abhishek.dhobe@kalagato.co

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Any suggested mitigations

You will receive an acknowledgement within 48 hours and a status update within 7 days.

## Credential Security

This project connects to multiple Google APIs and third-party services. **Never commit credentials to the repository.**

- Copy `.env.example` to `.env` and fill in your values — `.env` is gitignored.
- Service account JSON files, `token.json`, `credentials.json`, and `google-ads.yaml` are gitignored.
- If you believe credentials have been exposed, rotate them immediately and audit access logs.
- For production deployments, use Google Secret Manager or equivalent secrets management rather than `.env` files.

## Known Security Considerations

- MCP servers accept credential injection via HTTP headers (`X-Google-Credentials`). Expose MCP servers only over stdio or on trusted internal networks — never on a public port without auth.
- Tool outputs (Play Store reviews, ASO scrapes) flow into the LLM coordinator. The coordinator persona instructs it to treat tool output as untrusted data, but defence-in-depth sanitization at the application layer is recommended for production.
- The Google Ads MCP integration pulls code from GitHub at runtime (`uvx run --spec git+...`). Pin to a specific commit hash before production use.
