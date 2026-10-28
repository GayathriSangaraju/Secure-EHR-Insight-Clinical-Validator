# Security Policy

This is a demonstration project, not a certified clinical system. It is **not** intended to process
real patient data and must not be deployed as-is in a healthcare setting.

## Reporting a vulnerability

Please report security issues privately through GitHub's
["Report a vulnerability"](../../security/advisories/new) form on this repository rather than a
public issue. Expect an initial reply within a week.

## Data handling

- The repository contains no patient data. MIMIC-IV is credentialed data; never commit it or
  paste it into issues.
- Secrets live in `.env` (git-ignored). CI runs gitleaks and blocks tracked data files.
- Audit logs record pseudonymised patient references and counts only, never question or answer text.

## Known limitations

No authentication or per-user authorization on the API, and redaction is statistical (it can miss
identifiers). See the "Limitations" section of the readme.
